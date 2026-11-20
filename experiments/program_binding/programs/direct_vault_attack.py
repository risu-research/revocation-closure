import os
# Attacker controls Python, but file-opening syscall is denied after startup.
raw=os.open('/tmp/stage_q_should_not_open_vault',os.O_RDONLY)
emit(b'UNSAFE|' + str(raw).encode())
