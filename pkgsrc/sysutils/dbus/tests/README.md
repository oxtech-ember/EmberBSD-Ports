# Relocated DBus regression (Darwin)

Use selected native toolchain and isolated staged prefixes; do not run against the host system bus.

`relocated-session.py STAGED_PREFIX ORIGINAL_PREFIX SDK_SOURCE` copies only the staged provider to a temporary prefix, applies the SDK owner text relocation, starts a private session, activates a private test service, verifies the moved machine ID and probes default and explicitly overridden system addresses with temporary Unix listeners. It terminates its own children.

`old-new-exec.py OLD_PREFIX NEW_PREFIX INTERPOSER` uses a Darwin dyld interposer compiled from `exec-interpose.c` to prove the original launch targets the original prefix and the repaired launch targets its moved prefix, without executing either daemon.

`path-unit.c` links the actual private libdbus helper and checks default moved paths, explicit outside-prefix paths, noncanonical paths, and an unrecognized-library-name fallback. Build with the selected compiler, source and build headers and relocated test library; pass `PREFIX moved` or `PREFIX fallback`.

No host or user state is modified; run the tests outside network/IPC sandbox only when needed for private Unix sockets.
