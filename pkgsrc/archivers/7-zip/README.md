# Shared 7-Zip sources

The package recipe also provides the shared LZMA sources consumed by firmware;
prepare them with `scripts/source-inputs/7zip/source.py`. The default package
build retains its upstream hosted headers. A freestanding consumer may define
`Z7_FREESTANDING` for `C/LzmaDec.c` and provide its own declaration and
implementation of `memcpy`; this prevents the decoder and its type header from
requiring hosted `string.h` and `errno.h`. The consumer must supply the
platform ABI and memory services. The option does not itself establish a
working firmware or target runtime.
