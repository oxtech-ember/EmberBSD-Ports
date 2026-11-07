# Common littlefs source

This owner prepares and verifies the pinned `devel/littlefs` source from the
canonical Ports export, using the selected SDK prepared-source API. Both the
kernel integration and host image builder consume this same upstream source;
the OS keeps its native filesystem/VFS and block-device interfaces.

The current upstream release is v2.11.3, pinned to tag
`refs/tags/v2.11.3` at commit `6cb4e86540eca0d9ba62500a298385c9d863c8be`.
The recipe uses GitHub's tag archive (`archive/refs/tags/v2.11.3.tar.gz`),
not a release asset. The upstream BSD-3-Clause license and complete source
tree are retained. No device policy or OS adapter is provided here.

The local `lfs.c` patch keeps CTZ blocks reachable during filesystem traversal
while a regular file remains open after unlink or rename-overwrite. Without
this, allocation under pressure can reuse blocks still referenced by the open
descriptor. `tests/open-unlinked.c` exercises both operations against the
actual library on a RAM flash model, and also checks inline write/sync/unlink.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/littlefs/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/littlefs-2.11.3.tar.gz" \
  --patch "$HOST_PREFIX/bin/gpatch" --output "$WORK/littlefs-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/littlefs/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/littlefs-source" --patch "$HOST_PREFIX/bin/gpatch"
```

`WORK` must already exist and the output must be new. The prepared source
includes upstream tests and documentation as well as the library C files and
headers, allowing consumers to select the needed source files without a
second vendored copy.
