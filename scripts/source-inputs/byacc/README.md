# Common byacc source

Prepare the effective `devel/byacc` source from the Ports export, including
all recipe patches, using the selected SDK source-preparation API. This source
is suitable for OS integration only after its native behavior and OS-specific
patches have been reconciled; preparation alone does not establish that.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/byacc/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/byacc-20260126.tgz" --patch "$HOST_PREFIX/bin/gpatch" \
  --output "$WORK/byacc-source" --scoped-identity
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/byacc/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source --source "$WORK/byacc-source" \
  --patch "$HOST_PREFIX/bin/gpatch"
```

The scoped identity is opt-in for compatibility with existing consumers;
without it, preparation retains the historical export-wide identity.
The output must not exist. The verifier checks recipe identity, all patches,
and the prepared tree. This operation does not install or build a package.
When source inputs or the owner have changed, also supply the current
`--archive`; the verifier prepares the current expected payload and compares
it with the unchanged record.

A scoped record needs one pkgsrc export to compute the effective recipe.
Callers that verify several sources in one run can make that export once
with `scripts/pkgsrc-shared-export.py DIR --sdk-source ... --git ... --patch ...`
and pass `--pkgsrc-export DIR` to `verify-source`. The libarchive, libevent,
Texinfo, RCS, diffutils, GNU grep and E-Kermit owners accept the same option.
Each owner refuses the export unless the Ports commit, the pinned pkgsrc
commit, the overlay inputs and the patch tool still match its receipt.
