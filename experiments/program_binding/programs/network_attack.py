import socket
# New sockets forbidden by kernel seccomp, even if Python module is imported.
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
emit(b'UNSAFE_NETWORK')
