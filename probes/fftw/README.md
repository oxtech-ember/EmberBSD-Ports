# FFTW source probe

Compute real and complex Fourier transforms with FFTW 3.3.11 on EmberBSD.
This Ports-owned probe installs shared double (`fftw3`) and float (`fftw3f`)
libraries, headers, pkg-config/CMake metadata and separate pthread libraries.
Both precisions use one upstream release and one installation prefix.
The float library is the common dependency for liquid-dsp and future GNU Radio
integration. The build helper here remains a source profile. The ordinary
GCC16 pkgsrc package has separate [installed-package checks](../../profiles/common-build-tools/cross/README.md#installed-fftw-readline-and-ncurses).

## Build and test

Use a native C compiler, GNU make, tar and `sha256` or `shasum`.
The tests additionally need CMake 3.18 or newer and Ninja.
curl is only needed without an archive cache. There is no Python dependency.

```sh
JOBS=1 sh probes/fftw/build.sh /var/tmp/ember-fftw
sh probes/fftw/test.sh /var/tmp/ember-fftw
sh probes/fftw/tests/build-guards.sh
```

The work path must be absolute and absent. An optional second build argument
names an absolute cache containing the archive pinned by [sources.tsv](sources.tsv).
The SHA256 must match before extraction. `CC`, `MAKE` and `JOBS` select the
native compiler, GNU make executable and parallelism; `JOBS` defaults to one.
On macOS, use `MAKE=make` if GNU make is available under that name.
Existing work paths, relative paths, invalid job counts and corrupt archives
are rejected. Sources, installation and logs remain in the work directory.

The upstream release archive contains its generated codelets and configure
script. The recipe builds two precision variants sequentially with shared
libraries and pthread support. It disables static libraries, Fortran wrappers
and documentation. It does not request architecture-specific SIMD, MPI or
OpenMP. No upstream patch or system package replacement is needed.

Consumers select the installed prefix explicitly:

```sh
FFTW_PREFIX=/var/tmp/ember-fftw/install JOBS=1 \
  sh probes/liquid-dsp/build.sh /var/tmp/ember-liquid
```

Keep this FFTW installation while dependent consumers exist. Its manifest is
`install/share/ember-fftw/profile.txt`. Source and build trees are disposable
after preserving provenance and results; the installation is not disposable
while another profile uses it.

## Numerical contract

Two independent installed consumers compile [the same contract](tests/contract.c)
against the double and float public APIs. Each checks analytical complex
spectra at lengths 64, 45 and prime 127; positive and negative frequency peaks
have known amplitudes. Every other frequency bin must remain near zero.
Inverse transforms must recover the input after dividing by transform length.
Real transforms at lengths 64 and 75 verify DC, cosine and sine coefficients
and inverse recovery. Each precision also creates a 4096-point transform
with two pthread workers and repeats the spectral and round-trip contract.
Normalized error bounds are `2e-12` for double and `2e-5` for float.
NaN and infinity fail checks explicitly. Runtime version must be 3.3.11.

CTest runs the installed consumers with timeouts. Runtime linkage must resolve
both each precision library and its thread library from the selected prefix.
CMake clears discovery caches before every search to avoid stale prefixes.
Tests use explicit checks, including in Release builds; source build targets
are not linked into consumers.

## Validation and limits

On 2026-10-18, the ordinary `math/fftw` package `fftw-3.3.11` was
cross-built with GCC 16.2.0 and installed in an EmberBSD AArch64 E34 VM.
This package preserves its pkgsrc `openmp` and `simd` options and supplies
both precisions, pthread and OpenMP libraries. Four installed consumers use
the unchanged contract above, linking each precision to each thread backend.
All numerical cases pass; the OpenMP consumers load the installed
GCC16 `libgomp.so.1`. The upstream double and float `bench` verification
sets also pass complex lengths 16/45 and real lengths 64/75.

Normal package removal makes the double pthread and float OpenMP consumers
fail at the loader with the missing FFTW library. Reinstallation restores
all four consumers and passes `pkg_admin check`. All six installed FFTW
DSOs match the SDK byte-for-byte. This is package lifecycle and numerical
acceptance; it does not measure SIMD speed, sustained throughput or boards.
The package's Libtool `.la` metadata still retains absolute SDK search paths;
portable replacement archives remain pending.
It is independent of the earlier native GCC12 source-profile result below.

On 2026-10-07 the native source build, guards and both installed consumers
passed on EmberBSD AArch64 in a VM with NetBSD 11.0 userland, EMBER64 kernel
revision `b4f718d`, base GCC 12.5, CMake 4.3.3 and Ninja 1.13.2.
Across the complex cases, double normalized spectral error was at most
`5.87e-16` and inverse error `1.20e-15`; float errors were at most
`1.19e-7` and `8.77e-7`. Real and pthread cases passed. Both consumers
loaded their selected installed FFTW and pthread libraries.
Host guard checks also passed on Darwin arm64 with `MAKE=make`.

These are numerical and shared-library VM checks. Board timing, sustained
throughput, SIMD acceleration and real-time scheduling are unverified.
The full upstream FFTW suite and planner performance study were not run.
See [provenance and licensing](PROVENANCE.md); FFTW is GPL-2.0-or-later,
independently of the MIT license of the original probe helpers.
