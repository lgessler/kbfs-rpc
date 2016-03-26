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


def write_client_data_to_kbfs(fifopath,filepath):
    """ 
    Args:
        fifopath: the absolute path of a fifo a client created under SOCK_DIR
        filepath: the file under /keybase that is distributed by KBFS to other
                  servers
    """
    # http://stackoverflow.com/questions/17449110/fifo-reading-in-a-loop
    fifo = open(fifopath, "r")
    for line in fifo.read():
        with open(filepath, 'a') as f:
            f.write(line)
    fifo.close()

class Watcher(PatternMatchingEventHandler):
    patterns = ["*.fifo"]
    def on_created(self, event):
        SERVER.read_client_send_to_kbfs(event.src_path)

class Server(object):
    def __init__(self):
        self._client_info = self._get_device_id()
        self._username = self._client_info['Username']
        self._user_id = self._client_info['UserID']
        self._device_id = self._client_info['Device']['deviceID']

        self._fifonames = []
        self._fifowriters = []

        for fifopath in [os.path.join(dp, f) for dp, dn, fn in \
                os.walk(os.path.expanduser(SOCK_DIR)) for f in fn if \
                f.endswith('.fifo')]:
            self.read_client_send_to_kbfs(fifopath)

        self.clients = {} # name to subs

    def read_client_send_to_kbfs(self, fifopath):
        print("Listening on " + fifopath)
        self._fifonames.append(fifopath)
        t = thrd.Thread(target=write_client_data_to_kbfs,
                args=(fifopath, self._fifo_to_path(fifopath)))
        self._fifowriters.append(t)
        t.daemon = True
        t.start()

    def _fifo_to_path(self, fifo_path):
        """ Given the path under SOCK_DIR for a file used for client --> server
        communication, construct the corresponding path under /keybase for
        server --> KBFS communication """
        index1 = len("/tmp/kbrpc")
        index2 = len(fifo_path[:fifo_path.rindex('/')])
        filename = fifo_path[fifo_path.rindex('/') + 1 : fifo_path.rindex('.fifo')]
        return "/keybase" + \
               fifo_path[index1:index2] + \
               "/.kbrpc/" + \
               filename + \
               "." + self._user_id + "." + self._device_id + ".sent"

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
    observer.schedule(Watcher(), path=SOCK_DIR, recursive=True)
    observer.start()
    input("Press any key to exit")
