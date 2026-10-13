# Complete libei provider

This recipe updates pkgsrc `x11/libei` to stable libei 1.6.0.
The [upstream release record](https://gitlab.freedesktop.org/libinput/libei/-/releases/1.6.0)
is dated 2026-05-15. Archive hashes are recorded in `sources.tsv` and `distinfo`.
They are measured from the upstream archives, not a signed release manifest.
The base recipe comes from pkgsrc revision
`fff4deb639a1a640476203c80f752fb77b6cb14b`.
EmberBSD recipe changes are AI-assisted. Upstream authorship and licenses remain.

Build libei, libeis, and liboeffis together. The portal helper uses the
current pkgsrc basu 0.2.1 provider. It does not require a systemd daemon.
The shared input-headers package supplies the event constants used by the
upstream demo tools. The older pkgsrc patch that removed `ei-demo-client`
is not carried. Linux uinput support still depends on upstream libevdev
detection and is not a supported EmberBSD device backend.

The upstream Python/Jinja generator runs on the build host.
Compiled C and C++ tests remain enabled with `tests=auto`.
The upstream Python tests need pytest, structlog, and python-dbusmock when
liboeffis is enabled. Missing host test modules do not block a cross build.
They also do not count as a Python test pass. Retain the build and source
files for the target test preparation and execution step.

The upstream munit wrap refers to mutable `head`. This recipe instead
fetches commit `fbbdf1467eb0d04a6ee465def2e529e4c87f2118` through pkgsrc
checksums. It was the upstream head when checked on 2026-10-13.
The munit patch builds a private static test library. It preserves all test
sources and prevents an unrelated `libmunit.so` from entering the package.
Meson downloads are disabled because all source archives are already pinned.

Recipe and archive checks do not establish target execution. Cross build,
Cppcheck/path analysis, upstream runtime tests, installed Xwayland input,
and memory checks remain acceptance gates. No board result is claimed here.
