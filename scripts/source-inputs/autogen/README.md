# Common AutoGen libopts source

The native AutoGen package supplies a generated libopts tearoff. Prepare it
using a shared export of current Ports, the installed native package and the
same selected native pkgsrc configuration. This checks the complete distinfo
and patch inventory against the package's `+BUILD_VERSION`, relevant
configure arguments and options against `+BUILD_INFO`, and installed package
files through `pkg_admin check`. A metadata-only recipe change does not require
rebuilding the package. The output contains the complete tearoff and its
upstream licenses. It is suitable as source for a separately configured target
library; target Guile is not needed for that use.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/autogen/source.py \
  --sdk-source "$SDK_SOURCE" --export "$SHARED_EXPORT" \
  --host-prefix "$HOST_PREFIX" --pkg-admin "$HOST_PREFIX/sbin/pkg_admin" \
  --make "$HOST_PREFIX/bin/bmake" --makeconf "$HOST_MAKECONF" \
  --git "$GIT" --patch "$HOST_PREFIX/bin/gpatch" --output "$WORK/libopts-source"
```

Pass the same arguments with `--source` in place of `--output` to verify an
existing prepared source against the selected installed package. For later
OS builds, `source.py --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source
--source "$WORK/libopts-source" --patch "$HOST_PREFIX/bin/gpatch"` checks the
payload and current common source, patchset and generation recipe without an
installed AutoGen package. Recipe metadata such as comments and revision are
excluded; configure controls and options remain part of the selection. `--make-arg` passes a selected pkgsrc variable as a
separate argument when the native configuration needs it. `--package` selects
one installed version if more than one package of the same upstream version is
present. The export must be created by `scripts/pkgsrc-shared-export.py` from
the current common source. The helper does not change the installed package.
