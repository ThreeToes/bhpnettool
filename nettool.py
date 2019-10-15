#!/usr/bin/python
# nettool.py - Python 3 reimplemntation of the netcat script in Black Hat Python
# Copyright (C) 2019  Stephen Gream
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import socket
import subprocess
import sys
import threading
import select
import os
import signal


class Handler:
    def init_connection(self, connection):
        pass

    def handle_msg(self, msg, connection):
        return False


class EchoHandler(Handler):
    def init_connection(self, connection):
        connection.send(b'Echo enabled\r\n')

    def handle_msg(self, msg, connection):
        if len(msg) == 0:
            return False
        strmsg = msg.decode('utf-8')
        strmsg.rstrip()
        connection.send(bytes("{0}\r\n".format(strmsg), 'utf-8'))
        return False

class CommandHandler(Handler):
    __prompt = b'nettoolsh > \r\n'
    def init_connection(self, connection):
        connection.send(b'Call for papa Palpatine!\r\n')
        connection.send(self.__prompt)

    def handle_msg(self, msg, connection):
        if len(msg) > 0:
            strmsg = msg.decode('utf-8')
            strmsg.rstrip()
            print('[*] Running command "{0}"'.format(strmsg))
            try:
                output = subprocess.check_output(strmsg, stderr=subprocess.STDOUT, shell=True)
                print("[*] Output: {0}".format(output))
                connection.send(output)
                connection.send(b'\r\n')
            except Exception as e:
                print("[*] Error trying to run command")
                print(e)
                connection.send(b'Error running command\r\n')
        connection.send(self.__prompt)
        return False


class UploadHandler(Handler):
    def __init__(self, upload_location):
        self.__upload_location = upload_location

    def handle_msg(self, msg, connection):
        try:
            file_descriptor = open(self.__upload_location, "w")
            print('[*] Writing {0} bytes to file {1}'.format(len(msg), self.__upload_location))
            file_descriptor.write(msg)
            file_descriptor.close()
            connection.send(bytes("Successfully saved file to {0}\r\n".format(self.__upload_location), 'utf-8'))
        except:
            connection.send(bytes("Failed to save file {0}\r\n".format(self.__upload_location), 'utf-8'))
        return True


class Server:

    def __init__(self, target, port, handlers):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__target = target
        self.__port = port
        self.__handlers = handlers
        self.__stop = False

    def listen(self):
        print('[*] Listening on {0}:{1}'.format(self.__target, self.__port))
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
        except KeyboardInterrupt as e:
            print("[!!] Server was interupted. Shutting down")
        finally:
            self.__stop = True
            self.__socket.shutdown(socket.SHUT_RDWR)
            self.__socket.close()

    def __handle(self, client_conn, addr):
        close = False
        for handler in self.__handlers:
            handler.init_connection(client_conn)
        try:
            while not close and not self.__stop:
                data_len = 1
                raw_buffer = bytearray()
                while data_len > 0:
                    (sock_ready,x,y) = select.select([client_conn],[],  [], 0.01)
                    if len(sock_ready) == 0:
                        break
                    data = client_conn.recv(1028)
                    data_len = len(data)
                    if len(data) == 0 or data == b'\xff\xf4\xff\xfd\x06':
                        # Connection was probably closed
                        close = True
                        break
                    elif data:
                        raw_buffer.extend(data)
                    else:
                        break
                if len(raw_buffer) > 0:
                    for handler in self.__handlers:
                        try:
                            close = handler.handle_msg(raw_buffer,client_conn)
                            if close:
                                break
                        except Exception as e:
                            print("[*] Caught an exception")
                            print(e)

        except BrokenPipeError as e:
            print("[*] Connection closed")
        finally:
            print("[*] Closing connection from {0}".format(addr))
            client_conn.shutdown(socket.SHUT_RDWR)
            client_conn.close()


class Client:
    def __init__(self, target, port):
        self.__target = target
        self.__port = port
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__readerThread = threading.Thread(target=self.__reader, args=())
        self.__stop = False
        self.__target_disconnect = False

    def run(self):
        try:
            self.__socket.connect((self.__target, self.__port))
            self.__readerThread.start()
            while not self.__stop:
                t = input()
                msg = "{0}\r\n".format(t)
                sent = self.__socket.send(bytes(msg, 'utf-8'))
                if sent == 0:
                    print("[*] Collection closed")
                    break
        except EOFError as e:
            print('[*] End of file reached')
        except InterruptedError as e:
            print('[*] Interrupted. Exiting')
        except Exception as e:
            print('[*] Exception thrown')
            print(e)
        finally:
            if not self.__target_disconnect:
                self.__stop = True
                self.__socket.shutdown(socket.SHUT_RDWR)
                self.__socket.close()
                self.__readerThread.join(100)

    def __reader(self):
        while not self.__stop:
            try:
                buffer = ""
                dataLen = 1
                while dataLen > 0:
                    (readylist, x, y) = select.select([self.__socket], [], [], 0.01)
                    if len(readylist) == 0:
                        # Target is probably done writing
                        break
                    data = self.__socket.recv(1024)
                    if len(data) == 0 or data == b'\xff\xf4\xff\xfd\x06':
                        # Socket closed
                        self.__stop = True
                        self.__target_disconnect = True
                        break
                    elif data:
                        buffer += data.decode('utf-8')
                    else:
                        break
                if len(buffer) > 0:
                    print(buffer)
            except Exception as e:
                print("[*] Exception thrown: {0}".format(e))
        if self.__target_disconnect:
            print("[!!] Target machine shut down")
            # Interrupt the input
            os.kill(os.getpid(), signal.SIGINT)

def parse_args():
    parser = argparse.ArgumentParser(prog='nettool.py',description='Connect to a TCP server or create a server on a port')
    parser.add_argument('-t', '--target', dest='target', metavar='host', type=str,
                        help='IP target or address to bind to')
    parser.add_argument('-p', '--port', dest='port', metavar='port', type=int,
                        help='Target port or port to bind to')
    parser.add_argument('-l', '--listen', dest='listen', action='store_true',
                        help='Initialise a listener on {target}:{port}')
    parser.add_argument('-c', '--command', dest='command', action='store_true',
                        help='Attach a command listener to a server. Cannot be used with -u')
    parser.add_argument('-e', '--echo', dest='echo', action='store_true',
                        help='Attach an echo listener to a server')
    parser.add_argument('-u', '--upload', dest='upload', metavar='upload_location', type=str,
                        help='Start an upload server and upload to {upload_location}. Cannot be used with -c')
    parser.set_defaults(listen=False, command=False, echo=False)
    args = parser.parse_args(sys.argv[1:])
    arg_problems = arg_sanity_check(args)
    if len(arg_problems) > 0:
        for p in arg_problems:
            print("[*] {0}".format(p))
        parser.print_help()
        sys.exit(1)
    return args


def arg_sanity_check(args):
    problems = []
    if not args.target:
        problems.append("Target is required")
    if not args.port:
        problems.append("Port is required")
    if args.command and args.upload:
        problems.append("Can't have an upload server and a command server at the same time")
    return problems


def main():
    args = parse_args()
    if args.listen:
        handlers = []
        if args.command:
            handlers.append(CommandHandler())
        if args.echo:
            handlers.append(EchoHandler())
        if args.upload:
            handlers.append(UploadHandler(args.upload))
        s = Server(args.target, args.port, handlers)
        s.listen()
    if not args.listen:
        client = Client(args.target, args.port)
        client.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        # Just eat this, don't need a stack trace
        pass