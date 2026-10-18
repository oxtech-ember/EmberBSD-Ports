# Target memory-query selection

The upstream `/proc/meminfo` header probe reads an absolute build-host path.
During a Linux-to-EmberBSD build, that sets `HAVE__PROC_MEMINFO` incorrectly.
The existing BSD query implementations then lose precedence to Linux procfs.
`target-memory-query.patch` limits this probe to Linux and Cygwin targets.
It changes `configure.ac`, not the C query functions or their diagnostics.

Prepare separate baseline and patched source directories from the pinned archive.
The baseline has the first twelve patches. The patched tree has all thirteen.
Run current Autoconf and Autoheader in each source tree. Use separate native
and cross CLI build directories with the real dependency providers.
Keep the complete configuration:

```text
--with-ngshared=no --with-readline=yes --with-editline=no --without-x
--enable-cider --enable-xspice --enable-osdi --enable-klu --enable-openmp
--with-fftw3=yes --enable-shared --disable-static
```

Set the real `--build` and `--host` triplets. Use the common GCC16 runtime,
sysroot and native-generator flags described in the probe README.
Do not override upstream make flags on the command line.
`config.status` must generate the frontend Makefile, config header and Libtool.
Then run the helper for each configured source/build pair:

```sh
ruby probes/kicad/ngspice/tests/build-memory-query.rb \
    /absolute/source /absolute/cli-build /absolute/new-query-output
```

The helper builds three real frontend object targets with their generated rules.
It links `memory-query-contract.c` with those objects and configured flags.
It records compiler commands, configuration, source hashes and the executable hash.
It does not execute the result. Run each executable on its actual target OS.

The regression used Autoconf 2.73 and GCC 16.2.0. Full native and target shared
configuration preserved CIDER, XSPICE, OSDI, KLU, OpenMP and FFTW selections.
Full CLI configuration also retained GNU Readline. Linux kept its procfs define.
The target lost that define even with `ac_cv_header__proc_meminfo=yes` supplied.
A Linux `ac_cv_header__proc_meminfo=no` control still disabled the probe result.

In the E34 EmberBSD guest, the baseline consumer returned status 1. Both total
and available memory were zero, with two visible `/proc/meminfo` fopen errors.
The patched consumer returned status 0 with empty stderr. Its total was
1,054,785,536 bytes, equal to the contract's independent `HW_PHYSMEM64` query.
Both ELF files used target-only RPATHs; their loaded providers matched the SDK.
No package was changed during this causal check.

The inherited NetBSD available-memory implementation returns total memory.
It does not measure free memory. OpenMP configuration omits `getrusage`, so
both selected BSD RSS queries return zero. The contract preserves these limits.
It does not assert a new available-memory or process-RSS implementation.

Both native consumers returned positive memory values. Both strict Memcheck
runs had zero errors, zero live blocks and no suppressions. GCC `-fanalyzer`
and Clang Static Analyzer each completed 16 actual configurations without diagnostics:
three query units and the consumer, before/after, native/target.
Cppcheck used the same commands and measured compiler OS macros. Its initial
target report lacked `BSD`, `CTL_HW` and `HW_PHYSMEM64` from implicit system headers.
That produced two spurious missing-return paths. A bounded target rerun supplied
only those three values measured from actual GCC preprocessing.
The final native reports each retain 45 missing-system-header notices, two
const-pointer suggestions, five unused header functions and a checker report.
The final target baseline retains 47 such notices, two const-pointer suggestions,
five unused header functions and a checker report. The target repair retains
47 notices, five unused header functions and a checker report. Cppcheck returns
2 in all cases; these reports are not zero-diagnostic passes.
Raw initial failures and final diagnostics remain separate.

The ordinary recipes use revision 1 and require the exact matching shared package.
This module-level evidence does not replace rebuilt package or installed API checks.
The earlier revision-0 package hashes and acceptance remain separately documented.
