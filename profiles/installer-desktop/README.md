# Installer desktop package profile

Origin: EmberBSD optional amd64 installer desktop profile, prepared with AI assistance.

The EmberBSD installer offers **None** or **XFCE with a Wi-Fi manager** inside
its existing System step. An experimental Plasma profile uses a separate
audited package set. Its amd64 desktop session remains unqualified.
This directory owns the pinned XFCE package closure and the GTK3 adaptation of the
original [dhcpcd-ui 0.8.0](https://github.com/NetworkConfiguration/dhcpcd-ui/releases/tag/v0.8.0).
The OS repository owns sysinst, the verified bundle preflight and installed
`ember-desktop-install` / `ember-desktop` helpers.

`packages.json` freezes 142 official pkgsrc packages from the NetBSD 11.0 amd64
repository and one locally cross-built leaf, `dhcpcd-gtk3-0.8.0nb2`. Each archive has
an exact byte size and SHA512 digest. This is a compatible **NetBSD 11 ABI**
package profile for EmberBSD 1.0; the upstream metadata remains unchanged.
The XFCE components are 4.20, GTK3 is 3.24.52nb3 and GLib is 2.88.3nb1.
No GTK2 theme bundle, extra Qt stack or second DHCP daemon is included.
These upstream binary packages are not claimed as EmberBSD source builds.
Their individual package metadata and licensing remain in every archive.

## Build the Wi-Fi leaf

Download the original dhcpcd-ui archive linked above. `build-wifi.sh` checks
its pinned SHA512 before extraction. Supply an amd64 release cross compiler
and a sysroot containing matching base/X11 development files and the verified
pkgsrc closure, including GTK3, libnotify and zlib pkg-config metadata:

```sh
sh build-wifi.sh /absolute/dhcpcd-ui-0.8.0.tar.xz /absolute/sysroot \
  /absolute/tools/bin/x86_64--netbsd-gcc /absolute/new-build
```

The local patch checks allocation failure and rejects incomplete or invalid
configuration blocks. These changes are not submitted upstream.
Run `ruby tests/wifi-library.rb extracted-source` for the actual-library
ASan/UBSan regressions before packaging.

The recipe selects GTK3, notifications and base dhcpcd/wpa_supplicant sockets.
It disables the upstream Qt, curses, duplicate icon and online utilities.
The current release bootstrap uses GCC 12.5.0; this does not qualify the
separate GCC16 toolchain migration.

Transfer the build output to an isolated EmberBSD amd64 environment, then use
its normal pkgsrc packager, without altering package compatibility checks:

```sh
sh package-wifi.sh /absolute/build /absolute/new-dhcpcd-gtk3-0.8.0nb2.tgz
```

The recipe preserves original source license headers in the installed package.
It declares gettext-lib directly because the GTK3 executable needs libintl.so.8,
which is distinct from the base libintl ABI. Check the frozen leaf's actual ELF
dependencies with `ruby tests/wifi-dependencies.rb package-directory target-readelf`.
The frozen lock records the exact acceptance candidate created with native
`pkg_create`. Recompilation or packaging can produce different archive bytes;
a new candidate needs a new reviewed lock and runtime acceptance. A locally
recreated file must never silently replace the frozen candidate under its hash.

## Assemble installation media

With the exact native leaf used by `packages.json`, run on macOS or EmberBSD
(bsdtar and curl required):

```sh
ruby bundle.rb /absolute/unused-bundle-output /absolute/frozen-wifi-package.tgz
```

The helper downloads original packages over HTTPS, checks every digest and
size, validates the root package list, and creates `desktop-xfce.tar.xz` without
macOS extended attributes. It never installs packages on the build host.
Put this archive alongside the image's own base/X11 sets and include its digest
in their normal SHA512 manifest before constructing installation media.
The System step selects all five X11 sets when XFCE is chosen. sysinst copies
and hashes the bundle before offering disk-write confirmation, then validates
its target copy and every package archive before normal `pkg_add` execution.
The bundle is available through the same USB or HTTP(S) set source as the OS.

## Assemble a Plasma bundle

Use the complete output of the [package-set auditor](../../probes/plasma-mobile/toolkit/tests/package-set.md)
with `--target amd64`. Keep `packages/`, `packages.sha256`, `roots.txt`,
`install-order.txt` and `target.txt` together. Supply native pkgtools, Ruby
with Fiddle, and bsdtar/libarchive on the development host:

```sh
PKG_INFO=/absolute/native/pkg_info PKG_ADMIN=/absolute/native/pkg_admin \
BSDTAR=/absolute/bsdtar \
  ruby bundle-plasma.rb /absolute/audited-amd64-set /absolute/new-output
```

This helper uses only the supplied package closure. It does not use the XFCE
lock or download replacement packages. It snapshots the source bytes and
runs the installer's native `--target amd64 --verify-only` check. It then
reconstructs a private metadata database and reruns the full package auditor.
Every archive's metadata, payload digests and ELF target must pass again.
The resulting dependency closure must contain exactly the supplied packages.
The source set stays unchanged. Package scripts and target programs are not run.

The closure must provide executable `/usr/pkg/bin/startplasma-wayland`,
`kwin_wayland`, `plasmashell`, `Xwayland` and `dbus-run-session`. Symlinks
must resolve to executable payloads inside the same closure.

The new output contains:

- `desktop-plasma.tar.xz`, with `All/*.tgz`, `ROOTS`, `SHA512` and `PROFILE=plasma`.
- `SHA512`, with the outer archive digest for the installation-set manifest.
- `PROVENANCE.json`, with source hashes, package sizes/digests, program owners,
  producer revision when available, tool-source hashes and measured bundle size.

Package archives retain their audited bytes. Outer tar entries use numeric
owner/group zero and `root:wheel` names. macOS attributes, ACLs and file flags
are excluded. Private staging is removed after completion or failure.
Publication uses an atomic no-replace rename on macOS or Linux. Existing
outputs, dangling symlinks and concurrently created destinations are preserved.
The XFCE `bundle.rb` interface remains unchanged.

The helper reports the actual archive byte count. The current OS installer
has a **512 MiB** preflight and staging limit. The provenance records whether
the bundle fits that limit. An oversized bundle can be retained for capacity
work, but the current installer rejects it. Generation does not waive this
gate or establish image, VM, session or physical-display acceptance.

Run the small native package/tar regression with real pkgtools:

```sh
PKG_CREATE=/absolute/native/pkg_create PKG_INFO=/absolute/native/pkg_info \
PKG_ADMIN=/absolute/native/pkg_admin BSDTAR=/absolute/bsdtar \
  ruby tests/bundle-plasma.rb /absolute/new-results
```

Twelve macOS cases pass. Header-only ELF fixtures cover valid bundles,
symlinked programs, wrong target/ELF, changed digests, invalid roots, absent or
non-executable programs and output preservation, including a publication race.
Tar checks cover package bytes, root names, inner/outer hashes and ownership.
These fixtures are not a compiled or running Plasma desktop.

## Installed behavior and verification boundary

`ember-desktop` starts XFCE after console login. No automatic login or password
is created. The Wi-Fi manager autostarts in XFCE; dbus, base dhcpcd and
wpa_supplicant are enabled. The administrative wheel group can use their control
sockets. DHCP discovers all available interfaces after saved Ethernet settings
are applied; explicit static interfaces retain their ifconfig configuration.
Without graphics, base `wpa_cli`, `wpa_supplicant` and dhcpcd remain available.
The OS enables sshd by default and preserves its existing authentication policy.

Verified: original source checksum, amd64 GTK3 cross build, native
`pkg_create`, package metadata and archive hashes, and installer contracts.
The paired OS candidate `56046a492ea498bfe2a38ae635a60bba7551c574` passes complete
amd64 UEFI Standard/XFCE installation from USB and a cold boot without that medium.
The installed XFCE session opens Thunar, its terminal and dhcpcd-gtk preferences.
Actual X, xfce4-session, xfce4-panel, thunar and dhcpcd-gtk processes are checked.
SSH handshake, dbus, base DHCP/WPA services and wheel control sockets also pass.
The package installer reports missing pkg_install version metadata for the locally
created leaf; package installation and runtime succeed without bypassing checks.
A separate network Minimal/None installation verifies console Wi-Fi and enabled SSH,
with no graphical executables installed. A QEMU test
without a supported Wi-Fi radio cannot establish real wireless association.
Plasma and physical desktop acceptance are separate work.

## Required GCC16 base runtime bundle

A base built with GCC16 and `MKCXX=yes` needs its matching runtime before
post-install C++ utilities run. This requirement is independent of the desktop
selection, including **None**. Prepare its separate bundle on the build host:

```sh
BSDTAR=/absolute/bsdtar ruby bundle-gcc16.rb \
  /absolute/runtime-create-output /absolute/new-runtime-bundle
```

The input must be the complete, unchanged output of
[`runtime.rb create`](../development-toolchain/runtime/README.md):
`gcc16-runtime-16.2.0nb1.tgz`, `package.sha256` and `provenance.json`.
The helper snapshots those inputs. It checks the receipt schema, fixed amd64
metadata, source pin, package bytes, payload digests, licenses, runtime conflicts
and packing-list directives. It uses `GCC16Runtime.audit_package` and its ELF
parser again. Only the selected `libgcc_s.so.1`, `libstdc++.so.7` and versioned
aliases are accepted. Headers, CRT objects, static archives, compiler programs
and installation commands are rejected. It does not execute target programs.
The source receipts record local provenance; they are not a source attestation
or a signature. The recipe's earlier source and stage checks remain required.

The output contains `runtime-gcc16.tar.xz`, outer `SHA512` and
`PROVENANCE.json`. The inner archive has exactly `All/`, `ROOTS`, `SHA512` and
`PROFILE=gcc16`. `All/` holds the single, unchanged runtime package. The inner
manifest uses its SHA512 digest. Provenance records source hashes, tool-source
hashes, package hashes and the measured bundle size. The outer archive must
fit the OS installer's **64 MiB** limit. An oversized archive fails before
publication. Tar ownership is `root:wheel` (numeric zero). macOS attributes,
ACLs and file flags are excluded. A private staging directory is removed on
success or failure. Publication uses an atomic no-replace rename. Existing
outputs and symlinks are preserved.

The Plasma closure must contain the identical runtime package, including when
its set is assembled later. Compare the actual artifacts before media assembly:

```sh
cmp /absolute/runtime-create-output/gcc16-runtime-16.2.0nb1.tgz \
  /absolute/audited-amd64-set/packages/gcc16-runtime-16.2.0nb1.tgz
```

A matching package name or version is insufficient. Include both bundle hashes
in the installation-set manifest. The OS owns required preflight, extraction,
target-copy rehash and normal `pkg_add` through the shared target package DB.

## Audit the installer bootstrap ELF closure

Run the following on the completed base DESTDIR before image assembly:

```sh
ruby audit-bootstrap.rb /absolute/amd64-destdir \
  /absolute/tools/bin/x86_64--netbsd-readelf > /absolute/bootstrap-closure.json
```

This read-only gate requires actual executable ELF files at `/bin/sh`,
`/bin/tar`, `/usr/bin/tar`, `/usr/bin/sha512`, `/usr/bin/cmp`, `/usr/bin/id`,
`/usr/sbin/pkg_add` and `/usr/sbin/pkg_info`. Both tar aliases are checked.
It follows target symlinks inside DESTDIR, inspects `PT_INTERP` and recursively
resolves `DT_NEEDED`. Every visited file must be ELF64 little-endian x86_64.
It rejects missing libraries, escaping links, non-base paths, foreign ELF and
shared `libstdc++`, including a renamed file with that SONAME.
`/usr/pkg/gcc16` cannot supply any bootstrap dependency.

Library lookup follows the selected OS rtld order: optional `/etc/ld.so.conf`
paths, each referring ELF's RPATH/RUNPATH, then `/lib` and `/usr/lib`.
Only base directories are allowed. The optional configuration must be a regular
file; library mappings and multiple RPATH/RUNPATH tags are rejected.
The installer must use a clean `LD_*`
environment. The JSON report records actual file hashes, dependency edges,
symlink targets, the configuration hash and the selected readelf hash.
Changes during inspection fail. Source C files do not satisfy this gate.
This checks the bootstrap closure; it does not qualify all base executables.

Run the native package and cross-linked ELF fixtures with explicit host tools:

```sh
PKG_CREATE=/absolute/native/pkg_create \
CROSS_BIN=/absolute/tools/bin/x86_64--netbsd- BSDTAR=/absolute/bsdtar \
  ruby tests/runtime-installer.rb
```

The fixtures use native `pkg_create`, cross `as`/`ld`, host readelf and tar.
They include an incompressible runtime payload above 64 MiB to exercise the
capacity gate. They never execute target code. Actual runtime packaging,
DESTDIR bootstrap acceptance, installation and image boot remain separate
checks until their real artifacts are available.
