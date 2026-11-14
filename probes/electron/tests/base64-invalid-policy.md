# Base64 invalid-policy build validation

The exhaustive policy switch ends in `NOTREACHED()`, matching the existing
Chromium invalid-enum patches used for GCC 16. This retains a fatal invalid
policy path without a fallback value.

For the Electron 45.3.2 NetBSD amd64 source, the previous patched `base64.cc`
had SHA-256 `650a1bf1db3d11d3f1c34825b4f2d9f66c14e24e9ed4d744aa13760178683e0c`;
the revised file had SHA-256
`b57c27f59bda55a1573a1da842d0e2ef55363cfde770de26bf178b5d60478cd4`.
The actual saved production Clang 23.1.4 target compilation command succeeded
for both files. `llvm-objdump -dr` showed identical code and relocations, and
`.rodata` and `.rodata.str1.1` were byte-identical. The actual ASan/UBSan/vptr
target compilation command succeeded for the revised file. This comparison
checks this translation unit, not the complete application. A direct GCC 16
compile of the revised file was not run; the existing analogous Chromium
`NOTREACHED()` patches had previously passed GCC 16 compilation.
