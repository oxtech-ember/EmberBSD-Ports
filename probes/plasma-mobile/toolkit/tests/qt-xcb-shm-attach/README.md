# Qt XCB System V shared memory contract

This test compiles the actual `QXcbBackingStoreImage::createSystemVShmSegment`
definition from a Qt 6.12.0 source tree. It links that function to a small fake
System V/XCB backend. The backend models the observed NetBSD behavior: XCB
cannot attach a segment after `IPC_RMID` has removed it from lookup.

The test covers successful retained and test-only attachments, `shmget` and
`shmat` failures, XCB attach rejection, segment and error cleanup, and the
`shmat` diagnostic's original errno. It tests the extracted function's effects,
not source text order. Run it with the matching source and a native Clang build:

```sh
CXX=/absolute/native/clang++ ruby source-contract.rb \
  /absolute/qtbase-everywhere-src-6.12.0/src/plugins/platforms/xcb/qxcbbackingstore.cpp \
  /absolute/new-output
```

ASan and UBSan are enabled. A passing contract does not replace execution on
NetBSD with the real X server and kernel, which remain separate runtime checks.
