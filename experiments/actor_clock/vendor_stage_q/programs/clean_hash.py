import hashlib
raw=read('iottie_CLEAN')
emit(b'DIGEST|' + hashlib.sha256(raw).hexdigest().encode())
