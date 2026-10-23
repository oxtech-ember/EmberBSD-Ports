# Persistent Plasma session package

This no-build package installs the canonical Plasma service. It is part of
the Plasma toolkit selection. It does not add a desktop to the base system or
the embedded dependency profiles.

The normal pkgsrc export includes the recipe. Use the current common cross
configuration. Build dependencies on the development host.

```sh
sh scripts/prepare-pkgsrc.sh /absolute/new-pkgsrc
cd /absolute/new-pkgsrc/sysutils/ember-plasma-session
bmake MAKECONF=/absolute/common-cross.mk.conf package
```

The recipe has no distfile or compiler step. Its `files/` directory holds the
canonical supervisor and rc.d script. The package installs these exact bytes.
It requires the shared Plasma, Perl and corrected Qt runtime providers. It
requires the standard `/usr/pkg` prefix used by those service sources.

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
account. [The service contract](../../../probes/plasma-mobile/toolkit/service/README.md) describes startup,
ownership, stop behavior and the separate hardware boundary.
