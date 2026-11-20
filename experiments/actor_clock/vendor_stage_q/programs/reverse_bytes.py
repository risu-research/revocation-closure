raw=read('iottie_PRIV')
emit(b'REVERSED|' + raw[::-1])
