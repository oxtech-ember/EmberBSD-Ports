# WASI preview1 reactor smoke

With the selected host tools in `H`, the staged or installed package's `wasi`
directory in `S`, and a selected Node supporting `node:wasi` in `NODE`, run:

```sh
"$H/bin/clang" --target=wasm32-wasip1 --sysroot="$S" \
  -fuse-ld="$H/bin/wasm-ld" -mexec-model=reactor -Wl,--export=run \
  reactor.c -o reactor.wasm
"$NODE" reactor.js reactor.wasm
```

The same test can use `--target=wasm32-wasi` to check the compatibility aliases.
This exercises allocation and reactor initialization, not the entire WASI API.

`tool-prefix.py` checks the actual pkgsrc command expansion for both equal and
distinct host and install prefixes. Run it with the selected host Python,
`--recipe` pointing to the exported `lang/wasi-libc`, `--host-prefix`, a
different absolute `--target-prefix`, and the native `--makeconf`.

`link-flags.sh PKGSRC MAKECONF` configures the recipe and checks that the wasm
links do not take the package `LDFLAGS` that CMake reads from the environment.
