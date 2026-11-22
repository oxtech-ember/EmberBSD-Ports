# NNG IPC checks

The ordinary `net/nng` recipe provides the headers and shared library used by KiCad. Its API check opens a request and reply socket, sends binary data over a temporary local socket and checks the returned bytes. The target needs write access to its temporary directory.

Compile the check with the selected SDK compiler, target sysroot, headers and library, then run the binary on the corresponding EmberBSD target.

```sh
"$target_cc" --sysroot="$sysroot" -I"$sysroot/usr/pkg/include" \
    tests/ipc-smoke.c -L"$sysroot/usr/pkg/lib" -Wl,-rpath,/usr/pkg/lib \
    -lnng -o "$work/ipc-smoke"
```

Run the packing checks with the SDK Python. Pass `--without-docs` with the archive of a build that selected `-doc`. Run the recipe check once per native or cross configuration being exercised.

```sh
"$python" tests/check-docs.py "$package"
"$python" tests/check-host-tool.py --pkgsrc "$pkgsrc" --makeconf "$makeconf" --bmake "$bmake"
```

On EmberBSD AArch64, the installed NNG 2.1.0 library passed 26 checks with the IPC program. A separate run compiled KiCad 10.0.8's `KINNG_REQUEST_SERVER` against the real wxWidgets base library, received a reply from its callback and checked orderly shutdown. [Package details](../../../profiles/common-graphics/cross/nng.md)
