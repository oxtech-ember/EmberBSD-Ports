# GCC16 Fortran and Libtool consumer

Copy the `consumer` recipe to a new `devel/emberbsd-fortran-consumer` path in
a prepared pkgsrc export. Retain the original source copy. Use a normal
package-only invocation with the common cross configuration. Do not install
build tools on the target. Do not execute a target ELF on the build host.

The fixture uses the real `FC` and `F77` Libtool tags and the actual pkgsrc
Fortran wrapper. It builds a target shared library from an ISO C binding
routine and a fixed-form routine. A C main calls both. Formatted I/O and IEEE
module use require the real Fortran runtime and SDK modules. No fake compiler
or synthetic target library can satisfy this acceptance gate.

Select the clean Ports source through `EMBERBSD_FORTRAN_PORTS_SOURCE`.
Set `EMBERBSD_FORTRAN_CAPABILITY` to the completed compiler capability receipt.
Set `EMBERBSD_FORTRAN_PYTHON` and `EMBERBSD_SDK_SOURCE` to explicit host sources.
The common policy verifies the selected actual driver and f951. The SDK must
already contain the normally installed Fortran runtime and development roles.
A missing provider must fail before dependency auto-installation.

Build `cross/cross-libtool-fortran` with the same fake-cross target metadata
as `cross-libtool-base`. Pass its `TARGET_*` inputs as bmake command arguments.
The first `bsd.prefs.mk` include derives target values before it loads `mk.conf`.
Keep `USE_CROSS_COMPILE=no` and verify `TOOLS_USE_CROSS_COMPILE=yes`.
Do not set the derived `TARGET_MACHINE_GNU_ARCH` or GNU platform by hand.
For an amd64 NetBSD target, use these arguments with the common configuration:

```sh
bmake USE_CROSS_COMPILE=no \
    TARGET_MACHINE_ARCH=x86_64 TARGET_OPSYS=NetBSD \
    TARGET_OS_VERSION=11.0 TARGET_OPSYS_VERSION=110000 \
    TARGET_LOWER_OPSYS=netbsd TARGET_LOWER_OPSYS_VERSUFFIX= \
    TARGET_LOWER_OS_VARIANT= TARGET_OS_VARIANT= \
    TARGET_LOWER_VARIANT_VERSION= TARGET_LOWER_VENDOR= TARGET_OBJECT_FMT=ELF \
    package
```

Inspect the actual generated FC and F77 tag blocks.
The host package owns only the two distinct Fortran dispatcher scripts.
It does not own target runtime libraries or the C/C++ Libtool payload.
Do not suppress a failed native Fortran dependency by installing an old GCC.
For native Darwin `devel/libtool-fortran`, first select the real native GCC16
prefix with `GCCBASE`, `GCC_VERSION_SUFFIX=-16`, `USE_NATIVE_GCC=yes` and
`USE_PKGSRC_GCC=no`. Verify `FCPATH`, version, host format and runtime closure.
Keep this native configuration private to that provider. It must contain no
target sysroot. This documented selection still needs normal native acceptance.

Before runtime execution, inspect every ELF with the selected GCC16 readelf.
Require the selected target machine, target loader, SONAME, DT_NEEDED and RPATH.
Qualify the normal archive and its full target DSO closure. Execute only the
accepted consumer and closure on the selected target. Expect exactly:

```text
Fortran FC/F77 runtime: PASS
```

Repeat the compile/link probe with either tag removed from a private copy of
the actual dispatcher and require failure. Remove its SDK development provider
in a private fixture and require the normal preflight to refuse it. Preserve
the installed SDK and provider packages. Build the current FFTW package with
its default Fortran option unchanged, then run numerical F77 and ISO C binding
FFTW consumers. These real tests remain separate from the synthetic controls.
Run Cppcheck and path analysis with actual target flags for the C consumer and
selected runtime units. Use a supported memory checker for runtime consumers.
No completed link, runtime, FFTW, Valgrind or full KiCad result is claimed here.

The hook regression runs the actual `fix-libtool` and `post-build` recipe text:

```sh
python3 -B profiles/development-toolchain/cross/tests/libtool-fortran-post-build.py \
    --sdk-source /absolute/EmberBSD-SDK --pkgsrc /absolute/prepared-pkgsrc \
    --recipe /absolute/EmberBSD-Ports/pkgsrc/cross/cross-libtool-fortran/Makefile \
    --bmake /absolute/native-prefix/bin/bmake --lock-root /absolute/common-objects \
    /absolute/new-hook-check
```

Use `--baseline-recipe /absolute/original-Makefile` to retain the original
duplicate-hook witness. The check requires both tag guards and the dispatcher.
It checks text fixtures. It does not configure Libtool or qualify target code.
