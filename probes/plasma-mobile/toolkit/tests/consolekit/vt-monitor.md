# NetBSD actual-VT monitor

The local `consolekit-2.0.0nb3` recipe polls the actual NetBSD console state.
It does not enable server-managed devices or add a display manager.
It retains the [session foundation guards](README.md).

## Kernel contract

EmberBSD `sys/dev/wscons/wsdisplay.c` implements `WSDISPLAYIO_GETACTIVESCREEN`
on the display status device. It returns the zero-based current focus index.
`sys/dev/wscons/wsdisplay_compat_usl.c` implements `VT_GETACTIVE` on the
console/configuration device. It returns that same index plus one.
ConsoleKit already has the console descriptor and uses this one-based API.
A value of zero means there is no active screen.

This kernel has no `WSDISPLAYIO_GETSCREEN` enumeration operation.
`VT_GETSTATE` reports opened screens, not every configured screen.
Enabled gettys do not describe the configured wscons screens.
The status stream's `WSCONS_EVENT_SCREEN_SWITCH` is emitted before switch completion.
It can precede an `EBUSY` failure. Its requested screen is not committed state.

The NetBSD monitor therefore uses one GLib timeout and actual `VT_GETACTIVE` reads.
The nominal observation interval is 100 ms. Scheduling can delay observation.
The monitor needs no screen enumeration, getty count or fixed screen maximum.
New and sparse active screen numbers use the same kernel query.
This does not claim immediate secure device revocation.
That requires coordinated ConsoleKit device and libopeninput lifecycle acceptance.

## State and ownership

The NetBSD reader returns false on ioctl failure or a nonpositive active number.
It leaves the caller's previous output unchanged on failure.
The public monitor query reads fresh kernel state and returns an error on failure.
The already-active check also reads fresh state before requesting activation.
An accepted activation request does not itself generate an active notification.

A polling failure emits unknown VT zero once and logs the failed transition.
The monitor continues to query and can recover to a confirmed actual VT.
Unknown VT zero has no console device path.
The unchanged seat consumer cannot match it to a session.
It removes the active session through `change_active_session(NULL)` and
`ck_session_set_active(FALSE, TRUE)`.

The timeout holds no persistent reference to the monitor.
Finalization removes the timeout before closing its console descriptor.
The callback holds a temporary reference across signal delivery.
This protects a callback whose consumer releases the last external owner.
Other operating systems retain their previous monitor source paths.

## Host regression

Use the same explicit native tool variables as the [foundation test](README.md).
Also provide `unifdef` in PATH or set `UNIFDEF` to its executable.

```sh
ruby probes/plasma-mobile/toolkit/tests/consolekit/vt-monitor.rb \
    /absolute/distfiles/ConsoleKit2-2.0.0.tar.gz \
    /absolute/new-vt-receipt
```

The runner verifies the original archive and all normal recipe patch checksums.
It applies patches with zero fuzz. The archive URL, hashes and license stay unchanged.
The baseline is the committed session foundation `74f04e0105d96e5ae370db0b524b5a9f4e3c9be6`.
It compiles the complete upstream monitor with the selected NetBSD branch.
It extracts the actual NetBSD reader and the seat/session consumer functions.
The host fixture uses real GLib, GObject, timeouts, signal delivery and source removal.
Only kernel console transport and generated session property/device boundaries are controlled.
Host headers and ABI are used. This is not a complete target translation unit.

The 26 cases cover sparse/current/new VTs, fresh queries, activation errors,
failed ioctl reads, absent screens, inactive propagation, recovery, duplicate events,
source removal and release of the last owner from inside a signal callback.
The baseline fails 16 cases. The candidate must pass all cases.
`unifdef -U__NetBSD__` compares the other operating-system source selection.
The comparison ignores blank lines and directive spacing, but keeps all C tokens.

GCC16 path analysis and Clang ASan/UBSan cover the fixture.
No analyzer or warning category is suppressed.
Complete upstream monitor code still emits its existing GObject deprecation warnings.
The unchanged extracted consumers also have unused parameter warnings.
Cppcheck compares baseline and candidate findings.
It retains the inherited GLib `gstrfuncs.h:568` pointer-assignment warning.
It also finds the existing Solaris `handle_vt_active` uninitialized `num` path.
That non-NetBSD defect remains owned by a separate ConsoleKit portability follow-up.
The patch preserves that operating-system path instead of changing it here.
macOS ASan/UBSan execution is not a Valgrind pass.

The receipt retains source snapshots, exact commands, versions and hashes.
Temporary sources and executables are removed on exit.
Full target compilation requires target GLib and D-Bus development inputs.
Actual system D-Bus, VT switching, device revocation, SDDM and physical graphics
acceptance remain separate gates.
