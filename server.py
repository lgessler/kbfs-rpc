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
from collections import defaultdict

from config import FIFO_DIR, SUBS_DIR, INLINE_SEP, APP_DIR, HIDDEN_APP_DIR, \
        KBFS_WATCHER_THREAD_SLEEP
from common import Message, now

# only one per machine
SERVER = None

def write_client_data_to_kbfs(fifopath, filepath):
    """ 
    Args:
        fifopath: the absolute path of a fifo a client created under FIFO_DIR
        filepath: the file under /keybase that is distributed by KBFS to other
                  servers
    """
    # http://stackoverflow.com/questions/17449110/fifo-reading-in-a-loop
    fifo = open(fifopath, "r")
    for line in fifo.read():
        with open(filepath, 'a') as f:
            f.write(line)
    fifo.close()

def write_kbfs_data_to_client(fifopath, message):
    fifo = open(fifopath, "w")
    fifo.write(message)
    fifo.close()

class KbfsWatcher(object):
    def __init__(self, path, names, channel):
        self.path = path
        self.names = names
        self.channel = channel
        self.fifo_filename= "/".join([FIFO_DIR, self.names, self.channel + ".out.fifo"])
        print("SELF FIFO FILENAME:", self.fifo_filename)

        self.last_accessed = defaultdict(lambda: 0)
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
        
    def _write_new_lines(self, fname):
        last_accessed = self.last_accessed[fname]
        with open(fname, 'r') as f:
            for line in f.readlines():
                time_made = int(line.strip().split(INLINE_SEP)[0])
                if time_made > last_accessed:
                    write_kbfs_data_to_client(self.fifo_filename, line)
        self.last_accessed[fname] = now()

    def on_modified(self, fname):
        self._write_new_lines(fname) 
        print("File %s modified" % fname)

    def on_created(self, fname):
        self._write_new_lines(fname) 
        print("File %s created" % fname)

    def on_deleted(self, fname):
        pass # unsupported action
        #print("File %s deleted" % fname)

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

        self._subs = {}
        self._kbfs_watchers = {}

        # key: dir of file
        # value: thread managing it
        self._out_fifo_dict = dict()
        self._in_fifo_dict = dict()

        observer = Observer()
        observer.schedule(SubsWatcher(), path=SUBS_DIR)
        observer.start()

        SERVER = self

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
        cid = self._path2uuid(subspath)
        print("Updating sub for %s" % subspath)
        if deleted:
            self._delete_all_subs(cid)
        else:
            room_tuples = list()

            with open(subspath, 'r') as f:
                for line in f.readlines():
                    names, channel = line.strip().split(INLINE_SEP)
                    room_tuples.append((names,channel))

            if self._subs.values():
                existing_room_tuples = list(set(reduce(add, self._subs.values())))
            else:
                existing_room_tuples = []

            for names, channel in room_tuples:
                if (names, channel) not in existing_room_tuples:
                    self._add_room(cid, names, channel)

            for names, channel in existing_room_tuples:
                if (names, channel) not in room_tuples:
                    self._remove_room(cid, names, channel)

            print("updated subscriptions for %s:" % cid)

    def _delete_all_subs(self, cid):
        """ Delete all subscriptions for a particular client """
        print("Deleting all subscriptions for client %s" % cid)
        del self._subs[cid]

    def _remove_room(self, cid, names, channel):
        """ Remove a room for a particular client """
        self._subs[cid] = [(nms, chnl) for (nms, chnl) in self._subs[cid] \
                if not (nms == names and chnl == channel)]
        self._check_if_remove_watcher(existed_before)

    def _add_room(self, cid, names, channel):
        """ Add a room for a particular client """
        existed_before = self._get_unique_rooms()

        if cid not in self._subs:
            self._subs[cid] = list()

        if not (names, channel) in self._subs[cid]:
            self._subs[cid].append((names, channel))
        self._check_if_add_watcher(existed_before)

    def _check_if_remove_watcher(self, old_room_list):
        new_room_list = self._get_unique_rooms()
        for room in old_room_list:
            if room not in new_room_list:
                # delete in and out fifos
                self._kbfs_watchers[room].stop()
                del self._kbfs_watchers[room]

    def _check_if_add_watcher(self, old_room_list):
        new_room_list = self._get_unique_rooms()
        print(old_room_list, new_room_list)
        for room in new_room_list:
            if room not in old_room_list:
                self._make_fifos(room)
                self._kbfs_watchers[room] = KbfsWatcher(
                        self._tuple_to_kbfs_dir(room[0], room[1]), room[0],
                        room[1])
                self._kbfs_watchers[room].start()

    def _get_unique_rooms(self):
        """ List of unique (names, channel) tuples (rooms) """
        if self._subs.values():
            return list(set(reduce(add, self._subs.values())))
        return list()

    def _tuple_to_kbfs_dir(self, names, channel):
        return "/keybase/private/" + names + "/" + HIDDEN_APP_DIR + "/" + channel

    def _path2uuid(self, subspath):
        filename = subspath[subspath.rfind('/')+1:]
        return filename[:filename.rfind('.subs')]

    def _make_fifos(self, room):
        names, channel = room
        print("trying to make fifos for %s, %s" % (names, channel))
        sp.call(['mkdir', '-p', "/".join([FIFO_DIR, names])])
        in_fifo_filename = "/".join([FIFO_DIR, names, channel + ".in.fifo"])
        out_fifo_filename = "/".join([FIFO_DIR, names, channel + ".out.fifo"])
        sp.call(['mkfifo', in_fifo_filename])
        sp.call(['mkfifo', out_fifo_filename])

        t = thrd.Thread(
                target=write_client_data_to_kbfs,
                args=(in_fifo_filename,
                    self._fifopath_to_keybasepath(in_fifo_filename)))
        t.daemon = True
        self._out_fifo_dict[out_fifo_filename] = t
        t.start()

        # writing to in fifo is handled by KbfsWatcher made in
        # _check_if_add_watcher



    def _get_device_name(self):
        try:
            json_string = sp.getoutput('keybase status --json')
            return json.loads(json_string)
        except:
            print("keybase status failed. Do you have keybase installed?")
            exit(-1)

class SubsWatcher(PatternMatchingEventHandler):
    patterns = ["*.subs"]

    def on_created(self, event):
        SERVER.update_subs(event.src_path)

    def on_modified(self, event):
        SERVER.update_subs(event.src_path)

    def on_deleted(self, event):
        SERVER.update_subs(event.src_path, deleted=True)


