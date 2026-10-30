# KArchive 6.31 on the common desktop stack

The complete KArchive 6.31.0nb1 package builds with Qt 6.12, GCC16 and the
common compression libraries. Ports supplies the recipe and cross checks.
It passes normal package checks and installation in the sysroot and on CM5.
This establishes archive-library coverage, not Dolphin or Plasma acceptance.

## Imported dependency paths

CMake validates pkg-config imported include paths before compiler wrappers
run. The original configuration rejected `/usr/pkg/include` on the build host.
The cross recipe sets `PKG_CONFIG_SYSROOT_DIR` for target Zstd metadata.
Native builds keep the original behavior. Only native Linguist generators are
needed from QtTools; the package retains its target Qtbase runtime dependency.

```sh
export BMAKE=/absolute/native/bmake
export MAKECONF=/absolute/cross-mk.conf
export CMAKE=/absolute/native/cmake
export PKG_CONFIG=/absolute/native/pkg-config
sh probes/plasma-mobile/toolkit/tests/archive-pkgconfig.sh \
    /absolute/pkgsrc /absolute/new-path-check
```

The regression reproduces the original failure with the real target `.pc`,
then configures the same CMake imported target with the recipe's sysroot.
`tests/linguist-tools.sh` additionally checks that Linguist comes from the
native `qt6-qttools` TOOL_DEPENDS and that the target dependency is retained.

## CM5 runtime, 2026-10-12

The original cross-built `karchivetest` and `kfiltertest` load the installed
`libKF6Archive.so`. Copy those executables from `_KDE_build/bin` and the original
`autotests/data` alongside them. Do not copy the build-directory library.
Run `tests/archive-runtime.sh UPSTREAM_TEST_DIRECTORY NEW_OUTPUT` on the board.
It checks loaded libraries, isolates settings and scratch files, bounds each
program and compares boot identities.

CM5 Rev 1.0, BCM2712D0, 4 GiB RAM, Waveshare CM5-NANO-B passed **132 archive
and 21 filter QtTest cases**, with no failures among the selected cases.
Coverage includes ZIP, tar, 7z, RCC, ar, malformed inputs and compression filters.
The selected archive run took 47.5 seconds; filter tests took 0.12 seconds.
Kernel SHA256: `6c5aa74d3c33fb6e84ea5c04d6f3df48928deb021cdc908ee972a42df03c7bf5`.

**One additional case is not accepted:** `test7ZipLargeUnpackSize` opens an
archive containing 2 GiB of zeros. An isolated retry reached 3,761,208 KiB
maximum RSS and exited with status 137 after 11.24 seconds. That is consistent
with memory exhaustion on this 4-GiB board; a kernel OOM trace was not captured.
The initial combined run also ended with 137. Neither is a successful full suite.
For this measured board, `KARCHIVE_SKIP_LARGE_UNPACK=yes` explicitly excludes
only that case and writes `exclusions.txt`; no exclusion is the default.
This resource limit remains relevant to large 7z archives in desktop consumers.

| Object | SHA256 |
| --- | --- |
| KArchive package | `1067716a006e5b2c4b843f55df8dee2eb44746ca034eada6cb3f2eb4ef20fd69` |
| Selected CM5 tests | `228cc8110398762d12ed79545d89d0d768e887a52df2d2b4682177a72595d70c` |
| Isolated 2-GiB case | `e083da19ba8948581552cbebae0e6180f575d5a96827c28ec14e8bfe50a5164d` |

KCompressionDevice's separate suite, Valgrind, installed-package removal and
desktop integration have not been accepted. The port does not change archive
parsing code or remove upstream tests. No whole-source static-analysis pass
is implied by these recipe and runtime checks.
