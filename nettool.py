#!/usr/bin/python
import argparse
import sys
import socket
import threading
import subprocess


class Handler:
    def init_connection(self, connection):
        pass

    def handle_msg(self, msg, connection):
        return False


class EchoHandler(Handler):
    def init_connection(self, connection):
        pass

    def handle_msg(self, msg, connection):
        connection.send(bytes(msg, 'utf-8'))
        return False

class CommandHandler(Handler):
    __prompt = b'nettoolsh > '
    def init_connection(self, connection):
        connection.send(b'Call for papa Palpatine!\r\n')
        connection.send(self.__prompt)

    def handle_msg(self, msg, connection):
        if len(msg) > 0:
            print('[*] Running command "{0}"'.format(msg))
            try:
                output = subprocess.check_output(msg, stderr=subprocess.STDOUT, shell=True)
                print("[*] Output: {0}".format(output))
                connection.send(output)
            except Exception as e:
                print("[*] Error trying to run command")
                print(e)
                connection.send(b'Error running command\r\n')
        connection.send(self.__prompt)
        return False


class Server:

    def __init__(self, target, port, handlers):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__target = target
        self.__port = port
        self.__handlers = handlers

    def listen(self):
        print('[*] Listening on {0}:{1}'.format(self.__target, self.__port))
        self.__socket.bind((self.__target, self.__port))
        self.__socket.listen(5)
        try:
            while True:
                connection, addr = self.__socket.accept()
                print("[*] Connection from {0}".format(addr))
                proc = threading.Thread(target=self.__handle, args=(connection, addr))
                proc.start()
        except Exception as e:
            print("[*] Exception caught, shutting down")
            print(e)
        finally:
            self.__socket.close()

    def __handle(self, client_conn, addr):
        close = False
        dataLen = 1
        for handler in self.__handlers:
            handler.init_connection(client_conn)
        while not close and dataLen > 0:
            buffer = ""
            while dataLen > 0:
                data = client_conn.recv(1024)
                dataLen = len(data)
                if data:
                    buffer += data.decode('utf-8')
                else:
                    break
                if buffer.endswith("\r\n"):
                    break
            for handler in self.__handlers:
                msg = buffer.rstrip()
                try:
                    close = handler.handle_msg(msg,client_conn)
                    if close:
                        break
                except Exception as e:
                    print("[*] Caught an exception")
                    print(e)
        print("[*] Closing connection from {0}".format(addr))
        client_conn.close()


def parse_args():
    parser = argparse.ArgumentParser(prog='nettool.py',description='Connect to a TCP server or create a server on a port')
    parser.add_argument('-t', '--target', dest='target', metavar='host', type=str, nargs=1)
    parser.add_argument('-p', '--port', dest='port', metavar='port', type=int, nargs=1)
    parser.add_argument('-l', '--listen', dest='listen', action='store_true')
    parser.add_argument('-c', '--command', dest='command', action='store_true')
    parser.set_defaults(listen=False)
    return parser.parse_args(sys.argv[1:])


def main():
    args = parse_args()
    if args.listen:
        handlers = []
        if args.command:
            handlers.append(CommandHandler())
        s = Server(args.target[0], args.port[0], handlers)
        s.listen()


if __name__ == '__main__':
    main()