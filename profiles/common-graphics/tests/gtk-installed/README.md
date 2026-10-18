# Installed GTK 3 upstream subset

This bundle runs five unchanged upstream GTK 3.24.52 test programs against
the installed package: Builder (39 tests), entry (2), text buffer (11), tree
path (6) and window (7). It preserves their assertions and the Meson runner's
`--tap -k` arguments. This is 65 tests, not the complete GTK suite.

The tests use inline data. Text buffer's image comes from the installed
GTK library's embedded resources. The bundle includes the actual build's
compiled GSettings schemas, matching original XML, source tests and LGPL
license. `gtk_test_init` itself selects the C locale and clears GTK modules.
The wrapper uses the upstream memory GSettings backend and X11. It does
not require a window manager or a settings daemon.

Prepare with Python 3.15 and explicit SDK API 1:

```sh
python3.15 -B prepare.py --sdk-source /absolute/EmberBSD-SDK \
    --source /absolute/gtk-3.24.52 --archive /absolute/gtk-3.24.52.tar.xz \
    --package /absolute/gtk3+-3.24.52nb4.tgz --sysroot /absolute/sysroot \
    --readelf /absolute/aarch64--netbsd-readelf --output /absolute/new/bundle
```

The helper verifies archive hashes, unchanged upstream sources, actual GCC16
compile commands, assertions, ELF architecture, loader, RPATH and the available
SDK dependency closure. It checks that the installed GTK/GDK libraries match
the libraries used by this build. It does not compile, install or execute them.
Its deterministic archive has a separate SHA256 receipt.

Extract the archive in the target and run as the display's ordinary user:

```sh
DISPLAY=:99 /bin/sh /absolute/gtk-upstream/run.sh /absolute/new/results
```

The wrapper verifies payload hashes and records target `ldd` output. It uses
the installed `/usr/pkg` libraries without loader overrides. Base `timeout`
bounds each test to 30 seconds, then sends SIGKILL after five more seconds.
Original TAP output, stderr, exit status and counts are retained. Any failure,
timeout, missing test, zero-test run or skipped case prevents acceptance.
Require exit zero and all 65 tests. Actual target results remain separate from
bundle preparation. This does not prove a desktop, hardware display or CAD app.
