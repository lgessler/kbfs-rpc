import time
from config import INLINE_SEP
from base64 import b64encode

class Message(object):
    def __init__(self, unix_time, sender, data):
        self.unix_time = str(unix_time)
        self.sender = sender 
        self.data = b64encode(data)

    def __str__(self):
        return INLINE_SEP.join(self.unix_time, self.sender, self.data)

def now():
    """ current time rounded down to nearest milli"""
    return int(time.time() * 1000)
