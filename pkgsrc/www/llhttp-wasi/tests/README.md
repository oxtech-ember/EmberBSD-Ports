# WASI reactor checks

Run `consumer.js` using the selected Node runtime against each staged or
installed `llhttp.wasm` and `llhttp_simd.wasm`. It checks imports, exports and
parses an ordinary HTTP response.

With the selected host prefix in `H`, test that an undeclared import is
rejected (run from this directory):

```sh
if "$H/bin/clang" --target=wasm32-wasip1 --sysroot="$H/wasi" \
  -fuse-ld="$H/bin/wasm-ld" -mexec-model=reactor \
  -Wl,--allow-undefined-file=../files/wasm-imports.txt -Wl,--export=run \
  unexpected.c -o unexpected.wasm; then
  echo 'unexpected undefined symbol was accepted' >&2
  exit 1
fi
```
