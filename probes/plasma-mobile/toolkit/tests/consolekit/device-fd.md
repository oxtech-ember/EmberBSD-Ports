# ConsoleKit device reply ownership

The `consolekit-2.0.0nb4` patch keeps the canonical device FD in `CkDevice`.
`TakeDevice` appends a duplicate to a new `GUnixFDList` and checks the result.
Its reply uses the returned handle index and the actual device's inactive state.
The method releases its local list reference after the generated completion.
FD zero is valid. Only negative FDs fail the canonical-FD check.

A missing FD or failed append removes and unreferences the newly created device.
A duplicate request remains an error until `ReleaseDevice` removes the existing device.
Foreign controllers cannot create or export devices.
This patch does not enable the `udev` backend or change device pause/resume operations.

## Ownership contract

The source is the pinned [ConsoleKit2 2.0.0](https://github.com/ConsoleKit2/ConsoleKit2/tree/2.0.0) archive.
Its source hash, license and ordinary recipe checksum requirements are in the [foundation document](README.md).
The runner generates `ck-session-generated.c` from the original Session XML.
It uses the same namespace and interface prefix as `src/Makefile.am`.
The generated `console_kit_session_complete_take_device()` returns no status.
It transfers the invocation to GIO and borrows the outgoing FD list.
GIO retains the list in the reply message; the caller must release its own reference.
`g_unix_fd_list_append()` duplicates the FD; `new_from_array()` takes its ownership instead.

The old method transferred the canonical FD to `new_from_array()` and leaked the list's original reference.
That leak also masked premature canonical-FD closure after reply teardown.
The patch fixes both ownership errors together.

GIO handles reply-send failures internally. The generated completion cannot report them to this method.
The patch makes no delivery or application-acknowledgment claim.
Transport failure after completion still needs ordinary controller-disconnect cleanup.
This fixture does not execute the complete daemon's controller-vanished handler.

## Host regression

Set native GNU GCC16, Clang, GLib/GIO, pkg-config, D-Bus, gdbus-codegen and pkgsrc digest paths.
The receipt directory must not exist.

```sh
CC=/absolute/native/gcc \
SANITIZER_CC=/absolute/native/clang \
PKG_CONFIG=/absolute/native/pkg-config \
CPPCHECK=/absolute/native/cppcheck \
DIGEST=/absolute/pkgsrc/digest \
DBUS_DAEMON=/absolute/native/dbus-daemon \
GDBUS_CODEGEN=/absolute/native/gdbus-codegen \
ruby probes/plasma-mobile/toolkit/tests/consolekit/device-fd.rb \
    /absolute/distfiles/ConsoleKit2-2.0.0.tar.gz /absolute/new-receipt
```

The runner verifies the pinned archive and every recipe patch with ordinary pkgsrc checksums.
It extracts the real device-list, TakeDevice and ReleaseDevice functions.
Only the unused incoming FD-list parameter gets a fixture-only unused annotation.
Device construction and generated-object-to-private-session lookup are controlled boundaries.
The fixture uses actual GObject references, GUnixFDList operations and generated GDBus method completion.
An owned private D-Bus daemon transports FDs between two real GDBus connections.
It never uses the user's bus. The runner terminates and reaps its own daemon on exit.

The 65 checks cover active/inactive values, canonical/received FD lifetimes, local list finalization,
foreign controllers, duplicate requests, new-device rollback, FD zero and twenty repeated release cycles.
A real FD-list append under a temporary zero soft FD limit produces EMFILE.
The fixture restores that limit before sending the error reply.
A preseeded real FD list checks that the reply uses the append index.
An actual `NO_REPLY_EXPECTED` call checks the generated completion's alternate cleanup path.
The baseline omits the session patch; its selected methods match upstream and fail nine checks.
The candidate applies every recipe patch and must pass all checks.

GCC16 compiles the fixture and generated code with `-Wall -Wextra -Werror`.
Its path analyzer compiles the fixture with `-fanalyzer`.
Cppcheck compares baseline and candidate findings without category suppression.
The inherited GLib `gstrfuncs.h:568` finding is unchanged; its owner and scope are in the foundation document.
The candidate runs with Clang ASan/UBSan. Sanitizer diagnostics fail the runner, including child-process diagnostics.
This macOS execution is not a Valgrind pass.
Receipts keep generated code, extracted methods, exact commands, hashes, licenses and logs.
Temporary source trees, executable files and the test daemon are removed.

## Acceptance boundary

This is a native host GDBus contract test, not a target ConsoleKit translation-unit build.
It does not test NetBSD device classification, DRM authority, wscons revocation or VT handoff.
It does not prove daemon controller cleanup after bus disconnection.
Target compilation needs the cross-built GLib and D-Bus development inputs.
The [foundation gates](README.md#remaining-gates) remain mandatory before backend activation.
