# Common libevent source

This owner prepares the effective `devel/libevent` source from the canonical
Ports export for both native OS and package consumers. It uses the selected
SDK source-preparation API, the archive and the complete patch set in that
export. Preparation runs the existing pkgsrc exporter once. Verification
checks the prepared tree and the common export-input identity without another
full export. Changed export inputs conservatively require preparation again;
an unrelated Git commit with identical inputs does not.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/libevent/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/libevent-2.1.13-stable.tar.gz" \
  --patch "$HOST_PREFIX/bin/gpatch" --output "$WORK/libevent-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/libevent/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/libevent-source"
```

The native signal callback lifetime regression builds the prepared source in a
separate work directory. Select native tools and, when supported, enable
ASan/UBSan in the compiler binding for both compilation and linking. The last
argument is the host SDK path (use an empty string where none is needed).
This exercises host execution, not the target runtime.

```sh
CC="$NATIVE_CC" AR="$HOST_PREFIX/bin/llvm-ar" RANLIB="$HOST_PREFIX/bin/llvm-ranlib" \
  "$HOST_PREFIX/bin/mksh" profiles/common-build-tools/tests/libevent-signal-lifecycle.sh \
  "$WORK/libevent-source" "$WORK/signal-test" "$HOST_PREFIX/bin/cmake" \
  "$HOST_PREFIX/bin/gmake" "$HOST_SYSROOT"
```

`GIT` is an absolute Git executable used for source inspection; `WORK` must
already exist and the output must be new. The shared SDK records the recipe
input identity and the complete prepared tree. Verification refuses changed
inputs or payloads. This prepares source only; it does not build a package,
sysroot or target library.

The real owner regression uses the same selected inputs and keeps its
scratch tree under the caller's workspace:

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/libevent/test-source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" --patch "$HOST_PREFIX/bin/gpatch" \
  --archive "$DISTFILES/libevent-2.1.13-stable.tar.gz" --work-dir "$WORK"
```
