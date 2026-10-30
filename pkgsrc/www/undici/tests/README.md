# Undici source package checks

With the selected host prefix in `H`, run
`"$H/bin/python3.15" -B -I -S generator.py --host-prefix "$H"` to check both
llhttp WASM wrappers and a distinct target runtime path. It reads the common
`llhttp-wasi` package, not a bundled WASM archive.

`upstream-wrappers.js SOURCE_DIR PACKAGE_DIR WASM_DIR` compares the staged
wrappers byte-for-byte with the upstream Undici generator using the same
selected llhttp files. Run it with the selected Node interpreter.

For a cross pkgsrc configuration, `bmake do-build` with an empty
`EMBERBSD_UNDICI_RUNTIME_PREFIX=` must fail before generating a loader.
`profiles/common-build-tools/tests/undici-cross-runtime-prefix.sh` checks the
loader the EmberBSD cross profile selects. With an
explicit target prefix, check the staged loader contains that target path and
does not contain the native host prefix or the cross sysroot path.

`http-smoke.js PACKAGE_DIR` runs an ordinary loopback HTTP server and checks
fetch and request using the selected Node interpreter and the staged package.
For a loader generated with a matching `--install-dir`, pass `loader.js` as the
third argument; this checks the loader's HTTP fetch. A Node binary configured
with that external builtin must additionally be built and tested separately.
