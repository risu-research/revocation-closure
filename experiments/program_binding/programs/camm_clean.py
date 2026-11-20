raw=read('camm_CLEAN')
emit(b'CAMM_CLEAN_ANALYSIS|' + raw[4:18].upper())
