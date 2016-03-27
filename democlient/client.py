import uuid
import os
from base64 import b64encode
import time
from time import sleep
import subprocess as sp
import threading as thrd
import json

FIFO_DIR = "/tmp/kbrpc/private"
SUBS_DIR = "/tmp/kbrpc" 
INLINE_SEP = chr(7)
def now():
    """ current time rounded down to nearest milli"""
    return int(time.time() * 1000)

class Client(object):
    def __init__(self, subs=[]):
        """
        Subs: a list of 2 tuples:
            * element 1 is a string representing a subdir of /keybase/private,
              e.g. "lgessler,tondwalkar"
            * element 2 is a channel under that subdir that the client wants to
              listen to, e.g. "chat". (This corresponds to a directory under the
              first element's .kbrpc subdirectory, e.g.
              ".../lgessler,tondwalkar/.kbrpc/chat"
        """
        self.tok = uuid.uuid4().hex  # nonce identifier
        self.subsfilename = os.path.join(SUBS_DIR, self.tok + '.subs')
        self.sender = self._get_client_info()['Username']
        #self.sender = 'lgessler'

        self._subs = list()
        self._threads = {}
        if subs:
            for names, channel in subs:
                self.sub(names, channel)

    def __del__(self):
        os.remove(self.subsfilename)

    def sub(self, names, channel):
        print("Writing to", SUBS_DIR + '/' + self.tok + '.subs')
        self._subs.append((names, channel))
        with open(self.subsfilename, 'a') as f:
            f.write("{}{}{}\n".format(names, INLINE_SEP, channel))
        self._make_inbound_listener_thread(names, channel)

    def unsub(self, names, channel):
        #TODO: fix this. How to stop threads while they're blocked on IO?
        with open(self.subsfilename, 'r') as f:
            lines = f.readlines()

        with open(self.subsfilename, 'w') as f:
            for line in lines:
                n, c = line.strip().split(INLINE_SEP)
                if not (n == names and c == channel):
                    f.write(line)
        
        self._subs = [x for x in self._subs if \
               not (x[0] == names and x[1] == channel)]
        self._destroy_inbound_listener_thread(names, channel)

    def _get_fifo_in_name(self, names, channel):
        return "/".join([FIFO_DIR, names, channel + ".in.fifo"])

    def _get_fifo_out_name(self, names, channel):
        return "/".join([FIFO_DIR, names, channel + ".out.fifo"])

    def _make_inbound_listener_thread(self, names, channel):
        t = thrd.Thread(
                target=self._listen_to_inbound_fifo,
                args=(self._get_fifo_out_name(names, channel),))
        t.daemon = True
        self._threads[(names, channel)] = t
        print("Added thread for %s, %s" % (names, channel))
        t.start()

    def _listen_to_inbound_fifo(self, fifopath):
        # dear god don't let me get away with this
        while True:
            try:
                fifo = open(fifopath, 'r')
            except:
                # wait for it to get created
                sleep(2) # make this more elegant
                fifo = open(fifopath, 'r')

            accum = ""
            for line in fifo.read():
                accum += line
                if "\n" in accum:
                    self.on_message(accum[:accum.index("\n")])
                    accum = accum[accum.index("\n")+1:]
            fifo.close()

    def _destroy_inbound_listener_thread(self, names, channel):
        t = self._threads[(names, channel)]
        # stop thread somehow
        del self._threads[(names, channel)]

    def send_message(self, m, names, channel):
        if (names, channel) not in self._subs:
            raise Exception("Can't send message on a channel you're not"
                    "subscribed to")

        fname = self._get_fifo_in_name(names, channel)
        with open(fname, 'w') as f:
            f.write(INLINE_SEP.join([str(now()), self.sender, 
                b64encode(str.encode(m)).decode()]) + "\n")

    def on_message(self, m):
        print("Client receives message: %s" % m)

    def _get_client_info(self):
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

    c = Client()
    c.sub("lgessler,tondwalkar","chat")
    
    print("""c.send_message(os.getlogin() + " has joined room!","lgessler,tondwalkar","chat")""")
