import hashlib
raw=read('camm_PRIV')
emit(b'CAMM_SUMMARY|' + hashlib.sha256(raw).hexdigest()[:20].encode())
