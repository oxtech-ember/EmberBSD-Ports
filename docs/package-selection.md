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

## Small SDK and binary delivery

The initial versionless sets are:

| Set | Roots/purpose |
| --- | --- |
| `sdk-bootstrap` | Native Python, pkg_install, OpenSSL and public HTTPS CA certificates; runtime dependencies come from Ports |
| `sdk-c`, `sdk-cxx` | Shared native Clang, LLVM and LLD; the target application sysroot is selected separately |
| `kernel-tools` | Native compiler tools and bmake, without an application sysroot |
| `fetch` | Small target HTTPS client with its shared OpenSSL dependency |
| `host-fetch` | The same fetch recipe for the developer host |
| `sdk-source-tools` | Fetch, digest, awk, sed, patch and Ports build helpers; no compiler or sysroot |

The bootstrap set is the native dependency portion of the SDK client, not a
complete relocatable bootstrap archive. C and C++ share Clang; neither set adds
a desktop, every language, tests or all targets. Target libc/CRT and C++ runtime
remain the responsibility of the selected OS/SDK sysroot producer.
Existing runtime/development package partitions (for example LLVM) retain their
shared compilation and separate payload ownership.

The SDK [binary catalog](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/binary-catalog.md)
uses these same files when publishing. Its readers can list and plan package
sets without this source checkout, a compiler or bmake. Signing and catalog
checks do not establish installed SDK or on-device pkgin acceptance.

## Binary-first SDK installation

The SDK client first checks its signed binary catalog. When a requested root
is unavailable there, `selected-order` writes `STATE/packages`: one
`PKGPATH[@native] PKGNAME` row per resolved node. These identities come from the
same metadata queries as the dependency graph; no second package scan is needed.
The client may fetch matching binaries for that closure before invoking the
ordinary selected build.

For that build only, `CROSS_BULK_BINARY_INSTALLED` names a client-owned list of
verified binary selections in the same two-column format. Target builds skip a
listed node only when its evaluated PKGNAME still matches and pkg_info confirms
that exact name is installed. Ordinary source builds and explicit package-stage
recovery keep their existing rebuild rules. Native packages retain their
existing installed-version reuse. Derive this input from the installed package metadata. Honor an explicitly
requested source rebuild.

For binary package updates, use the SDK client's
[`installed`, `plan --installed` and `update` commands](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/sdk-client.md#installed-versions-and-updates).
They use actual pkgdb package identities and published runtime dependencies.
They do not expand these package sets, recreate removed selections or build
the source catalog. Package versions and revisions determine replacements;
there is no common catalog generation or client-side freshness counter.
Signed metadata binds the selected indexes and archives; package signatures,
installed-version checks and dependency constraints protect installation.
The same Ports recipes and existing controller remain the source-build owner.
