#!/usr/bin/env python3
#
# enhanced_burst_generator.py Copyright (c) 2022 Steve Curry
# LICENSE: GPLv3
#
#   This Program is an enhanced prog to generate a burst of flows.
# Based on the idea of program 'burst_generator.py', I hope the program
# can simulate the real flows in ** localhost **.
#   Let's review the old one. There is only one server being generated,
# and the size of the waiting queue is only one, which means that the
# requests of clients will be dealt one by one no matter how many clients
# have been generated.
#   What we should do is to simulate the real flows, which needs a multi-
# threads technique to generate a lot of flows in the same time.
#
import time
import random
import socket
import argparse
import threading

# ----- Globals ----- #
#   We only use one msg to achieve the results of simulating the real 
# flows. And note that byte-str is needed for the transmission.
# We define it.
TEST_MSG = b'Hello, eBPF!'

# ----- SERVER ----- #
class server_thread(threading.Thread):
    def __init__(self, port: int, threads: int):
        super(server_thread, self).__init__()
        self.lock = threading.Lock()
        self.threads = threads
        s_addr_port = ('localhost', port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(s_addr_port)
        self.sock.listen(threads)

    def run(self):
        for i in range(self.threads):
            t = threading.Thread(target=self.__run__)
            t.daemon = True
            t.start()
        self.lock.acquire()
        self.lock.acquire()
    
    #   This function is to accept requests endlessly,
    # and they will be set as daemons, which means they
    # will die when the main thread is dead.
    def __run__(self):
        while True:
            try:
                con, c_addr = self.sock.accept()
                data = con.recv(16)
            except socket.error as exp:
                continue
    
    def stop(self):
        self.lock.release()
        self.sock.close()

class Server():
    def __init__(self, threads: int, n: int):
        self.threads = threads
        self.s_n = n
        self.s_list = list()
    
    def start(self, s_port: int) -> list:
        s_counter, s_ports = 0, list()
        while s_counter < self.s_n or s_port >= 65535:
            try:
                s = server_thread(s_port, self.threads)
                self.s_list.append(s)
                s_ports.append(s_port)
                s_counter += 1
                s.start()
            finally:
                s_port += 1
        return s_ports
    
    def stop(self):
        for i in self.s_list:
            i.stop()
        del self.s_list

# ----- CLIENT ----- #
class client_thread (threading.Thread):
    def __init__(self, s_port: int):
        threading.Thread.__init__(self)
        self.addr = ('localhost', s_port)

    def connect(self):
        """
        Tries to connect to self.addr:self.msg and send self.msg
        Return: True if no error occurres otherwise False 
        """
        s = socket.socket()
        s.settimeout(.5)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.connect(self.addr)
            s.send(TEST_MSG)
            return True
        except socket.error as exc:
            return False
        finally:
            s.close()

    def run(self):
        while not self.connect():
            pass

class Client():
    def __init__(self, s_ports: tuple, n: int):
        self.s_ports = s_ports
        self.c_n = n
        self.c_list = list()
    
    #   This function is to connet to the server, and
    # send a series of messages and then return.
    def start(self):
        s_n = len(self.s_ports)
        for i in range(self.c_n):
            tar_index = random.randint(0, s_n-1)
            c = client_thread(self.s_ports[tar_index])
            self.c_list.append(c)
            c.start()
    
    def join(self):
        for i in self.c_list:
            i.join()
        del self.c_list

# ----- EXCEPTION ----- #
class EbgException(Exception):
    CLIENT_NUM_ERROR = 1
    SERVER_NUM_ERROR = 2
    THREAD_NUM_ERROR = 3
    NO_PORT_TO_USE   = 4

    def __init__(self, value: int):
        self.value = value
    
    def __str__(self) -> str:
        if self.value == EbgException.CLIENT_NUM_ERROR:
            return "Arguments' error: the number of client can not be 0!"
        if self.value == EbgException.SERVER_NUM_ERROR:
            return "Arguments' error: the number of server can not be 0!"
        if self.value == EbgException.THREAD_NUM_ERROR:
            return "Arguments' error: the number of thread each server can not be 0!"
        if self.value == EbgException.NO_PORT_TO_USE:
            return "Port error: no one is available after specified port!"
        else:
            return "Unknown error!"

if __name__ == '__main__':
# ----- Aegument Parsing ----- #
#   There are something we should consider. At first, we should consider
# how many servers should we generate and how many threads a server
# should have. Nextly, for a client, we only generate one thread but
# users could choose how many clients will be generated.
    parser = argparse.ArgumentParser(description="""EBG (enhanced burst generator): 
        Do the best to simulate the real flows. You must choose to generate
        at least one client and one server. By the way, client
        has only one thread created but server can be a multi-thread one.
        It\'s up to you. Enjoy!""")
    parser.add_argument('-c', '--clients', default=1,
    help='specify the number of client to generate.')
    parser.add_argument('-s', '--servers', default=1,
    help='specify the (beginning) number of server to generate.')
    parser.add_argument('-t', '--threads', default=1,
    help='specify the number of thread of one server.')
    parser.add_argument('-p', '--port', default=55534,
    help='specify the port of server to use.')
    args = parser.parse_args()

    CLIENT_NUM = int(args.clients)
    SERVER_NUM = int(args.servers)
    THREAD_NUM = int(args.threads)
    PORT = int(args.port)
    if CLIENT_NUM <= 0:
        raise EbgException(EbgException.CLIENT_NUM_ERROR)
    if SERVER_NUM <= 0:
        raise EbgException(EbgException.SERVER_NUM_ERROR)
    if THREAD_NUM <= 0:
        raise EbgException(EbgException.THREAD_NUM_ERROR)
    
    print('> Initialization begin...')
    start = time.perf_counter_ns()
    s = Server(THREAD_NUM, SERVER_NUM)
    s_ports = s.start(PORT)
    if not len(s_ports):
        raise EbgException(EbgException.NO_PORT_TO_USE)
    print('> Server(s) started...')
    c = Client(s_ports, CLIENT_NUM)
    print('> Generating traffic...')
    c.start()
    c.join()
    print('> Closing servers...')
    s.stop()
    end = time.perf_counter_ns()
    print('> {:.2f} ms is used this time.'.format((end-start)/1000000.0))