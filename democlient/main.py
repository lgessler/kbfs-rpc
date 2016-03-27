from client import Client
import datetime

c = Client()

class MyClient(Client):
    def __init__(self):
        super().__init__()

    def on_message(self, m):
        m = m.split(chr(7))
        timestamp = datetime.datetime.fromtimestamp(
            int(m[0])
        ).strftime('%Y-%m-%d %H:%M:%S')
        print(timestamp, m[1] + ": ", + b64.b64decode(m[2]).decode())

if __name__ == '__main__':
    c = MyClient()

    other = input("Who would you like to chat with?\n")
    names = ",".join([c.sender, other])
    channel = "chat"
    c.sub(names, channel)

    #try:
    while True:
        line = input()
        if line.strip() == 'exit':
            exit(0)
        else:
            c.send_message(line, names, channel)
    #except KeyboardInterrupt:
    #    c.__del__()
    #    exit(0)


