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
  --archive "$DISTFILES/xsrc.tgz" --output "$WORK/xsrc-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/xsrc/source.py \
  --sdk-source "$SDK_SOURCE" verify-source --source "$WORK/xsrc-source"
```

The prepared tree is the `usr/xsrc` directory of the set. The set records CVS
metadata as hard links; those `CVS` directories are omitted, which needs an
SDK with `sourceprep.ARCHIVE_SKIP_DIRECTORIES_API == 1`. No patches are
applied by this owner.
The identity covers the pin and this owner; verification refuses a changed
receipt or payload. `pin` prints the identity without reading an archive.
This prepares source only; it does not build X11 or any set.

The owner regression (about 1 GiB of scratch space):

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/xsrc/test-source.py \
  --sdk-source "$SDK_SOURCE" --archive "$DISTFILES/xsrc.tgz" --work-dir "$WORK"
```
