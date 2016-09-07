**NOTE:** This is a proof of concept and it's almost entirely broken. 

# Keybase RPC

KBRPC provides a simple interface for RPC-like communication that is end-to-end encrypted, built on top of (and requiring) [Keybase filesystem](https://keybase.io/docs/kbfs). The API is essentially a copy of Socket.IO's: there are just two things to keep track of in the demo Python implementation: `on_message` and `send_message`.

# Implementation

![](http://i.imgur.com/9gX1zE8.png)

Keybase RPC is a layer on top of Keybase filesystem. KBFS appears on the machine at `/keybase`, and all files shared here are automatically signed and encrypted for transmission to either (1) the world, e.g. at /keybase/public/lgessler, or (2) specific people, e.g. /keybase/private/lgessler,tondwalkar,prestwood. Keybase RPC uses this filesystem to pass messages and abstracts away the details for the clients.

We wrote Keybase RPC in Python 3. We used a client-server model for local machine connections, where the "server" is the program that communicates with KBFS, and "clients" are applications that ask the server to write to KBFS on their behalf. Server-client communication is achieved with UNIX FIFO's, i.e. named pipes, and keybase-server communication is accomplished with simple filesystem writes.

# License

MIT
