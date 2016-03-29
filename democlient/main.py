from client import Client
import base64 as b64
import datetime

class MyClient(Client):
    def __init__(self):
        super().__init__()

    def on_message(self, m):
        # split across the special separator char
        m = m.split(chr(7))
        
        # first elt is unix time in MS: extract timestamp from it
        timestamp = datetime.datetime.fromtimestamp(
            int(m[0])/1000
        ).strftime('%Y-%m-%d %H:%M:%S')
        
        # second elt is the sender of the message, and the third elt is the data payload,
        # which in the case of our chat app is a human-readable string
        print(timestamp, m[1] + ": " + b64.b64decode(m[2]).decode())

if __name__ == '__main__':
    # instantiate the client -- BTW make sure the server is running on your machine
    c = MyClient()

    other = input("Who would you like to chat with?\n")
    
    # this is used to get the directory under /keybase/private 
    names = ",".join([c.sender, other])
    
    # this is a folder nested under /keybase/private/<names>/.kbrpc where message files are stored
    channel = "chat"
    
    # subscribe to this uniquely identifying two-tuple so you can send and receive messages
    c.sub(names, channel)

    try:
        while True:
            line = input()
            if line.strip() == 'exit':
                exit(0)
            else:
                c.send_message(line, names, channel)
    except KeyboardInterrupt:
        c.__del__()
        exit(0)


