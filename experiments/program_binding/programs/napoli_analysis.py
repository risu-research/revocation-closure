raw=read('napoli_PRIV')
# A content-dependent transform that is not a fixed broker-owned function.
emit(b'NAPOLI_NOTE|' + bytes((c ^ 0x33 for c in raw[:16])))
