# DBus package roles

The `dbus-system` pkgsrc option is enabled by default. It retains the system
service configuration, account, privileged activation helper and rc/SMF
integration. EmberBSD target builds retain this default unless explicitly
configured otherwise.

The SDK cross-build host profile defaults to `-dbus-system`. This variant
retains the library, session daemon and traditional session service activation;
X11 autolaunch remains available through the `x11` option. It provides a
prefix-owned machine-id directory. It does not install the system daemon
configuration, privileged helper or system account integration;
`dbus-daemon --system` therefore cannot start using the package default.
Clients may still use an explicitly configured external system bus address.
Set `PKG_OPTIONS.dbus=dbus-system` in the native build configuration when full
system integration is intentionally required.

`tests/metadata-options.py` checks target and native options with actual bmake;
run it with `--help` for the explicit SDK, pkgsrc, recipe and host-profile paths. It is
a metadata check, not a substitute for installed runtime and hook tests.

`tests/session-only.py` exercises an already installed disposable native
Darwin prefix with the producer prefix still present. It checks session service
activation, loaded libdbus, repeated machine-id initialization, fail-closed
system daemon startup and an explicit external system address. It creates only
its own temporary service and socket; it does not require or create a host
`dbus` user or group.
