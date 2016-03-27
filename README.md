**DISCLAIMER:** This is a proof of concept and it's almost entirely broken. DO NOT use this for anything more than amusement.

#Keybase RPC

## Inspiration

WhatsApp and Telegram drew attention in the news about a month ago. They claim to offer end-to-end encrypted chat, but with no easy way of inspecting their source, users were left with no real choice but to blindly trust them.

Keybase RPC empowers application developers by giving them easy access to (1) authentication of users and (2) encrypted transmission of arbitrary messages. 

We were able to implement a simple chat client just like Telegram's in just 20 lines of code using Keybase RPC, and its architecture is general enough to allow many different kinds of apps as well.

## What it does

Keybase RPC exposes a dead-simple API to application developers that provides encryption and authentication for message passing with *no expectation* that the application developer know anything about cryptography: all that's required is a Keybase Filesystem and a Keybase RPC installation. The application developer then uses just two methods, `on_message` and `send_message`, to interact with Keybase RPC. That's it!

## How we built it

![](http://i.imgur.com/9gX1zE8.png)

Keybase RPC is a layer on top of Keybase Filesystem, an open-source service. An encrypted filesystem appears on the machine at `/keybase`, and all files shared here are automatically signed and encrypted for transmission to either (1) the world, e.g. at /keybase/public/lgessler, or (2) specific people, e.g. /keybase/private/lgessler,tondwalkar,prestwood. Keybase RPC uses this filesystem to pass messages and abstracts away the details for the clients.

We wrote Keybase RPC in Python 3. We used a client-server model for local machine connections, where the "server" is the program that communicates with KBFS, and "clients" are applications that ask the server to write to KBFS on their behalf. Server-client communication is achieved with UNIX FIFO's, i.e. named pipes, and keybase-server communication is accomplished with simple filesystem writes.

## Challenges we ran into

KBFS is streamed on demand, not automatically mirrored like Dropbox, so we had to come up with a way to know when there was a new message a remote client had created. We ended up going with the simplest solution, polling the directory. FIFO's also require special care to read from and write into: every FIFO edge in the diagram above had to be implemented with a thread to avoid blocking the main thread.

## Accomplishments that we're proud of

We abstracted away a *lot* of details for application developers: all an implementing developer has to do in Python is to inherit from a Client class and (1) override its `on_message` function and (2) use its `send_message` function. Application developers don't need to know *anything* about cryptography to have reasonable assurance (assuming they trust the people at Keybase and us, the authors of Keybase RPC, or trust that they have read our code well).

## What we learned

## What's next for Keybase RPC (kbrpc)

Refactoring

# License

MIT
