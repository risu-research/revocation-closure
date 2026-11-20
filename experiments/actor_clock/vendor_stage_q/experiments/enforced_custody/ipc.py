"""Narrow single-request JSON-over-Unix-socket protocol; Linux SO_PEERCRED.

This is a synthetic research harness, not a remotely exposed service.
"""
import json
import socket
import struct

MAX_BYTES = 2_000_000

class ProtocolError(ValueError):
    pass


def client(path: str, message: dict) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(4)
        sock.connect(path)
        data = json.dumps(message, sort_keys=True, separators=(',', ':')).encode() + b'\n'
        if len(data) > MAX_BYTES:
            raise ProtocolError('Request too long')
        sock.sendall(data)
        with sock.makefile('rb') as reader:
            response = reader.readline(MAX_BYTES + 1)
    if not response.endswith(b'\n') or len(response) > MAX_BYTES:
        raise ProtocolError('Invalid response framing')
    obj = json.loads(response)
    if not isinstance(obj, dict):
        raise ProtocolError('Nonobject response')
    return obj


def receive(conn: socket.socket) -> dict:
    with conn.makefile('rb') as file:
        raw = file.readline(MAX_BYTES + 1)
    if not raw.endswith(b'\n') or len(raw) > MAX_BYTES:
        raise ProtocolError('Malformed/oversized input')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ProtocolError('Nonobject request')
    return value


def peer_credentials(conn: socket.socket) -> tuple[int, int, int]:
    size = struct.calcsize('3i')
    pid, uid, gid = struct.unpack('3i', conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, size))
    return pid, uid, gid


def serve(sockpath: str, allowed_uids: set[int], handler, ready_file: str | None = None):
    import os
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(sockpath)
        os.chmod(sockpath, 0o660)
        server.listen(12)
        if ready_file:
            with open(ready_file, 'w') as f:
                f.write('READY\n')
        while True:
            conn, _ = server.accept()
            with conn:
                try:
                    _, uid, _ = peer_credentials(conn)
                    if uid not in allowed_uids:
                        raise ProtocolError('Peer UID not allowed')
                    request = receive(conn)
                    result = handler(request, uid)
                    result = {'ok': True, 'result': result}
                except Exception as exc:
                    result = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)[:240]}
                conn.sendall((json.dumps(result, sort_keys=True, separators=(',', ':'))+'\n').encode())
