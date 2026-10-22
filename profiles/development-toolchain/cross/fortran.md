# GCC16 application Fortran frontend

The explicit `--with-fortran` application mode configures the same pinned
GCC16.2.0 source and patches with `--enable-languages=c,c++,fortran`.
The default remains `c,c++`. Kernel mode, bootstrap-libgcc mode and other
entry points reject this option. Repeated options fail before output creation.

Use a new work directory and a new compiler prefix. Never install this
extension into a compiler prefix used by another producer. The mode installs
host compiler executables only. It does not build or install target runtimes.
Retain the preceding compiler generation until its consumers have stopped and
the new generation has passed the required compatibility checks.

```sh
HOST_CC=gcc-16 HOST_CXX=g++-16 CROSS_JOBS=10 \
    python3 -B profiles/development-toolchain/cross/build.py \
    --sdk-source /absolute/EmberBSD-SDK --target amd64 --with-fortran \
    /absolute/prepared-pkgsrc /absolute/gcc-16.2.0.tar.xz \
    /absolute/sysroot-amd64 /absolute/os-tools /absolute/host-math-prefix \
    /absolute/new-gcc16-fortran-generation
```

The selected Ports and explicit SDK sources must be complete clean Git roots.
The producer records their commits, the original archive hash and the complete
GCC recipe byte, mode and link inventory. It repeats these checks after the
compiler build and before publishing the capability receipt.

`fortran-check/capability.json` binds the new driver and its resolved `f951`
to their hashes and native host executable formats. Both must stay within the
new prefix. The driver must report GCC16.2.0, the selected target triplet and
POSIX threads. The producer compiles a real fixed-form Fortran routine and an
`ISO_C_BINDING` routine. Both objects must be ELF64 for the selected target. The selected GNU nm2.47
must find each expected nonempty routine, including its C binding name.
It repeats the compiler identity checks before writing the exclusive receipt.
Queries use SDK producer stream API1 with output limits and a timeout.
Compilations use the owned SDK producer path. An unproven process shutdown
quarantines the new work. Failed work stays available for inspection.

The receipt establishes host frontend and target compile capability only.
It does not establish target linking, `libgfortran`, Libtool, FFTW, target
execution or full toolchain acceptance. No target runtime is installed on the
host or target by this mode. An additional runtime-only provider must supply
the matching target libraries before dependent applications can link.
Host development modules and linker aliases need their own verified role.
A native Mac GFortran does not provide a NetBSD target frontend or runtime.

Run the parser, report, containment and bounded-query controls with explicit
SDK API1 sources. The two optional inputs add real read-only negative controls.
They do not compile a target object or mutate either compiler prefix.

```sh
python3 -B profiles/development-toolchain/cross/tests/fortran-policy.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --native-gfortran /absolute/native/gfortran-16 \
    --existing-cxx-prefix /absolute/existing-gcc16-cxx-prefix \
    /absolute/new-fortran-policy-check
```

Source guard checks do not qualify a newly built Fortran frontend.
Fresh compiler, target runtime and FFTW acceptance remain separate.
