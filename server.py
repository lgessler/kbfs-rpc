import os
import base64
import json
import subprocess as sp
import socket
import threading as thrd
from operator import add
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from config import FIFO_DIR, SUBS_DIR, INLINE_SEP, APP_DIR, HIDDEN_APP_DIR

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
        if SERVER._device_id in event.src_path:
            SERVER.read_client_send_to_kbfs(event.src_path)

class SubsWatcher(PatternMatchingEventHandler):
    patterns = ["*.subs"]

    def on_created(self, event):
        SERVER.update_subs(event.src_path)

    def on_modified(self, event):
        SERVER.update_subs(event.src_path)

    def on_deleted(self, event):
        SERVER.update_subs(event.src_path, deleted=True)

class Server(object):
    def __init__(self):
        global SERVER

        try:
            os.listdir(FIFO_DIR)
        except:
            os.makedirs(FIFO_DIR)

        self._client_info = self._get_device_id()
        self._username = self._client_info['Username']
        self._user_id = self._client_info['UserID']
        self._device_id = self._client_info['Device']['deviceID']

        self._fifonames = []
        self._fifowriters = []

        for fifopath in [os.path.join(dp, f) for dp, dn, fn in \
                os.walk(os.path.expanduser(FIFO_DIR)) for f in fn if \
                f.endswith('.fifo')]:
            self.read_client_send_to_kbfs(fifopath)

        self._subs = {}
        self._poll_dirs = []

        observer = Observer()
        observer.schedule(FifoWatcher(), path=FIFO_DIR, recursive=True)
        observer.schedule(SubsWatcher(), path=SUBS_DIR)
        observer.start()

        SERVER = self

    def read_client_send_to_kbfs(self, fifopath):
        """ Uses a thread for each fifo a client is writing to and streams their
        contents to the corresponding files under /keybase """
        print("Listening on " + fifopath)
        self._fifonames.append(fifopath)
        t = thrd.Thread(target=write_client_data_to_kbfs,
                args=(fifopath, self._fifopath_to_keybasepath(fifopath)))
        self._fifowriters.append(t)
        t.daemon = True
        t.start()

    def read_kbfs_send_to_client(self, fifopath):
        """ Once someone writes to a file under FIFO_DIR that doesn't
        belong to the SERVER._device_id, this method is invoked """
        pass

    def _fifopath_to_keybasepath(self, fifo_path):
        """ Given the path under FIFO_DIR for a file used for client --> server
        communication, construct the corresponding path under /keybase for
        server --> KBFS communication """
        index1 = len("/tmp/" + APP_DIR)
        index2 = len(fifo_path[:fifo_path.rindex('/')])
        filename = fifo_path[fifo_path.rindex('/') + 1 : fifo_path.rindex('.fifo')]
        return "/keybase" + \
               fifo_path[index1:index2] + \
               "/" + HIDDEN_APP_DIR + "/" + \
               filename + \
               "." + self._user_id + "." + self._device_id + ".sent"

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
        
        self._poll_dirs = 

    def _get_device_id(self):
        try:
            json_string = sp.getoutput('keybase status --json')
            return json.loads(json_string)
        except:
            print("keybase status failed. Do you have keybase installed?")
            exit(-1)

