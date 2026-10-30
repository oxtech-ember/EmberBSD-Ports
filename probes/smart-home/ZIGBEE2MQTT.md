# Zigbee2MQTT 2.14.2 candidate

The recipe uses the original release archive, upstream frozen pnpm lock,
the selected common Node 26.13.0 and upstream-selected pnpm11.26.0.
Node 26.13.0 is outside upstream's declared engine range; the application
retains its own startup warning. pnpm's bootstrap archive
is separately pinned in [sources/pnpm.tsv](sources/pnpm.tsv).

```sh
NODE=/absolute/common-node/bin/node sh build-zigbee2mqtt.sh \
    /absolute/new-zigbee-work /absolute/archive-cache
NODE=/absolute/common-node/bin/node
"$NODE" test-onboarding.mjs /absolute/new-zigbee-work/source \
    /absolute/new-http-check
```

The archive cache must contain the Zigbee2MQTT and pnpm archives. The recipe
installs dependencies with `--frozen-lockfile --ignore-scripts`, preserving
the upstream package integrity checks. `--package-import-method=copy`
isolates the later patch from pnpm's content store. It then applies the local
serial patch before running the upstream allowed dependency build scripts.
On NetBSD native addons build from source with common GCC 16.2, one worker
and its C++ runtime path. A native Node/addon installation has not yet been
verified; the recipe stops on build or test failure.

The GitHub archive contains no `.git`. After the upstream build, the recipe
records `5c0c1c60` in `dist/.hash`, from the actual release commit
`5c0c1c60078e1737c5dee5f8217583bca7610e66`. This makes the application's
version reporting reproducible without inventing Git metadata.

## NetBSD serial adaptation

[`serialport-netbsd-list.patch`](patches/serialport-netbsd-list.patch) adapts
the exact npm package `@serialport/bindings-cpp`13.0.1. That package ships
compiled JavaScript, so the patch targets its shipped `dist` files. Its C++
implementation already has NetBSD termios/Unix I/O branches; their native
operation is not claimed by the JavaScript tests.

NetBSD selection reuses the existing Unix open/read/write implementation and
enumerates dial-out character nodes. It no longer executes Linux `udevadm`.
The list excludes normal files, symlinks and dial-in aliases; a node removed
during enumeration is skipped, while other filesystem errors propagate.
It never opens ports during discovery or fabricates USB metadata.

NetBSD can retain static device nodes without attached hardware. These are
path candidates only. Coordinator type, actual attachment, custom baud rates
and USB vendor/product discovery remain unverified. An explicitly configured
serial or TCP coordinator still requires a real runtime check.

## Evidence and limits

On 2026-10-07 a fresh recipe run on macOS27/arm64 with Node 24.21.0 passed
all 842 upstream tests in 25 files and all 5 local serial-list contracts.
The dispatch regression fails with the original platform selector and passes
with the patch; four unaffected list/error cases pass in both comparisons.
This tests JavaScript platform selection with fixtures, not NetBSD serial I/O.

The real application subsequently served its onboarding page, settings/schema
API and device enumeration API on an ephemeral loopback port. The test uses
an isolated data directory, removes inherited Zigbee2MQTT configuration
overrides, submits no radio configuration and stops its own process.
The test requires the application shutdown to exit 0. It does not modify the user's HOME
or use a mock application server.

`test-onboarding-exit.mjs NEW_WORK` separately tests the test harness with an
explicit fake server: clean exit is accepted, exit 1 and ignored SIGTERM
are rejected, and failed shutdown cannot publish `result.json` or PASS.
The previous harness fails this regression. This fixture is not application
runtime evidence. A second real Zigbee2MQTT HTTP run passed the corrected
shutdown requirement.

`EMBER_HOST_CHECK=1` explicitly permits host-only recipe validation. Its
environment log and HTTP result record the actual OS. Host success must not
be reported as EmberBSD support. Native Node, addon ABI/PTY transport, radio
pairing, MQTT device traffic, service startup and package installation are
still separate acceptance gates.
