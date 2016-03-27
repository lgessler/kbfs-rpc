import os
import time
from threading import Thread

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

class Watcher(FileSystemEventHandler):
    def __init__(self, path):
        self.path = path

    def on_any_event(self, event):
        print("=== FS event for watcher: %s ===" % (self.path))
        print(event)

def run_fs_observer(path):
    o = Observer()
    o.schedule(Watcher(path), os.path.abspath(path), recursive=True)
    o.start()

    try:
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        o.stop()

    o.join()

class WatchDaemon(object):
    def __init__(self):
        self.watchers = []

    def add_watch_dir(self, dir_path):
        t = Thread(
            target=run_fs_observer, 
            args=(os.path.abspath(dir_path),))
        self.watchers.append(t)
        t.start()

if __name__ == '__main__':
    wd = WatchDaemon()
    wd.add_watch_dir("/Users/sam/Desktop")
    wd.add_watch_dir("/Users/sam/Documents/2016/Spring Semester/misc/kbfs-rpc")

    print("Asdfasdfasdfasdfasd")
    time.sleep(60)
    print("hi hi")