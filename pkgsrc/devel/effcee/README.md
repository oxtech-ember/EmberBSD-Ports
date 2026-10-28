# Effcee source and installed dependencies

The recipe uses upstream version 1.2026.0 at
[`f8e8a164822d4f65e757bff66bc00e1567959aa0`](https://github.com/google/effcee/commit/f8e8a164822d4f65e757bff66bc00e1567959aa0).
SPIRV-Tools v2026.4 selects this revision in `DEPS`. Upstream has no current
GitHub release. Its published tags stop at v2019.1. The selected revision
declares version 1.2026.0 in `CMakeLists.txt`.

At source review, the newer upstream main revision
`66c954c82ab04686b3b3583adbdc7c06c891cc29` differed only in the macOS CI script.
The [comparison](https://github.com/google/effcee/compare/f8e8a164822d4f65e757bff66bc00e1567959aa0...66c954c82ab04686b3b3583adbdc7c06c891cc29)
contains no library or CMake changes. The recipe therefore retains the tested
SPIRV-Tools source pin. `distinfo` records the original archive hashes.

The patch adds an opt-in installed dependency mode. The recipe enables it and
uses the common RE2, Abseil and GoogleTest providers. Tests and sample programs
remain enabled. Missing providers and GoogleTest targets are fatal. The default
upstream vendor path remains available to other users.

The shared library uses upstream API major 1 as its SONAME. The patch installs
a relocatable `effceeConfig.cmake` and the `effcee::effcee` target. Its exported
interface resolves `re2::re2` through `find_dependency`. GoogleTest is a build
dependency. It is not part of the installed library interface.

On Darwin, Mach-O current version encodes the year-valued minor as years
since 2000: upstream 1.2026.0 becomes 1.26.0. Out-of-range components fail
configuration; the package version, install name and compatibility major remain
unchanged. The library directly links Abseil through the RE2 interface.

Run `python3 -B tests/macho-version.py --cmake /absolute/cmake` to check
the actual version fragment, including its bounds.

```sh
python3 -B tests/installed-config.py --cmake /absolute/cmake \
    --archive /absolute/effcee-1.2026.0-f8e8a164822d4f65e757bff66bc00e1567959aa0.tar.gz \
    --bmake /absolute/bmake --pkgsrc-source /absolute/prepared-pkgsrc \
    --patch /absolute/patch --work-parent /absolute/private-test-parent
```

This finite check verifies the commit-suffixed `DISTFILES` name with the real
prepared pkgsrc fetch rules and bmake. It does not override `github.mk` naming.
It verifies source hashes and zero-fuzz patch application. It
runs the actual dependency and export/config fragments with real CMake and
`LANGUAGES NONE`. An INTERFACE target stands in for the C++ library. Package
fixtures contain only target metadata. The check installs and relocates the
config, checks its exported dependency, and rejects missing providers.
It does not compile the library or qualify its ELF ABI.

Run the ordinary GCC16 build, upstream tests, staged packing-list check and
installed-library consumer before package acceptance. Full SPIRV-Tools unit
execution is a separate consumer check. Source checks do not establish these
results.

The native test phase sets `LD_LIBRARY_PATH` and `DYLD_LIBRARY_PATH`, as in
the common RE2 recipe, to find the uninstalled library in the CMake build's
`effcee` directory. pkgsrc does not define `SHLIB_PATH_VAR`. This environment
applies only to `make test`. Installed-library acceptance uses the normal
loader environment. Package RPATH rules are unchanged.

The [shared test-environment check](../../parallel/spirv-tools/tests/README.md)
uses actual pkgsrc platform discovery and checks this recipe too.
