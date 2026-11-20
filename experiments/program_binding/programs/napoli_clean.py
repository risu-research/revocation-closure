raw=read('napoli_CLEAN')
emit(b'NAPOLI_CLEAN|' + raw.split(b'_')[1] + b'|' + str(len(raw)).encode())
