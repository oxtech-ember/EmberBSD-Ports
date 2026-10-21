# Persistent Plasma service

This opt-in rc.d service starts one automatic session for an existing non-root
account. It starts the standard installed entry:

```sh
/usr/pkg/bin/dbus-run-session -- /usr/pkg/bin/startplasma-wayland
```

The session uses the account's real HOME. It has no test controller, fixed
lifetime, automatic logout, or respawn. A normal Plasma logout stops the
service. A failed entry stops the service and retains its exit status.
A successful `start` confirms the supervisor launch. It does not prove that
KWin, Plasma, pixels, input, or a seat are ready. An entry can exit zero even
when one of its services fails. Inspect the session log and the desktop.

## Install and select an account

Install the current common Plasma packages and Perl first. The account must
already have the required device access. This service does not change device
permissions, create accounts, start ConsoleKit, select a seat implementation,
or force a graphics driver. It does not replace a display manager or qualify
physical HDMI, input, locking, or seat ownership.

Install these two files as root from a reviewed source checkout:

```sh
install -d -o root -g wheel -m 0755 /usr/pkg/libexec
install -o root -g wheel -m 0755 plasma-service.pl /usr/pkg/libexec/ember-plasma-service
install -o root -g wheel -m 0755 ember_plasma.rc /etc/rc.d/ember_plasma
```

Set these values in `/etc/rc.conf`. Replace `desktopuser` with the existing
account. Do not select root.

```sh
ember_plasma=YES
ember_plasma_user=desktopuser
```

This setting deliberately starts an unauthenticated automatic session for
that account after the rc.d `LOGIN` marker. Enable it only on a device where
this policy is intended. The service requires the existing `dbus` and
`x11_runtime` rc.d providers. It adds no authentication or session broker.

```sh
/etc/rc.d/ember_plasma start
/etc/rc.d/ember_plasma status
/etc/rc.d/ember_plasma stop
```

Use `ember_plasma=NO` to disable startup at the next boot. Stop the current
service separately. There is no automatic restart after logout or failure.

## Environment and ownership

The supervisor builds a clean environment from the passwd account. It retains
persistent HOME configuration. It does not inherit DISPLAY, a bus address,
Wayland display, library overrides, graphics overrides, or theme overrides.
The standard Plasma entry selects its own compositor and session behavior.
The service does not prestart KWin or change `KDE_FULL_SESSION`.

The root rc.d entry prepares `/var/run/ember-plasma/UID` with mode 0700 for the
selected user. The nested `runtime` directory is the session's private
`XDG_RUNTIME_DIR`. Existing unsafe directories or metadata cause failure.
The private log is `$HOME/.local/state/ember-plasma/session.log`. Status and
owned-process records remain in the private runtime state. Do not publish
these records or their private session identifiers.

A private lock prevents concurrent starts. Status verifies the supervisor's
UID, birth time and command. Stop writes a generation-specific request; it
never signals a PID read from a file. The supervisor signals only its live,
unreaped child group or processes with two fresh matching UID, birth-time and
private-marker observations. It allows six seconds for TERM. Forced KILL
makes cleanup fail. Cleanup has a 12-second budget and a two-second final
reap budget. The stop caller has a 20-second deadline. Startup has a bounded
ownership handshake and a 30-second parent acknowledgement deadline.

## Host contract

Run the focused test with Ruby 4 and a new work directory under an existing
parent:

```sh
ruby host-test.rb --work /absolute/new-work
```

The test executes the actual supervisor and rc.d account function. It replaces
passwd data, target command paths, and process inventory with explicit host
Perl doubles. It checks clean environment, singleton start, stale and foreign PID
metadata, generation isolation, normal exit, error exit, detached cleanup,
forced cleanup failure, ownership refusal and unsafe paths. A causal mutation
removes the marker predicate and must release a launch that the real predicate
refuses. The old bounded session-test guard remains unchanged.

These checks do not execute KDE or DRM. They do not prove native `ps`
environment visibility, service boot ordering, or target desktop readiness.
The source and host contract require separate target service acceptance.
