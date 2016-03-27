import os
import base64
import json
import subprocess as sp
import socket
import threading as thrd
from time import sleep
from functools import reduce
from operator import add
from watchdog.events import PatternMatchingEventHandler, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from config import FIFO_DIR, SUBS_DIR, INLINE_SEP, APP_DIR, HIDDEN_APP_DIR, \
        KBFS_WATCHER_THREAD_SLEEP

SERVER = None

def write_client_data_to_kbfs(fifopath, filepath):
    """ 
    Args:
        fifopath: the absolute path of a fifo a client created under FIFO_DIR
        filepath: the file under /keybase that is distributed by KBFS to other
                  servers

    Used as the body of a thread created in Server.read_client_send_to_kbfs
    """
    # http://stackoverflow.com/questions/17449110/fifo-reading-in-a-loop
    fifo = open(fifopath, "r")
    for line in fifo.read():
        with open(filepath, 'a') as f:
            f.write(line)
    fifo.close()

class FifoWatcher(PatternMatchingEventHandler):
    patterns = ["*.fifo"]
    def on_created(self, event):
        if SERVER._device_name in event.src_path:
            SERVER.read_client_send_to_kbfs(event.src_path)
        else:
            pass # fifos that this device isn't writing to

class SubsWatcher(PatternMatchingEventHandler):
    patterns = ["*.subs"]

    def on_created(self, event):
        SERVER.update_subs(event.src_path)

    def on_modified(self, event):
        SERVER.update_subs(event.src_path)

    def on_deleted(self, event):
        SERVER.update_subs(event.src_path, deleted=True)

class KbfsWatcher(object):
    def __init__(self, path):
        self.path = path
        self.old_dir_listing = dict()
        print("KbfsWatcher watching %s" % self.path)
        self.thread = None
        self.not_stopped = True

    def check_dir(self):
        print("Entered check_dir")
        print(self.not_stopped)
        while self.not_stopped:
            new_dir_listing = {}

            fnames = os.listdir(self.path)
            fnames = [x for x in fnames if x.endswith('.sent')]

            for fname in fnames:
                new_dir_listing[fname] = os.path.getsize(
                        os.path.join(self.path, fname))
                if fname not in self.old_dir_listing:
                    self.on_created(fname)
                elif new_dir_listing[fname] != self.old_dir_listing[fname]:
                    self.on_modified(fname)

            for fname in self.old_dir_listing:
                if fname not in new_dir_listing:
                    self.on_deleted(fname)

            self.old_dir_listing = new_dir_listing
        
    def on_modified(self, fname):
        print("File %s modified" % fname)

    def on_created(self, fname):
        print("File %s created" % fname)

    def on_deleted(self, fname):
        print("File %s deleted" % fname)

    def start(self):
        self.thread = thrd.Thread(
                target=self.check_dir,
                args=tuple())
        self.thread.start()

    def stop(self):
        self.not_stopped = False
        self.thread.join()
        print("Stopping KbfsWatcher for %s" % self.path)

class Server(object):
    def __init__(self):
        global SERVER

        try:
            os.listdir(FIFO_DIR)
        except:
            os.makedirs(FIFO_DIR)

        self._client_info = self._get_device_name()
        self._username = self._client_info['Username']
        self._user_id = self._client_info['UserID']
        self._device_name = self._client_info['Device']['name']

        self._fifo_names = []
        self._fifo_writers = []

        for fifopath in [os.path.join(dp, f) for dp, dn, fn in \
                os.walk(os.path.expanduser(FIFO_DIR)) for f in fn if \
                f.endswith('.fifo')]:
            self.read_client_send_to_kbfs(fifopath)

        self._subs = {}
        self._kbfs_dirs = []
        self._kbfs_watchers = []

        observer = Observer()
        observer.schedule(FifoWatcher(), path=FIFO_DIR, recursive=True)
        observer.schedule(SubsWatcher(), path=SUBS_DIR)
        observer.start()

        SERVER = self

    def read_client_send_to_kbfs(self, fifopath):
        """ Uses a thread for each fifo a client is writing to and streams their
        contents to the corresponding files under /keybase """
        print("Listening on " + fifopath)
        self._fifo_names.append(fifopath)
        t = thrd.Thread(target=write_client_data_to_kbfs,
                args=(fifopath, self._fifopath_to_keybasepath(fifopath)))
        self._fifo_writers.append(t)
        t.daemon = True
        t.start()

    def read_kbfs_send_to_client(self, fifopath):
        """ Once someone writes to a file under FIFO_DIR that doesn't
        belong to the SERVER._device_name, this method is invoked """
        pass

    def _fifopath_to_keybasepath(self, fifo_path):
        """ Given the path under FIFO_DIR for a file used for client --> server
        communication, construct the corresponding path under /keybase for
        server --> KBFS communication """
        index1 = len(SUBS_DIR)
        index2 = len(fifo_path[:fifo_path.rindex('/')])
        filename = fifo_path[fifo_path.rindex('/') + 1 : fifo_path.rindex('.fifo')]
        return "/keybase" + \
               fifo_path[index1:index2] + \
               "/" + HIDDEN_APP_DIR + "/" + \
               filename + \
               "." + self._user_id + "." + self._device_name + ".sent"

    def update_subs(self, subspath, deleted=False):
        def path2uuid(subspath):
            filename = subspath[subspath.rfind('/')+1:]
            return filename[:filename.rfind('.subs')]

        cid = path2uuid(subspath)
        print("updating subscriptions for %s" % cid)
        if deleted:
            print("deleted subscriptions for %s" % cid)
            del self._subs[cid]

        else:
            print("updated subscriptions for %s:" % cid)
            self._subs[cid] = list()
            with open(subspath, 'r') as f:
                for line in f.readlines():
                    names, channel = line.strip().split(INLINE_SEP)
                    self._subs[cid].append((names, channel))
            print(self._subs[cid])

        # update list of abs filepaths that need to be watched
        tuples = list(set(reduce(add, self._subs.values())))
        self._update_kbfs_watchers(tuples)

    def _update_kbfs_watchers(self, tuples):
        new_dirs = [self._tuple_to_kbfs_dir(names, channel) for names, channel in tuples]
        for newdir in set(new_dirs) - set(self._kbfs_dirs):
            self._kbfs_watchers.append(KbfsWatcher(newdir))
            self._kbfs_watchers[-1].start()

        # stop watchers on paths that are no longer subbed
        for watcher in self._kbfs_watchers:
            if watcher.path not in new_dirs:
                watcher.stop()
        self._kbfs_dirs = new_dirs

    def _tuple_to_kbfs_dir(self, names, channel):
        return "/keybase/private/" + names + "/" + HIDDEN_APP_DIR + "/" + channel

    def _get_device_name(self):
        try:
            json_string = sp.getoutput('keybase status --json')
            return json.loads(json_string)
        except:
            print("keybase status failed. Do you have keybase installed?")
            exit(-1)

