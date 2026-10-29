# Installed LIEF API check

Run this positive consumer with the selected host SDK. It creates an ordinary
short-lived certificate and signature locally; the private key stays in the
temporary directory and is removed after the test. `LIEF_PREFIX` is the
installed prefix (or staged prefix); `HOST_PREFIX` selects native build tools.
For a staged library, include its `lib` directory in the loader search path.

```sh
HOST_PREFIX=/absolute/host-tools/llvm
LIEF_PREFIX=/absolute/installed-or-staged-prefix
SDK_SOURCE=/absolute/EmberBSD-SDK
LOCK_ROOT=/absolute/EmberBSD/tmp/obj
MACOS_SDK=/absolute/macOS.sdk
export PATH="$HOST_PREFIX/bin:$HOST_PREFIX/sbin"
work=$("$HOST_PREFIX/bin/gmktemp" -d)
trap '"$HOST_PREFIX/bin/grm" -rf "$work"' EXIT HUP INT TERM
"$HOST_PREFIX/bin/openssl" req -x509 -newkey rsa:2048 -nodes \
  -keyout "$work/key.pem" -out "$work/cert.pem" -days 1 \
  -subj '/CN=LIEF test' >/dev/null 2>&1
"$HOST_PREFIX/bin/gprintf" abc > "$work/input"
"$HOST_PREFIX/bin/openssl" dgst -sha256 -sign "$work/key.pem" \
  -out "$work/signature" "$work/input"
"$HOST_PREFIX/bin/cmake" -S . -B "$work/build" \
  -DCMAKE_CXX_COMPILER="$HOST_PREFIX/bin/clang++" \
  -DCMAKE_MAKE_PROGRAM="$HOST_PREFIX/bin/gmake" \
  -DCMAKE_OSX_SYSROOT="$MACOS_SDK" \
  -DCMAKE_CXX_FLAGS="--ld-path=$HOST_PREFIX/bin/ld64.lld" \
  -DCMAKE_PREFIX_PATH="$LIEF_PREFIX;$HOST_PREFIX" \
  -DCMAKE_CXX_LINKER_LAUNCHER="$HOST_PREFIX/bin/python3.15;$SDK_SOURCE/scripts/link-launcher.py;--lock-root;$LOCK_ROOT;--context;$LOCK_ROOT/coordination/heavy-link;--"
"$HOST_PREFIX/bin/cmake" --build "$work/build"
DYLD_LIBRARY_PATH="$LIEF_PREFIX/lib" "$work/build/lief_header_link"
DYLD_LIBRARY_PATH="$LIEF_PREFIX/lib" "$work/build/lief_consumer" \
  "$work/cert.pem" "$work/signature"
```

Run from this directory on macOS using the selected SDK and prefix. The
consumer checks the byte-buffer certificate parser before other LIEF crypto
operations, then checks hash, UTF, dates, certificate and RSA attributes, and
one valid signature. It does not claim target execution or runtime acceptance.

The header-link consumer checks host-version constructors after system headers
and a shared-library result template. For a cross build, compile and link it
with the selected target SDK and staged LIEF; execute only on the target.
