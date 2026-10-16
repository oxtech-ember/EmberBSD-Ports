# ConsoleKit registration privilege

The `consolekit-2.0.0nb5` recipe enforces the documented privileged registration API.
`OpenSessionWithParameters` requires verified bus credentials and UID zero.
Both UID and PID lookups must succeed before the manager creates a session leader.
Failed lookups return a general error. Other users receive an insufficient-permission error.
The shipped default D-Bus policy also denies this method.
The existing root policy retains access. Ordinary `OpenSession` is unchanged.

`ck-launch-session` exits with status one when connector allocation or registration fails.
It prints an explicit error and never executes the command or default shell in that case.
It keeps the original method selection: no `--service` uses `OpenSession`;
`--service` uses the privileged parameterized API. It does not silently discard that argument.
Successful registration retains the existing cookie, runtime directory and child-status behavior.

## Existing clients

Pinned `tools/ck-launch-session.c` selects the parameterized API only for `--service`.
Pinned `pam-ck-connector.c` sends the user's UID, display paths and locality through that API.
Root PAM callers and root `--service` callers retain their existing request paths.
A nonroot `--service` call must fail under the documented privileged contract.
An ordinary successful nonroot launcher without `--service` retains `OpenSession`.

The earlier [CM5 launcher test](../../cross/desktop-session.md) ran as root.
Its seven successful registration and child-status cases remain covered by host control tests.
This change does not claim a renewed target PAM or ordinary-user login pass.

## Host regression

Use a nonroot native host with GNU GCC16, Clang, GLib/GIO, libdbus, D-Bus and pkgsrc digest.
The output receipt directory must not exist.

```sh
CC=/absolute/native/gcc \
SANITIZER_CC=/absolute/native/clang \
PKG_CONFIG=/absolute/native/pkg-config \
CPPCHECK=/absolute/native/cppcheck \
DIGEST=/absolute/pkgsrc/digest \
DBUS_DAEMON=/absolute/native/dbus-daemon \
ruby probes/plasma-mobile/toolkit/tests/consolekit/privilege.rb \
    /absolute/distfiles/ConsoleKit2-2.0.0.tar.gz /absolute/new-receipt
```

The runner verifies the pinned upstream archive and ordinary recipe checksums before extraction.
Its baseline is commit `a7b358eceafd02440b3c0dbcc09eeb61bdcbf009`.
The original [source, hash and license](README.md#source-and-license) remain unchanged.

The manager fixture executes the real credential lookup and both registration entry points.
Only credential transport, invocation sender and the session-creation boundary are controlled.
Its 38 checks cover root, two nonroot UIDs, UID/PID query failures, missing sender/proxy,
forged session properties, unchanged ordinary registration and error-before-creation behavior.
The credential fixture preserves GIO's nonnull value/error contract for path analysis.
The baseline fails 35 checks. The candidate must pass all checks.

The separate policy fixture loads the actual shipped `ConsoleKit.conf` into a private D-Bus daemon.
It grants this test UID only service-name ownership so the test service can receive calls.
It adds no ConsoleKit method permission. Actual nonroot Unix credentials must receive AccessDenied
for the parameterized method while ordinary OpenSession reaches the test handler.
The root allow stanza is also checked. Actual root bus credentials are not simulated by this policy test.

The launcher fixture compiles the complete patched launcher, with real GLib, libdbus, fork, wait and exec.
Only the registration connector is controlled. Real child scripts write sentinels and require the fixture cookie.
Twelve cases combine allocation failure, explicit denial and failure without a D-Bus error
with ordinary/`--service` requests and command/default-shell execution.
Every failure must return one, print an error and leave the child sentinel absent.
Seven successful controls retain success, exit 42, signal status, shell, service and CLI error behavior.
The baseline fails all twelve registration-failure cases. The candidate passes all nineteen cases.

GCC16 uses `-Wall -Wextra -Werror` and actual `-fanalyzer -c` passes.
Cppcheck compares all baseline and candidate findings without suppressing categories.
The inherited external GLib `gstrfuncs.h:568` finding remains unchanged.
Clang ASan/UBSan runs all three candidate fixtures. Sanitizer diagnostics fail the runner.
This macOS sanitizer run is not a Valgrind pass.
Receipts retain exact source, patch hashes, tool versions, license and diagnostic logs.
The runner removes temporary trees, executables and its own private bus.

## Remaining gates

UID zero authorizes the privileged API; it does not prove kernel TTY or VT entitlement.
Native devices still require verified caller/session ancestry, real console ownership and active-seat checks.
The device backend remains `none`. Native DRM, wscons revocation and VT_PROCESS remain separate work.
Full target translation-unit compilation needs cross-built D-Bus and GLib development inputs.
Cross-build target tests on the developer host. VM and boards only execute the prepared results.
No development tools are installed on the acceptance target.
Target system-bus policy, real PAM/login, device handoff and full desktop acceptance remain pending.
