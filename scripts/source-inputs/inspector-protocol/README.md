# Common inspector protocol source

`devel/inspector-protocol` owns the pinned Gitiles commit, Git tree, normalized
archive checksums and full Ports patch set. Its source-only package installs the
same prepared tree at `share/inspector-protocol` under the selected prefix.
Node, V8 and Chromium consumers select that source explicitly and retain their
own build integration; this preparation does not establish API or runtime
compatibility for any consumer.

Prepare a new standalone tree using the selected SDK source code and tools:

```sh
"$HOST_PREFIX/bin/python3.15" -B -I -S scripts/source-inputs/inspector-protocol/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/inspector-protocol-0.0.0pre20261020.tar" \
  --patch "$HOST_PREFIX/bin/gpatch" --output "$WORK/inspector-protocol"
```

`verify-payload --source "$WORK/inspector-protocol"` checks the detached tree;
`verify-source --source "$WORK/inspector-protocol" --pkgsrc-root "$PKGSRC"`
also compares its effective recipe with the explicitly selected current
prepared pkgsrc export. Both accept `--sdk-source "$SDK_SOURCE"`. Neither
executes a command from the receipt. The output must not already exist.

For source fetching without a built SDK, use a control Python and SDK source
code. The recipe's `do-fetch` reads `INSPECTOR_FETCH_PYTHON` and
`EMBERBSD_SDK_SOURCE`; its fetch helper also accepts `--input-archive` for an
already obtained Gitiles response. The helper validates all source bytes and
file modes against the pinned Git tree before publishing the normalized tar.
