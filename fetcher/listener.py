import select
import socket
import sys


def log(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def loop(server_sock, clients):
    readable, _writable, exceptional = select.select(
        [server_sock] + clients, [], [server_sock] + clients,
    )

    for s in exceptional:
        if s is server_sock:
            raise ValueError('Exceptional error from the server socket. Fuck')

        # O(n) but ok since clients will never be large,
        # literally the kernel ulimit is like 8196 anyway.
        clients.remove(s)
        log('Removed', s.getpeername())


    for s in readable:
        if s is server_sock:
            conn, addr = server_sock.accept()
            log('Connection from', addr)
            conn.setblocking(False)
            clients.append(conn)
        else:
            data = s.recv(1024*8)
            if data == b'':
                clients.remove(s)
            else:
                sys.stdout.buffer.write(data)


def main(s):
    clients = []
    while True:
        loop(s, clients)


if __name__ == '__main__':
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', 1234))
        s.listen(5)
        s.setblocking(False)
        main(s)
