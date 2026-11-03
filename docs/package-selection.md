# Package selection

Package sets name versionless roots, one PKGPATH per line. Add `@native` only
for a host package root; a path without the suffix is a target root. They
select packages; pkgsrc and the
cross-bulk controller resolve dependencies and build order. The `plasma` set
selects the `sysutils/ember-plasma-session` root, whose declared dependencies
provide the Plasma desktop, workspace, window manager, and required host tools.

The SDK `scripts/packages.py` frontend can list and show sets without invoking
bmake. `plan` and `build` require an explicit `--set` or `--package`, the
configured `BMAKE`, `MAKECONF`, and `PKGSRCDIR`, a persistent build-state path,
and an explicit `--host-prefix`; the frontend selects both the host `bmake` and shell
from that prefix without a shell fallback. Keep generated MAKECONF files in a
dedicated stable config directory rather than a shared temporary directory,
because cache validity includes makefile parent-directory metadata. An empty
selection does nothing; there is no
implicit all-packages or Plasma build.

For example, from an SDK workspace with its cross environment configured:

```sh
/path/to/native/bin/python3 scripts/packages.py --ports-root /path/to/EmberBSD-Ports list
/path/to/native/bin/python3 scripts/packages.py --ports-root /path/to/EmberBSD-Ports show --set plasma
/path/to/native/bin/python3 scripts/packages.py --ports-root /path/to/EmberBSD-Ports plan \
  --state /path/to/build-state --host-prefix /path/to/native --set plasma
/path/to/native/bin/python3 scripts/packages.py --ports-root /path/to/EmberBSD-Ports build \
  --state /path/to/build-state --host-prefix /path/to/native --set plasma
```

`plan` and `build` pass their explicit roots to `scripts/cross-bulk.sh` as
`selected-order` and `selected-build`. Both return the target and closure
summary while holding the state lock; `build` keeps that lock through package
builds and installs into the selected build prefix/sysroot. This is not a
target-device package installer.
The generated root list is temporary and kept outside the state directory so
selection does not overwrite the persistent full-build root list.
