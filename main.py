import os
from server import Server, Watcher
from watchdog.observers import Observer

if __name__ == '__main__':
    #try:
    #    os.listdir('/keybase')
    #except:
    #    print("Failed to open /keybase -- do you have KBFS installed?")
    #    exit(-1)

    SERVER = Server()

    input("Press any key to exit")
