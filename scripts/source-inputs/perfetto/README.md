# Common Perfetto source

`source.py` prepares the Perfetto source selected by the common pkgsrc owner,
including its complete patch inventory. It uses the selected SDK sourceprep
API and verifies the archive against the recipe's distinfo.

Select absolute paths for the SDK source, Git, patch executable, archive and
a new output directory:

```sh
python3 -B source.py --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$ARCHIVE" --patch "$PATCH" --output "$OUTPUT"
python3 -B source.py --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$OUTPUT" --archive "$ARCHIVE" --patch "$PATCH"
```

All three commands accept `--pkgsrc-export "$EXPORT_ROOT" --export-patch "$EXPORT_PATCH"`
to use a shared export authenticated against current inputs. `EXPORT_ROOT` is
the directory containing `pkgsrc-export.json` and `pkgsrc/`. The caller holds
its `.pkgsrc-update.lock` shared for the entire access; an export writer takes
that lock exclusively. The selector does not acquire this lock. Without a shared
export, preparation creates an export.

Preparation and verification that replays a changed receipt check the archive
hashes, patch inventory and checksums, and prepared tree. The current-receipt
fast path checks the tree and effective identity without rereading the archive.
`refresh-source` uses the same verification, which may take either path, then
updates only the source receipt; the caller holds exclusive source ownership.
These operations do not build or validate a target runtime.

The focused `test-portability.py` regression uses the prepared source, selected
host C++ compiler and Python, and a generated Perfetto build-flags directory.
It checks Murmur tail values, typed-proto rejection and the default/scoped
host generator launcher; pass `--help` for the explicit input paths.
