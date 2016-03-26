import os
import base64
import json
import subprocess as sp
import socket
import threading as thrd

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

#import socketserver

SOCK_DIR = "/tmp/kbrpc/private"
SERVER = None

#fifo.read("/tmp/kbrpc/private/lgessler,tondwalkar,prestwood/chat.sock")

class Watcher(PatternMatchingEventHandler):
    patterns = ["*.fifo"]
    def on_created(self, event):
        SERVER.listen(event.src_path)

class Server(object):
    def __init__(self):
        self._client_info = self._get_device_id()
        self._username = self._client_info['Username']
        self._user_id = self._client_info['UserID']
        self._device_id = self._client_info['Device']['deviceID']

        self._fifonames = []
        self._fifoobjs = []

        for fifopath in [os.path.join(dp, f) for dp, dn, fn in \
                os.walk(os.path.expanduser(SOCK_DIR)) for f in fn if \
                f.endswith('.fifo')]:
            self.listen(fifopath)

        self.clients = {} # name to subs

    def listen(self, fifopath):
        self._fifonames.append(event.src_path)

    def _get_device_id(self):
        try:
            json_string = sp.getoutput('keybase status --json')
            return json.loads(json_string)
        except:
            print("keybase status failed. Do you have keybase installed?")
            exit(-1)



if __name__ == '__main__':
    try:
        os.listdir('/keybase')
    except:
        print("Failed to open /keybase -- do you have KBFS installed?")
        exit(-1)

    SERVER = Server()

    observer = Observer()
    observer.schedule(Watcher(), path=SOCK_DIR)
    observer.start()
