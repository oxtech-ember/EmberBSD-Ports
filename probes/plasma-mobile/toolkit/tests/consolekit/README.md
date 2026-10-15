# ConsoleKit session foundation

The local `consolekit-2.0.0` recipe carries focused source patches.
They do not enable server-managed devices or install a display manager.
The separate [NetBSD VT monitor](vt-monitor.md) observes actual kernel console state.
The [device reply regression](device-fd.md) checks canonical FD ownership with actual host GDBus replies.

`TakeControl` now checks the caller UID after both credential lookups succeed.
Only the session owner or root can acquire or reuse control.
Only root can replace another controller with `force=true`.
The existing unsupported-backend error remains first.
Every rejected call preserves the controller and sends no success reply.

NetBSD `devname()` returns a name relative to `/dev`.
The port adds `/dev/` before the session collector resolves its VT number.
Valid nonconsole names, including `tty00` and `pts/0`, remain valid TTY paths.
Absolute names, empty path components, `.` and `..` are rejected.
Console parsing accepts only `/dev/ttyE` followed by canonical decimal digits.
It rejects signs, whitespace, suffixes, leading zeros and unsigned overflow.
It reserves one for the one-based VT number before each accumulation.
Failure leaves the caller's output value unchanged.
This parser does not establish which screens exist.

## Source and license

The original source is [ConsoleKit2 2.0.0](https://github.com/ConsoleKit2/ConsoleKit2/tree/2.0.0).
The archive URL and SHA256 remain in the toolkit source manifest.
The SHA256 is `f3f4a424f2a4fbb67696b4011caf2fd4c02e5e67c24ef1c86cecb2301bccdba4`.
The ordinary pkgsrc BLAKE2s, SHA512 and patch SHA1 checks remain required.
The archive's copyright notices and GPLv2 `COPYING` are unchanged.
The patches identify EmberBSD and AI assistance. They are not upstream submissions.

## Host regression

Use native GNU GCC16, native GLib/GIO, a native pkg-config and pkgsrc digest.
Use Clang with AddressSanitizer and UndefinedBehaviorSanitizer for execution.
Set the tool paths explicitly. The output directory must not exist.

```sh
CC=/absolute/native/gcc \
SANITIZER_CC=/absolute/native/clang \
PKG_CONFIG=/absolute/native/pkg-config \
CPPCHECK=/absolute/native/cppcheck \
DIGEST=/absolute/pkgsrc/digest \
ruby probes/plasma-mobile/toolkit/tests/consolekit/foundation.rb \
    /absolute/distfiles/ConsoleKit2-2.0.0.tar.gz \
    /absolute/new-receipt
```

The runner verifies the archive before extraction.
It verifies every recipe patch with the ordinary pkgsrc checksum checker.
It applies the patches with zero fuzz to temporary source trees.
The baseline keeps the previous recipe patches and omits the two foundation patches.
The candidate applies all recipe patches.
The runner extracts the actual credential lookup, `TakeControl` and TTY functions.
It uses real host GLib variants, error objects and string functions.
Only external credential transport and generated session accessors use fixtures.
The controlled transport models both UID and PID lookup failures.
Its assertions preserve GLib's nonnull value/error contract for path analysis.

The 53 cases cover owner, root, foreign UID, forced replacement, repeated control,
missing sender, failed credentials and the unchanged unsupported backend.
They also cover normal TTY paths, path escapes, console syntax and overflow.
The upstream baseline fails 35 cases. The candidate must pass every case.
GCC16 compiles both fixtures with `-Wall -Wextra -Werror` and `-fanalyzer`.
Cppcheck compares baseline and candidate findings without category suppression.
Native GLib 2.90 headers can report inherited `uselessAssignmentPtrArg` in
`glib/gstrfuncs.h:568`. This is external GLib code, not a ConsoleKit finding.
The runner retains both logs and rejects any change in findings.
The candidate also runs under ASan and UBSan.
macOS does not provide a supported Valgrind execution target for this fixture.
The sanitizer run is not a Valgrind pass.

The receipt retains exact commands, compiler versions, extracted functions,
source and patch hashes, the upstream license and diagnostic output.
Temporary extracted trees and executables are removed on exit.

## Remaining gates

These are host function fixtures, not complete NetBSD translation units.
Their headers, macros and ABI are those of the native host fixture.
Full target compilation needs the cross-built D-Bus and GLib development inputs.
Actual system-bus credentials and ordinary-user session registration remain untested.
NetBSD VT watching has host contracts in the separate monitor test.
Actual VT switching, wscons revocation and input close/reopen remain separate work.
The device backend remains `none`; native DRM `TakeControl` remains unsupported.
Backend activation also requires a trusted session-registration contract.
The [registration privilege patch](privilege.md) requires root for `OpenSessionWithParameters` in source and D-Bus policy.
It stops the launcher before child execution when registration fails and preserves ordinary successful `OpenSession`.
Root-supplied `unix-user`, locality, VT and display properties still do not prove native console or device entitlement.
Verify kernel PID, TTY and session ancestry separately before backend activation.
Native device work also requires checked DRM DROP/SET_MASTER and wscons revoke/reopen results.
KWin must release devices even when revoked FDs fail `fstat()` and must preserve failed resume state.
These are pending changes, not capabilities of the FD ownership patch.
No SDDM, password-login, logout, GPU or physical-device acceptance is claimed.
