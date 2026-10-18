# Check the GCC16 OpenMP runtime

`libgomp.c` checks the installed CPU OpenMP runtime with four workers.
It checks integer and binary-exact floating-point reductions over 10,000 items,
256 tasks with a shared lock, and distinct thread-local storage for each worker.
It joins the worker pool with `omp_pause_resource_all(omp_pause_hard)`.
It does not test GPU offloading or the complete upstream OpenMP specification.

The executable requires the exact absolute pathname reported by
`dl_iterate_phdr` for the expected `libgomp.so` provider.
It rejects a different pathname or multiple loaded providers.
A pathname does not prove the GCC version. Before and after execution, compare
the resolved library's SHA256 with the accepted package or native-tool receipt.
Retain the compiler version, source hash, ELF dependencies and executable hash.

## Cross-build and execute

Use the common GCC16 application compiler and its coherent EmberBSD sysroot.
The bootstrap must select `--with-libgomp`. Keep its installed `omp.h`,
`libgomp.spec`, development linker files and library on the build host.
Install the verified runtime-only package on the target.

From this directory, set `CC` to the complete cross-compiler pathname and
`SYSROOT` to the verified SDK. Keep GCC16's development metadata selected:

```sh
triplet=$("$CC" -dumpmachine)
runtime=$SYSROOT/usr/pkg/gcc16
"$CC" --sysroot="$SYSROOT" \
    -B"$runtime/lib/gcc/$triplet/16.2.0/" -B"$runtime/lib/" \
    -std=c11 -O2 -g -Wall -Wextra -Werror -fopenmp libgomp.c \
    -L"$runtime/lib" \
    -Wl,-rpath,/usr/pkg/gcc16/lib -o libgomp-test
```

The second `-B` selects the matching `libgomp.spec` before the base compiler's
copy. The common pkgsrc cross profile applies both prefixes through cwrappers.

Run the prebuilt executable in the target environment:

```sh
./libgomp-test /usr/pkg/gcc16/lib/libgomp.so.1
```

Do not use an alternate loader search path to select a second runtime.
Keep the package's normal runtime path and record the actual loaded provider.
The baseline needs four available OpenMP threads. A target policy that limits
the process to fewer threads causes a test failure.

Run two negative controls. An incorrect provider pathname must fail with
`Unexpected libgomp provider`. `OMP_THREAD_LIMIT=1` with the correct pathname
must fail with `OpenMP reduction/tasks/lock/TLS contract failed`.
Retain each process's exit status and diagnostic; neither failure is a pass
of the baseline contract.

Use the existing `libatomic.cpp` for the optional atomic library.
It checks 256-byte store/load/exchange and 2,000 concurrent compare/exchange
updates. Keep its provider hash and runtime installation evidence separately.

## Native checks and limits

On Linux, compile the same source with native GCC16 and `-ldl`.
Use that compiler's verified native `libgomp`, not the target library.
On 2026-10-18, GCC 16.2.0 passed the contract and both negative controls.
GCC `-fanalyzer` passed. Cppcheck 2.22.0 used the actual GCC16 macros and
`omp.h`; it passed with one documented callback-type suppression.
The system `dl_iterate_phdr` declaration requires that non-const parameter;
changing the callback type would violate its interface.

Clang 19.1.7 Static Analyzer could not parse the GCC16 header's
`__malloc__(omp_free)` attributes. This is an analysis limitation, not a
successful Clang check. The header and diagnostics were not disabled.

Valgrind Memcheck 3.24.0 ran the same native executable with all leak kinds
treated as errors and no suppression. The functional contract passed, but
the strict memory check failed on 328 still-reachable bytes in three
`libgomp` allocations after worker shutdown. It reported zero definitely,
indirectly or possibly lost bytes and no invalid access in that execution.
The upstream runtime retains initialization and initial-task allocations;
`omp_pause_resource_all` releases the pool, not all process-global state.
This result is not a clean strict Memcheck pass.

These native checks do not establish AArch64 execution, target package
lifecycle acceptance, or the absence of races in the runtime implementation.
Run the actual target package and consumer before claiming those results.

## AArch64 execution

On 2026-10-18, the application GCC16 cross compiler built this contract against
the verified EmberBSD E34 SDK. The runtime-only nb2 package passed installation,
removal and reinstallation in the AArch64 `EMBER64` QEMU guest.
The four-worker contract and both negative controls passed.
The separate 256-byte atomic contract also passed all 2,000 updates.
Removing the package made both executables fail at the loader, as expected.
Reinstalling it restored both results without loader overrides or a compiler
in the guest. The loaded runtime hashes matched the package.
See the [runtime package acceptance](../runtime/README.md#aarch64-installed-acceptance)
for source and package identities. This does not establish KiCad acceptance.
