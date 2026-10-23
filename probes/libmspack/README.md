# libmspack KWAJ header cleanup regression

[tests/header-errors.c](tests/header-errors.c) checks early KWAJ error cleanup
through the public `mspack_system` callback interface. It uses BSD-2-Clause;
see [LICENSE](LICENSE). The 15-byte `f00.kwj` fixture comes from libmspack
0.11alpha `test/test_files/kwajd`. Its original LGPL license is retained in
[COPYING.LIB](COPYING.LIB). The byte array records that origin.

The common [libmspack recipe](../../pkgsrc/archivers/libmspack) adapts upstream
[4d868504114346aa767d435fbb89a8b76603493f](https://github.com/kyz/libmspack/commit/4d868504114346aa767d435fbb89a8b76603493f).
The stable source archive has SHA256
`70dd1fb2f0aecc36791b71a1e1840e62173079eadaa081192d1c323a0eeea21b`.
The fix initializes the header filename and extra-data pointers before an
incomplete read or invalid signature can enter cleanup.

## Run the regression

The allocator fills each allocation with `0xa5`. The free callback counts
foreign pointers without passing them to `free`. Each case requires the exact
error code, header shape, zero callback errors, zero live allocations and a
closed input. The empty and blank headers must return errors 3 and 7.
The valid fixture must return error 0 and a data offset of 14.
Success prints three `result=PASS` rows followed by `cases=3/3` and exits 0.
A constructor, ABI self-test, callback or cleanup failure fails the program.

Use the ordinary GCC16 compiler, coherent sysroot and installed static library.
Create a new work directory. Run this example from `probes/libmspack`:

```sh
target=x86_64--netbsd # Use aarch64--netbsd for AArch64 inputs.
cc=/absolute/toolchain/bin/$target-gcc
sysroot=/absolute/sysroot
work=/absolute/new-work
mkdir -m 700 "$work"
TMPDIR="$work" "$cc" --sysroot="$sysroot" \
    -B"$sysroot/usr/pkg/gcc16/lib/gcc/$target/16.2.0/" \
    -B"$sysroot/usr/pkg/gcc16/lib/" \
    -std=c11 -O2 -g -Wall -Wextra -Werror \
    -I"$sysroot/usr/pkg/include" tests/header-errors.c \
    "$sysroot/usr/pkg/lib/libmspack.a" \
    -L"$sysroot/usr/pkg/gcc16/lib" \
    -Wl,-rpath,/usr/pkg/gcc16/lib \
    -Wl,-rpath-link,"$sysroot/usr/lib" \
    -Wl,-rpath-link,"$sysroot/lib" -o "$work/header-errors"
```

Execute the result through the [production target executor](../../profiles/common-graphics/cross/introspection.md#compiled-configure-probes).
Its `build_root` must contain the new work directory. The executor checks the
ELF closure, preserves status and removes its private target directory.
Native GCC16 can compile the same C source against the normal native static
library. Use the native platform headers and SDK selected by the normal build.

For a causal negative control, compile the unpatched release `kwajd.c` with the
normal build's generated `config.h` and exact compiler flags. Put that object
before `libmspack.a` in the link command. Keep the probe unchanged. The first
two cases must each report two invalid free requests. The valid case must
pass. Expected status is 1 with `cases=1/3`. A compiler, loader, timeout or ABI
failure is not this expected negative result.

## Recorded scope

The normal native GCC 16.2.0 package passes all three upstream test programs:
410 CAB, 195 CHM and 104 KWAJ assertions. The causal header probe passes with
the patched native static library. The exact unpatched release reproduces the
four invalid free requests. A separate UBSan trap build instruments all 22
library C translation units and the probe; it preserves these results.
The callback allocator reports zero live allocations after every case.

A GCC16 ASan/LSan attempt on Darwin arm64 is unaccepted. LeakSanitizer blocks
at process exit in `StopTheWorld`, dyld inspection and an allocator semaphore
on macOS 27. Its stack and interrupted run are retained separately. No check
is disabled to convert this attempt into a pass. Valgrind was not run.
UBSan and the callback allocator do not establish general uninitialized-read
coverage or whole-library memory safety.

The same GCC16 amd64 causal pair runs through the production executor with a
source-built EmberBSD library closure and an existing NetBSD 11 kernel/loader.
A further positive run uses the exact static archive payload from the qualified
`libmspack-0.11alphanb1` package. These runs use UID 0. They establish the bounded
header cleanup behavior, not kernel boot, unprivileged, general decompression
or KiCad GUI acceptance. No target package is installed by this check.

GCC 16.2.0 `-fanalyzer` and analysis-only Clang Static Analyzer 21 report no
findings for the configured amd64 baseline, patched KWAJ unit and probe.
Cppcheck 2.22 completes all three GCC-preprocessed units with exhaustive
checks. Baseline and patched units have the same 45 style diagnostics and one
checker report. The probe has 41 style diagnostics and one checker report.
There are no error, warning or parser diagnostics. Exit status remains 2
because style diagnostics are included. No category or diagnostic is suppressed.
The inherited findings concern upstream local scope, names and optional const,
and SDK header names or unused inline functions. The probe's four const callback
suggestions conflict with the exact public nonconst callback types; keep those
types without incompatible function-pointer casts. The analyzers do not detect
the baseline cleanup error. The independent runtime control detects it.
