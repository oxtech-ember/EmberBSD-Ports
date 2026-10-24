# LLVM family Python 3.15 migration

Clang 23.1.4 installs Python tools for scan-build, scan-view, header maps and
formatting. They require the target Python interpreter. The compiler ELF files
have no libpython dependency. Upstream lit remains a runtime package dependency
of LLVM, Clang and LLD in this profile. LLD has no installed Python scripts.
The recipes select Python 3.15. The lit recipe rejects another ABI provider,
because `bin/lit` and `bin/llvm-lit` have no ABI suffix.

Normal new builds use the common current Python and LLVM packages. Existing
23.1.4 packages can use the bounded
[package preparation tool](prepare-llvm-python315.py). Supply the accepted
NetBSD/aarch64 Clang, LLD and Python315-lit archives, the matching upstream
Clang source, host Python 3.15, host CMake, target readelf and host pkg_create.
Set `EMBERBSD_SDK_SOURCE` to the SDK source directory.
Run the tool with `--help` for its arguments. Use a new output directory.

This operation does not rebuild the compiler. It verifies the original packing
hashes and target identity. It compares all 13 Clang script bodies with upstream
before it changes only their interpreter line. It uses the existing CMake
`file(RPATH_CHANGE)` install mechanism to remove an unused Python 3.14 search
path. It requires exact byte equality outside that string and its zero padding.
It preserves every other file and symlink. A foreign libpython dependency,
unknown search path or unexpected source body stops the operation.

The new nb1 packages retain their original `+BUILD_INFO` and `+BUILD_VERSION`.
Additional fields identify the separate repackage operation and input archive
SHA256. The JSON receipt records all input/output hashes and allowed changes.
Historical Python paths in build provenance are not runtime dependencies.
The output is not a claim of a fresh compiler build or target execution.

The [metadata check](../tests/llvm-python315-metadata.py) parses actual pkgsrc
recipes and rejects the old ABI override. The [ownership fixture](../tests/llvm-lit-ownership.py)
checks co-install rejection, provider replacement and rollback with real pkgtools.
The [packlist regression](../tests/llvm-python315-packlist.py) verifies that
`pkg_create` emits each generated metadata entry once. The
[preparation fixture](../tests/llvm-python315-prepare.py) uses real pkgtools
to check script replacement and reject a changed upstream body. It has no
compiler or ELF payload.

Run [the payload check](../tests/llvm-python315-payload.py) on extracted output
packages with host Python 3.15. The original Clang package must fail the same
check. Run upstream `clang/tools/scan-build-py` unit tests with Python 3.15,
then run the existing [lit source check](../tests/llvm-lit.sh). The separate
[installed lit check](run-llvm-lit-tests.sh) verifies target launchers, wheel
metadata and real passing, expected-failure and failing shell tests.

## Replace one provider

`pkg_add -U` replaces a version of the same package base. It does not rename
`py314-llvm-lit` to `py315-llvm-lit`. Do not install both providers over the same
launcher paths. Preserve the original provider, reverse dependency lists and
all consumer packages before a transition.

Prepare and verify the complete replacement set first. Stop package mutations
and users of lit. Remove only the old lit provider in a bounded maintenance
transaction, then install Python315-lit and update its LLVM/Clang/LLD consumers.
A forced provider removal temporarily leaves dependency metadata unsatisfied;
it must have a tested rollback and must not remove the compilers. If both
providers were already registered, reinstall the retained provider immediately
after removing the old one to restore its launchers. Use ordinary pkgtools for
all package metadata changes. Never edit package ownership databases by hand.

After the transaction, verify package hashes, unique launcher ownership, every
reverse dependency, Clang helper startup and actual lit pass/fail behavior.
Keep the old provider package until rollback and target checks pass. A source
check alone does not complete the migration of an installed target.

The packaging changes and checks are AI-assisted EmberBSD work. Upstream
licenses and authorship remain unchanged.
