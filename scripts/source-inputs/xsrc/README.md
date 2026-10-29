# NetBSD X11 source set (xsrc)

This owner prepares the X11 sources consumed by the OS build when a release
profile selects `MKX11=yes`. EmberBSD has no X11 source repository of its own,
so the input is the NetBSD 11.0 `xsrc.tgz` release set, pinned here by SHA512,
BLAKE2s and size. The OS pins the same archive in `ember/source.json`
(`x11SourceSha512`), and the SDK release builder checks that both pins agree.

Fetch the archive with the Ports `fetch` tool from the host prefix, not with a
system downloader, then prepare and verify the tree:

```sh
"$HOST_PREFIX/bin/fetch" -o "$DISTFILES/xsrc.tgz" \
  https://cdn.netbsd.org/pub/NetBSD/NetBSD-11.0/source/sets/xsrc.tgz
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/xsrc/source.py \
  --sdk-source "$SDK_SOURCE" prepare \
  --archive "$DISTFILES/xsrc.tgz" --output "$WORK/xsrc-source" \
  --patch "$HOST_PREFIX/bin/gpatch"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/xsrc/source.py \
  --sdk-source "$SDK_SOURCE" verify-source --source "$WORK/xsrc-source"
```

The prepared tree is the `usr/xsrc` directory of the set. The set records CVS
metadata as hard links; those `CVS` directories are omitted, which needs an
SDK with `sourceprep.ARCHIVE_SKIP_DIRECTORIES_API == 1`.

`patches/` holds EmberBSD fixes to the set, applied in name order with
`-p0` from the xsrc root by the absolute patch tool given to `prepare`
(no fuzz, no backups; a leftover `.orig` or `.rej` is refused). Each
patch's SHA256 is part of the identity. They fix code that the OS build's
`-Werror` rejects with a current Clang:

- `libxcb-read-setup-header.patch`: `read_setup` reads the fixed setup
  header into a stack object before allocating the full reply, instead of
  allocating `xcb_setup_t` with the size of the shorter generic header
  (`-Walloc-size`).
- `mesa-trivially-destructible.patch`: `HAS_TRIVIAL_DESTRUCTOR` uses
  `__is_trivially_destructible` when Clang has it, instead of the
  deprecated `__has_trivial_destructor` (`-Wdeprecated-builtins`).
- `mesa-sw-winsys-prototypes.patch`: the gallium software winsys table
  gets one prototyped constructor per winsys instead of an unprototyped
  `create_winsys()` called with different arguments
  (`-Wdeprecated-non-prototype`, `-Wstrict-prototypes`).
- `mesa-glx-sgix-choose-fbconfig.patch`: `glXChooseFBConfigSGIX` forwards
  to `glXChooseFBConfig` instead of being an alias of it. The SGIX
  prototype takes a non-const attribute list, and Clang rejects an alias
  whose type differs from the aliased function.
The identity covers the pin and this owner; verification refuses a changed
receipt or payload. `pin` prints the identity without reading an archive.
This prepares source only; it does not build X11 or any set.

The owner regression (about 1 GiB of scratch space):

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/xsrc/test-source.py \
  --sdk-source "$SDK_SOURCE" --archive "$DISTFILES/xsrc.tgz" \
  --patch "$HOST_PREFIX/bin/gpatch" --work-dir "$WORK"
```

The patch regression compiles each fixed construct to assembly with the
target Clang and the OS build's `-Werror` (alias types are checked only
when code is generated); it passes on a prepared tree and, with
`--expect-failure`, every case fails on an unpatched tree. `--sysroot` is a
target DESTDIR with the base and the installed X11 headers:

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/xsrc/test-clang.py \
  --source "$WORK/xsrc-source" --clang "$HOST_PREFIX/bin/clang" --sysroot "$DESTDIR"
```
