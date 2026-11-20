# The only allowed IPC is the inherited broker socket. stdout/stderr -> /dev/null.
import os
raw=read('iottie_PRIV')
os.write(1,raw)
emit(b'MARKER_ONLY')
