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

### CPU allocation at the end of a build

Cross-bulk divides the selected CPU budget among ready workers. If no new
package can start, active Ninja workers share the available slots. A sole
worker can also receive slots before it starts Ninja. A worker waiting for
an exclusive replacement returns its allocation. The scheduler restores the
allocation before the replacement starts. The pkgsrc CMake Ninja generator
and the Meson build, test and install targets use those slots with Ninja 1.13
or newer. A short file lock coordinates the grant with starting the worker's
Ninja FIFO. Package completion and replacement requests trigger the grant.
The package install and replacement locks still control access to shared files.

An explicit `CROSS_BULK_MAKE_JOBS` keeps the fixed allocation.
`MAKE_JOBS_SAFE=no` stays serial and `MAKE_JOBS.<PKGPATH>` or an explicit
Ninja `-j` retains its package limit. Older Ninja versions and early SDKs
use the numeric budget. Makefile generators keep their normal make jobs.
Concurrent Ninja calls in one adaptive worker share the same lock.

The SDK uses Ninja for a new LLVM package build. LLVM keeps the generator of
a configured work directory. An explicit `CMAKE_GENERATOR` selects the tool.

The [tail measurement](../scripts/tests/cross-bulk-ninja-tail.py) runs five
real Ninja builds with the selected native Clang, a recording pkgsrc fixture
and the cross-bulk scheduler. Pass `--sdk-source SDK --host-prefix PREFIX`
to the SDK Python. The report includes total elapsed time, overlap of compiler
processes across the whole run and after the four short builds finish,
the time until their serialized fixture installations finish, and the maximum
RSS of one compiler process. Increasing `--rounds` alternates the measurement order.
Add `--waiting-replace` to measure a native CMake reader while a short package
waits to replace its installed version. Both packages update an isolated pkgdb
using real `pkg_add` before their two dependents start. The benchmark measures
how long the short package waits within a total budget of four slots. Increase
`--units` if the reader finishes before the scheduler can grant extra jobs.

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
verified binary selections in the same two-column format. The scheduler reads
this file. Changing its path preserves the package metadata cache. Target builds skip a
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
