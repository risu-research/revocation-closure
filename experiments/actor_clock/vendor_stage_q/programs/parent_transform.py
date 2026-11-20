p=parent('PRE_REVERSE')
a=read('iottie_CLEAN')
emit(b'CHILD_OF|' + p.encode() + b'|' + a[:3])
