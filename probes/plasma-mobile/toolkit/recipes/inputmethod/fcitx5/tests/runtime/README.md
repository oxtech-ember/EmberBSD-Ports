# Fcitx5 core runtime tests

This runner packages all 51 CTest cases from Fcitx5 5.1.23.
It runs original upstream executables with the installed EmberBSD libraries.
Assertions and fixtures remain intact. It does not start an input session.
It does not change package registration.

Configure the cross build with explicit absolute target fixture roots.
Keep these options in the test build configuration, not the production recipe:

```text
-DFCITX5_TEST_SOURCE_DIR:PATH=/var/tmp/ember-fcitx5-tests/source
-DFCITX5_TEST_BINARY_DIR:PATH=/var/tmp/ember-fcitx5-tests/build
```

Use the existing complete build. The preparation command does not compile:

```sh
sh prepare.sh /absolute/fcitx5-5.1.23 /absolute/cmake-pkgsrc-build \
    /absolute/fcitx5-5.1.23.tar.zst /absolute/new-payload
COPYFILE_DISABLE=1 tar --no-xattrs -czf runtime-tests.tar.gz -C /absolute/new-payload .
```

On the target, install the matching Fcitx5 package and its dependencies first.
Extract the archive at the configured root, owned by the ordinary test user.
The runner requires that exact root. It does not create unrelated absolute paths.
Use a new work directory and run as an ordinary user:

```sh
mkdir /var/tmp/ember-fcitx5-tests
tar -xzf /absolute/runtime-tests.tar.gz -C /var/tmp/ember-fcitx5-tests
sh /var/tmp/ember-fcitx5-tests/run.sh /var/tmp/ember-fcitx5-tests /absolute/new-results
```

The runner uses `/usr/bin/timeout`, `/usr/bin/ldd`, and installed `/usr/pkg` Fcitx5.
Each case has a 60-second limit and a five-second forced-termination grace period.
D-Bus cases use upstream `dbus_wrapper.sh` and a private session daemon.
They do not use the desktop bus. `testconfigdbus` only tests serialization.
No registered case needs X11, Wayland, or a display server.
Upstream does not register `testxim`; it remains outside this acceptance.

The 13 `fixture` cases use the patched `testdir.h` roots. Their source assertions
are unchanged. The payload retains upstream source/build fixture layout.
Only uninstalled `dummyaddon` and `dummyaddondeps` modules are copied.
Production and installed testing modules resolve from `/usr/pkg`.
`testisocodes` and `testxkbrules` require installed iso-codes and xkeyboard-config data.
Sysroot paths in their configuration fail the run. Upstream `testxkbrules` only
prints a dump. The runner also requires US/Russian layouts, a PC105 model,
and the layout-switch option group in that dump.

Preparation verifies the source archive and unchanged upstream test files.
It reconstructs the two test-path plumbing changes with hash-checked recipe patches.
It rejects a different registered CTest set. Target executables, fixture data,
configuration, patch provenance, and licenses have a payload SHA256 manifest.
Target `ldd` logs record installed library selection. No production library is copied.
Each child receives private HOME, XDG, and temporary directories.
The runner retains its own HOME. `build/test` must remain writable for the
original fdstream test; the test removes its own temporary file.
PASS, SKIP, and FAIL counts are written to `results.tsv`.
A failed test makes the runner fail. Missing D-Bus is an explicit SKIP.

This is a unit-test check. It does not establish GTK-free Plasma integration,
Wayland text-input behavior, long-run stability, source analysis, or memory-safety acceptance.
