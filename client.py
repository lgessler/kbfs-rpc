import uuid
import os
from config import FIFO_DIR, SUBS_DIR, INLINE_SEP

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

        self._subs = list()
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

    def unsub(self, names, channel):
        with open(self.subsfilename, 'r') as f:
            lines = f.readlines()

        with open(self.subsfilename, 'w') as f:
            for line in lines:
                n, c = line.strip().split(INLINE_SEP)
                if not (n == names and c == channel):
                    f.write(line)
        
        self._subs = [x for x in self._subs if \
               not (x[0] == names and x[1] == channel)]

    def send_message(self, m, names, channel):
        if (names, channel) not in self._subs:
            raise Exception("Can't send message on a channel you're not"
                    "subscribed to")

    def on_message(self, m):
        pass
