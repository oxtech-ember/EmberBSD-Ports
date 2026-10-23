# Explicit Mach-O runtime paths

Origin: EmberBSD (AI-assisted). Preserve the NetBSD cwrappers source license.

The wrapper normalizer and both cleanup passes removed Meson's
`@loader_path/../dbus` runtime path before GCC16 reached the linker. Darwin
D-Bus build-tree tests could not locate their uninstalled shared library.
The D-Bus recipe keeps the upstream Meson test and install settings.
It declares only this build-tree path through the existing pkgsrc API:

```make
BUILDLINK_PASSTHRU_RPATHDIRS+= @loader_path/../dbus
```

cwrappers 20220403nb2 recognizes the complete `@loader_path` and
`@executable_path` root tokens only in runtime RPATH processing. Each path
must match an explicit `R:` source rule at a directory boundary. The first
matching rule still controls mapping or denial. The second cleanup pass
validates the mapped destination. A token is never prefixed with the SDK
sysroot or used to generate a sysroot-relative `-rpath-link` path.
Ordinary relative directories, `@rpath`, partial root names and unlisted
runtime tokens receive no new allowance. Link-time path handling, ordinary
NetBSD defaults and existing absolute `.libs` exceptions stay unchanged.
The existing LD plain-relative pass-through policy also stays unchanged.

The separate framework patch follows the Libtool unwrap-boundary repair.
It raises the tool predicate to nb2 for both native and cross builds.
The D-Bus recipe selects nb7 on both routes and adds the exact whitelist
only on Darwin. Target D-Bus retains its normal platform selection.

## Regression

Build the upstream and patched wrapper programs with GCC16 and their real
configured headers. Pass copies of generated `cc` and `ld` configurations.
The test changes only execution and log paths and runs the real wrappers
against `echo`, as the upstream wrapper tests do:

```sh
python3.15 -B -E -S profiles/common-build-tools/tests/cwrappers-macho-rpath.py \
    /absolute/upstream/bin /absolute/patched/bin \
    /absolute/config-copies /absolute/new-work
```

The 38 paired cases cover mapping, denial, component boundaries, path lists,
split and joined options, sysroot separation and unchanged LD defaults.
They establish argument filtering. Full D-Bus package tests and installed
loader behavior remain separate checks. Module analysis and instrumentation
must use the actual compiler flags and configured headers; parser refusals
must not be reported as clean analysis.

Native GCC16 ASan and UBSan support controls detect the injected faults.
Full instrumented upstream and patched wrappers both stop in the unchanged
`mi_vector_hash.c:178` tail read before RPATH processing. Full wrapper memory
acceptance remains open. No sanitizer exclusions are used.

The primary contracts are [NetBSD cwrappers](https://github.com/NetBSD/pkgsrc/tree/trunk/pkgtools/cwrappers/files/bin)
and [Apple dyld runtime paths](https://github.com/apple-oss-distributions/dyld/blob/main/doc/man/man1/dyld.1).
