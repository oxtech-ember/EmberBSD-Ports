# Current desktop support libraries and session bus

The common graphics profile builds libsfdo 0.1.4nb1 and D-Bus 1.16.2nb5 for
AArch64 using the existing GCC16 cross toolchain on macOS. Ordinary pkgsrc
package/install checks remain enabled. hicolor-icon-theme 0.18 and
nerd-fonts-Hack 3.5.1 also package and install without recipe changes.
This stage supplies prerequisites for labwc; it does not establish a complete
Wayland desktop, SVG rendering, Xwayland or hardware GPU support.

## Recipe corrections

libsfdo's upstream tests and examples link through an in-tree shared library
that itself needs `libsfdo-desktop-file`. The cross linker cannot resolve it
from the target runtime search path. The NetBSD cross recipe adds
`-rpath-link` for this build directory. The actual original command fails;
the same command with this single flag succeeds. Installed runtime paths
contain no work directory. Native selection is unchanged.

D-Bus's Meson configuration had selected Apple's `/usr/bin/xsltproc`, whose
catalog could not resolve the required pkgsrc DocBook resources. Upstream
then disabled XML documentation, and the normal PLIST check rejected nine
missing manpages and thirteen missing HTML files. Cross builds now select
`${TOOLBASE}/bin/xsltproc` and require `xml_docs=enabled`. This preserves the
full PLIST, X11 and kqueue options. The real upstream `--nonet` probes fail
with the original tool and pass with the common host tool; a real D-Bus XML
page transforms successfully. Missing host tools fail instead of dropping docs.
Native D-Bus behavior is unchanged.

The CM5 KDE tests exposed a second issue: Meson copied the host `TMPDIR`
into the installed session policy and compiled socket defaults. A normal
`dbus-run-session` then failed before KDE could connect. Cross builds now
set both upstream socket-directory options to the target `/tmp`. A required
post-configure check validates the actual header and installed-policy input.
[`dbus-runtime-paths.rb`](../tests/dbus-runtime-paths.rb) rejects the original
generated files and four individual host-path mutations; the corrected
configuration passes. No target directory resembling a build-host path is created.

The normal host prerequisites xmlto 0.0.29nb3, libpaper 2.2.8 and getopt
1.1.6nb1 use the shared host prefix. Existing libxml2, libxslt, DocBook,
Python, Mesa, LLVM and compilers are reused. No parallel toolchain is added.
Exact upstream archive identities and licenses remain in
[`sources.tsv`](../sources.tsv) and the imported recipes.

Use the [common cross configuration](README.md), with separate host tools
and target sysroot. Run ordinary `package` and sysroot install targets;
do not bypass PLIST, ELF, RPATH, permissions or work-reference checks.
The focused regressions are [`libsfdo-cross-link.rb`](../tests/libsfdo-cross-link.rb)
and [`dbus-cross-docs.rb`](../tests/dbus-cross-docs.rb); each script prints its
required paths when invoked without arguments. Keep their source/configuration
inputs unchanged during execution. Run the link regression before an installed
libsfdo can hide the original indirect dependency failure.

## Installed runtime acceptance

Extend the [text bundle](labwc-dependencies.md#installed-text-and-png-acceptance)
with the exact current libsfdo and D-Bus archives passed as additional package
arguments to `prepare-text-render.rb`. This reuses its full installed-payload,
recursive ELF dependency and canonical-provider checks. The target must have
normal base libraries and utilities, including `timeout`, `ldd` and `sha256`.
A valid base-system passwd database must resolve the invoking UID; a minimal
synthetic image must supply that too. No installed desktop session or persistent
system bus is required.

```sh
ruby prepare-desktop-support.rb /path/to/cross-tools /path/to/sysroot \
  /path/to/host/bin/pkg-config /path/to/extended-text-bundle \
  /path/to/libsfdo-0.1.4.tar.gz /path/to/new-desktop-work
# On the matching AArch64 target:
mkdir /absolute/private/desktop-bundle
tar -xzf desktop-support.tar.gz -C /absolute/private/desktop-bundle
sh /absolute/private/desktop-bundle/run-desktop-support.sh \
  /absolute/private/desktop-bundle /absolute/private/new-desktop-logs
```

The preparer verifies the upstream archive SHA256 and preserves its full BSD
license. It compiles all four unchanged libsfdo tests against installed headers
and DSOs: basedir, desktop-file, desktop and icon. The icon test runs against a
private writable copy of the original fixtures because it updates cache mtimes.
Target library providers and package payloads are checked before and after use.
Each real upstream test has a 15-second deadline, plus a five-second kill grace.

The earlier VM test runs D-Bus with a custom private policy and authenticated EXTERNAL session under `dbus-run-session`,
with no system-bus connection, network listener, activation services or permanent
configuration. The test checks the bus ID and names, acquires a well-known name,
verifies eight replies from its actual unique owner, checks exact unknown-method
and missing-service errors, and observes name release. The upstream echo tool
returns empty replies; this is not a payload-echo or byte-integrity claim.
The session has a 30-second deadline and five-second kill grace. Name release
and daemon disappearance are asynchronous and have bounded observation loops.
The runner never signals a PID that it does not own.

On 2026-10-08, all four tests and the session scenario passed in an isolated
EmberBSD/NetBSD 11 AArch64 VM. The runner and QEMU exited with status zero,
and the input FFS remained unchanged. The initial image lacked its passwd
database; that failed attempt is not runtime acceptance. No package changed
between that image correction and the successful run.

On 2026-10-12, the corrected `dbus-1.16.2nb5` package also passed CM5
acceptance using its **installed default session policy**, without a custom
`--config-file`. The unchanged KDBusAddons 6.31 upstream tests pass unique
application activation, exit-status propagation and dead-service name recovery.
The custom unique-instance test has `QT_FORCE_ASSERTS` enabled. The QtTest
recovery suite reports three passed cases, zero failures and no skips.
See the [Frameworks receipt](../../../probes/plasma-mobile/toolkit/cross/models-and-jobs.md).

Package SHA256: `a19ed59b68a34a30299fd24fba1c0866958c7c5baf5dcc31b697754df3c89f63`.
Path-regression journal: `4e311b005d74ab7eeb07af4490763b37fc48390beed63f825ef40435650ffcc2`.
The earlier VM test alone did not cover default-policy paths; the CM5 test
closes that specific gap.

This proves the installed freedesktop lookup libraries and a local session bus.
It does not test system-bus policy, X11 autolaunch, desktop service activation,
all upstream D-Bus tests, compositor clients or a full labwc session.
Current librsvg/Rust and Xwayland dependencies still require their own builds
and runtime acceptance; disabling those features is not a completed full port.
