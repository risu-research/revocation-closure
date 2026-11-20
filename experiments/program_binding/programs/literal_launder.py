# Negative control: program source itself embeds a value equal to a protected
# synthetic source. The runtime only asks the broker for CLEAN data.
read('iottie_CLEAN')
emit(b'SYNTHETIC_PRIV_SOURCE_FOR_iottie_V1_03' + b'|program_literal')
