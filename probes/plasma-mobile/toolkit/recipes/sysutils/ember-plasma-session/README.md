# Persistent Plasma session package

This no-build package installs the canonical toolkit service. It belongs to
the optional `plasma-mobile` toolkit profile. It does not add a desktop to the
base system or the embedded dependency profiles.

Prepare the normal standalone source export and use the current common cross
configuration. Build dependencies on the development host.

```sh
sh scripts/prepare-pkgsrc.sh /absolute/new-pkgsrc plasma-mobile
cd /absolute/new-pkgsrc/sysutils/ember-plasma-session
bmake MAKECONF=/absolute/common-cross.mk.conf package
```

The recipe has no distfile or compiler step. The exporter materializes its
two relative source links from the canonical `toolkit/service` directory.
It retains the exact supervisor and rc.d bytes. The package requires the
shared Plasma, Perl and corrected Qt runtime providers. It requires the
standard `/usr/pkg` prefix used by those service sources.

Install the package and its dependency closure with normal package scripts:

```sh
PKG_RCD_SCRIPTS=yes pkg_add /absolute/ember-plasma-session-1.0.tgz
```

The explicit environment setting installs the standard rc.d files through
pkgsrc's generated hooks. It does not start Plasma or edit `rc.conf`.
If D-Bus or Xwayland was already installed without its rc.d file, reinstall
that exact installed package from its archive with `PKG_RCD_SCRIPTS=yes
pkg_add -U /absolute/package.tgz`. Do not copy service files manually.
The `dbus` and `x11_runtime` rc.d providers must be installed before startup.

Set these values in `/etc/rc.conf` and select an existing ordinary account:

```sh
dbus=YES
ember_plasma=YES
ember_plasma_user=desktopuser
```

The default is `ember_plasma=NO`. The package creates no account and changes
no device permissions. Automatic login is intentional for the selected
account. [The service contract](../../../service/README.md) describes startup,
ownership, stop behavior and the separate hardware boundary.
