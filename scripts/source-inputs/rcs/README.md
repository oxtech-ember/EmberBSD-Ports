# Common rcs source

Prepare the effective `devel/rcs` source from the Ports export, including
all recipe patches, using the selected SDK source-preparation API. This source
is suitable for OS integration only after its native behavior and OS-specific
patches have been reconciled; preparation alone does not establish that.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/rcs/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/rcs-5.10.1.tar.lz" --patch "$HOST_PREFIX/bin/gpatch" --lzip "$HOST_PREFIX/bin/lzip" \
  --scoped-identity --output "$WORK/rcs-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/rcs/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source --source "$WORK/rcs-source" \
  --archive "$DISTFILES/rcs-5.10.1.tar.lz" --patch "$HOST_PREFIX/bin/gpatch" --lzip "$HOST_PREFIX/bin/lzip"
```

The output must not exist. The verifier checks recipe identity, all patches,
and the prepared tree. This operation does not install or build a package.

Scoped identity reuses equivalent effective inputs. If those or the owner
change, verification compares a freshly prepared payload using the explicit
archive, patch, and lzip. Legacy records use the same comparison when needed.
