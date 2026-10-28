# Common nvi source

Prepare the complete `editors/nvi` archive and effective Ports patch set for
native OS consumers using the selected SDK source preparation API. The native
base uses the DB1 API and its own build, installation and manual; the package
uses Berkeley DB 18. This helper does not build or install either consumer.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/nvi/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/nvi-1.81.6.tar.bz2" --patch "$HOST_PREFIX/bin/gpatch" \
  --scoped-identity --output "$WORK/nvi-source"
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/nvi/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/nvi-source" --patch "$HOST_PREFIX/bin/gpatch" \
  --archive "$DISTFILES/nvi-1.81.6.tar.bz2"
```

The source includes upstream and NetBSD notices and the BSD license. Generated
headers are placed in the consumer's object directory by the common generator.
When effective inputs change, verification compares a freshly prepared payload.
