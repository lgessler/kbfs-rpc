package main

import (
  "net"
)

type KbrpcServer struct {
  fsMonitor KbrpcFsMonitor
  socketList []string
}

type KbrpcFsMonitor interface {
  WatchFs() // notify subscribed clients of new files
  // Func() returntype
}


func main() {
}



