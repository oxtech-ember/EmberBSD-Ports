# Common libcbor source for the base system

Prepare the current Ports libcbor archive and its complete pkgsrc patch set for
OS integration. Select the SDK and native tools. The output is a new absolute
directory and can be reused with matching source inputs.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/libcbor/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTDIR/libcbor-0.14.0.tar.gz" --patch "$PATCH" \
  --output "$WORK/libcbor-source" --scoped-identity --pkgsrc-export "$SHARED_EXPORT"
```

Use `verify-source --source "$WORK/libcbor-source"` with the same SDK and Git;
when inputs differ, supply `--archive`, `--patch`, and `--pkgsrc-export` to
compare the current prepared payload. The OS owns native integration and ABI.
