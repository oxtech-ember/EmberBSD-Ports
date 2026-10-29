# Common Perfetto source

`source.py` prepares the Perfetto source selected by the common pkgsrc owner,
including its complete patch inventory. It uses the selected SDK sourceprep
API and verifies the archive against the recipe's distinfo.

Select absolute paths for the SDK source, Git, patch executable, archive and
a new output directory:

```sh
python3 -B source.py --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$ARCHIVE" --patch "$PATCH" --output "$OUTPUT" --scoped-identity
python3 -B source.py --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$OUTPUT" --archive "$ARCHIVE" --patch "$PATCH"
```

Preparation and verification check source identity and archive integrity;
they do not build or validate a target runtime.

The focused `test-portability.py` regression uses the prepared source, selected
host C++ compiler and Python, and a generated Perfetto build-flags directory.
It checks Murmur tail values, typed-proto rejection and the default/scoped
host generator launcher; pass `--help` for the explicit input paths.
