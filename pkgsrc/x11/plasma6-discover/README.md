# Discover on EmberBSD

The Updates page and the Plasma notifier read the public service record at
`/var/db/ember-update/state.json` (`emberbsd.update-state.v1`). Refresh reads
the record again. The OS service owns network checks and unattended updates.

The page shows the available OS generation, package updates, custom-kernel
hold, restart request, slots, last check and errors reported by the service.
One action applies the available system update. An active local user
authorizes `/usr/sbin/ember-update apply` with polkit. A custom kernel holds
the OS generation. Available packages can still be applied. A missing or
invalid record disables the action. Reopening Discover reads the current
record, including a prepared update that needs a restart.

The store runs `ember-update catalog` as the desktop user. To install an
application, it authorizes `ember-update install PKGPATH --pkgname PKGNAME`.
The selected version must still exist in the signed catalog. Discover checks
the live package database after installation on a single-root system. On a
two-slot system it checks the selected package in the prepared update and
shows that installation takes effect after restart.

The package depends on polkit for `/usr/pkg/bin/pkexec`.

## Tests

Run the native state reader against a temporary directory with Qt 6 and
KF6 I18n from the selected host prefix. These tests exercise atomic changes,
resume, failure, a custom kernel and an unavailable service.

```sh
cmake -S files/update-tests -B "$build" -DCMAKE_PREFIX_PATH="$prefix;$prefix/qt6"
cmake --build "$build"
ctest --test-dir "$build" --output-on-failure
python3 files/check-system-action.py
```
