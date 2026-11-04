# Common zlib source

Prepare the complete source of the current `devel/zlib` recipe, including all
patches verified against its distinfo. The source retains upstream licensing;
the OS owns ABI and platform integration. A prepared source is not a built library.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/zlib/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/zlib-1.3.2.tar.xz" --patch "$HOST_PREFIX/bin/gpatch" \
  --pkgsrc-export "$EXPORT" --export-patch /usr/bin/patch \
  --output "$WORK/zlib" --scoped-identity
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/zlib/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source --source "$WORK/zlib" \
  --patch "$HOST_PREFIX/bin/gpatch"
```

Select the archive matching the current recipe. The output must not exist.
Scoped identity allows unchanged prepared sources to survive unrelated Ports
changes; the shared export and its original patch tool can be selected explicitly.
The verifier checks the prepared tree and current effective recipe; an archive
is required if a changed owner or recipe needs payload comparison.

The NetBSD libz.so.1 offset ABI and kernel/standalone syntax can be checked
with explicitly selected compiler and OS inputs:

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/zlib/test-netbsd-abi.py \
  --cc "$HOST_PREFIX/bin/clang" --sysroot "$AMD64_SYSROOT" \
  --os-source "$OS_SOURCE" --zlib-source "$WORK/zlib"
```
