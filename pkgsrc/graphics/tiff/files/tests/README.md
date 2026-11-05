# TIFF donor safety checks

Build the common patched TIFF source with the selected host compiler, enabling
zlib and PixarLog, and run:

```
python3 -B donor-guards.py --source PATCHED_SOURCE --baseline-source PREVIOUS_SOURCE --build BUILD_DIRECTORY \
    --cc SELECTED_CLANG [--cc-arg=OPTION ...]
```

The fixture reads an ordinary TIFF and rejects a file declaring 2^31 strips
with a one-megabyte allocation limit. It compiles the actual patched size and
row expressions with undefined-behavior sanitization, and contrasts the previous and patched PixarLog comparison and tests 32-bit and
64-bit size boundaries. The selected compiler must supply its UBSan runtime.
