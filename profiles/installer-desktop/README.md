# Installer desktop package profile

Origin: EmberBSD optional amd64 installer desktop profile, prepared with AI assistance.

The EmberBSD installer offers **None** or **XFCE with a Wi-Fi manager** inside
its existing System step. Plasma remains a disabled development option.
This directory owns the pinned package closure and the GTK3 adaptation of the
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

## Installed behavior and verification boundary

`ember-desktop` starts XFCE after console login. No automatic login or password
is created. The Wi-Fi manager autostarts in XFCE; dbus, base dhcpcd and
wpa_supplicant are enabled. The administrative wheel group can use their control
sockets. DHCP discovers all available interfaces after saved Ethernet settings
are applied; explicit static interfaces retain their ifconfig configuration.
Without graphics, base `wpa_cli`, `wpa_supplicant` and dhcpcd remain available.
The OS enables sshd by default and preserves its existing authentication policy.

Verified so far: original source checksum, amd64 GTK3 cross build, native
`pkg_create`, package metadata and archive hashes, and installer contracts.
Full installation and graphical runtime acceptance are pending. A QEMU test
without a supported Wi-Fi radio cannot establish real wireless association.
Plasma and physical desktop acceptance are separate work.
