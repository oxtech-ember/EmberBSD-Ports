# Common OpenSSL source for the base system

Prepare the current Ports OpenSSL archive and its complete pkgsrc patch set for
OS integration. Use the selected SDK and native tools. The output is a new
absolute directory and can be reused by consumers with the same source inputs.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/openssl/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTDIR/openssl-4.1.0.tar.gz" --patch "$PATCH" \
  --output "$WORK/openssl-source" --scoped-identity --pkgsrc-export "$SHARED_EXPORT"
```

Use `verify-source --source "$WORK/openssl-source"` with the same SDK and Git;
when inputs differ, supply `--archive`, `--patch`, and `--pkgsrc-export` as
needed to compare the current prepared payload. Source preparation does not
establish the base system ABI or runtime compatibility.
