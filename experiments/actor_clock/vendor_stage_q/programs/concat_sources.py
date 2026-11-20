part1=read('iottie_CLEAN')
part2=read('iottie_PRIV')
emit(b'COMBINED|' + part1[:4] + b'|' + part2[-8:])
