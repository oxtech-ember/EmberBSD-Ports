# Native development configuration

The common-tools profile uses the installed native Ports prefix, with Clang/LLVM
by default. Select GCC explicitly for a platform requirement. The SDK checks the
actual host OS/CPU and that tools and compiler components remain in the prefix.
This configuration does not acquire the first compiler or rebuild its prerequisite
closure. Use the existing [SDK bootstrap interface](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/darwin-bootstrap.md)
before a complete native prefix exists.

## Select the installed prefix

Generate the ordinary make include using the existing
[native-prefix adapter](cross/native-toolset.md):

```sh
/absolute/native-prefix/bin/python3.15 -B -E -S \
    profiles/common-build-tools/cross/prepare-native-tools.py \
    --sdk-source /absolute/EmberBSD-SDK write \
    --host-prefix /absolute/native-prefix --output /absolute/host-tools.mk
```

Use a prepared common-tools source export and a caller-owned MAKECONF:

```make
.if defined(BSD_PKG_MK)
PREFIX= /absolute/native-prefix
LOCALBASE= /absolute/native-prefix
EMBERBSD_SDK_SOURCE= /absolute/EmberBSD-SDK
EMBERBSD_HOST_PREFIX= /absolute/native-prefix
EMBERBSD_NATIVE_TOOLSET_MAKECONF= /absolute/host-tools.mk
.include "/absolute/pkgsrc/EMBERBSD-COMMON-TOOLS-MK.CONF"
.endif
```

`PREFIX` and `LOCALBASE` must match the selected prefix. On a native EmberBSD
development machine this can be `/usr/pkg`. The profile is not restricted to
that spelling or to NetBSD 11. Native package support still depends on each
recipe and the actual host; metadata checks do not establish a native build.
`USE_CROSS_COMPILE=yes`, a different compiler family, foreign compiler overrides
and a stale tool mapping are rejected. The include selects the prefix's PATH;
ordinary pkgsrc compiler wrappers remain in use.

Invoke the prefix's bmake and shell explicitly, with the MAKECONF above.
Keep its package database, object, cache and package-output settings in that
configuration. `MAKE_JOBS` defaults to one and accepts an explicit resource limit.
The profile also selects shared Python 3.15, Ruby 4.0 and current Meson/LLVM policy.
Regenerate `host-tools.mk` when the selected tools change. It is a configuration
include, not an admission report.

For the GCC alternative, add `--compiler-family gcc` when generating the include
and set `EMBERBSD_HOST_COMPILER_FAMILY=gcc` before the profile include. That route
retains `GCC_REQD=16.2`, the repaired full `gcc16>=16.2.0nb1` dependency and
`USE_PKGSRC_GCC_RUNTIME=no`: it does not add the separate `gcc16-libs` provider.
Neither branch silently switches to another family or a system compiler.
Keep native and target selection separate when preparing a cross SDK.

## Durable configuration and rollback

Before updating an existing `/etc/mk.conf` or user profile, preserve its contents,
permissions and unrelated settings. Install a durable source include and its
generated mapping together; do not leave a system default pointing into a
temporary export. Restore the previous configuration if its selected package
closure is not ready. Keep matching packages available for normal `pkg_add -u`
rollback. Do not overwrite base compiler files or change SSH/login settings just
to select pkgsrc compilers.

For interactive compilation, invoke the selected prefix's `clang`/`clang++`, or
its explicitly selected GCC drivers. Existing CMake/Meson build directories
retain their compiler and ABI choices. A family/runtime change requires new
compatible objects and consumers; changing PATH does not migrate their ABI.

## Verification boundary

The [metadata regression](tests/native-profile-selection.py) uses real bmake and
pkgsrc C/C++ recipes for NetBSD aarch64/amd64 and Darwin arm64. SDK-selection and
compiler-query doubles make the boundary explicit: no compiler, package build,
installation or target runtime is accepted by this test.

The historical [native GCC selection fixture](tests/native-compiler-selection/README.md)
passed on Zero 3W A733 with GCC 16.2.0 and the repaired nb1 package through
`/etc/mk.conf`. It checked real wrappers, C/C++20 packaging, execution, loaded
GCC libraries, removal and base-compiler preservation. Its unchanged installed
GCC checks remain available for that explicit family; they do not establish
Clang runtime compatibility. See the [native validation](../development-toolchain/native-validation.md)
for the retained compiler and module limits.
