# GDB 18.1 for EmberBSD/AArch64

The selected debugger is upstream GDB **18.1**, released on 2026-09-25.
The base NetBSD GDB 15.1 reads standalone DWO files but rejects
`DW_FORM_strp_sup`. Current upstream GDB supports the standard supplementary
forms; EmberBSD ports its native AArch64 backend and validates real debugging
on the target.

The [pkgsrc package](package.md) replaces `devel/gdb` in the development
profile and supplies the offline development image. The standalone cross
helper remains available for backend diagnosis. Neither route rebuilds the
base OS's imported GDB sources; the image explicitly selects the Ports package.

## Sources and adaptations

[sources.tsv](sources.tsv) pins the original release archive's SHA256.
The downloaded archive also matched the upstream
[SHA512 manifest](https://sourceware.org/pub/gdb/releases/sha512.sum):
`e7079ad31e6176391a4d278c85a668cc92c13c8dc1f4937f3d4438f9dc7afdbb12083af7f86e17e854b3d23c3ceff80c63bdbbc8e18b0cf9962656f75ab8b5a0`.
See the [release directory](https://sourceware.org/pub/gdb/releases/) and
[current upstream download page](https://sourceware.org/gdb/download/).

The three `aarch64-netbsd-*` source files come from NetBSD's GDB import in
[EmberBSD `21cd2464c720159bec0a3ba352e4dee940a58b02`](https://github.com/oxtech-ember/EmberBSD/tree/21cd2464c720159bec0a3ba352e4dee940a58b02/external/gpl3/gdb/dist/gdb).
Their Free Software Foundation copyright and GPLv3 notices are retained.
EmberBSD's integration, repairs and test scripts are AI-assisted work.
These patches have not been submitted or accepted upstream.

| Patch | Purpose |
| --- | --- |
| `netbsd-aarch64.patch` | Register the native/target backends; use GDB 18 initialization and shared-library APIs; preserve kernel type visibility; correct FPCR/FPSR order and the NetBSD signal trampoline/context layout |
| `supplementary-bounds.patch` | Bound the filename and ULEB checksum length, enforce supplementary roles, reject inconsistent lengths and safely compare empty checksums |
| `netbsd-iconv.patch` | Use NetBSD's real Unicode/iconv implementation instead of upstream's ASCII-only fallback |

Both build routes use the canonical package patch set, including the
[DWARF expression/location-list patch](dwarf-variants.md),
[entry-state reconstruction](entry-value.md),
and a POSIX-shell adaptation for `gstack`. Package and standalone build
options are recorded below; both enable zstd compression.

The signal unwinder follows NetBSD's `x28` ucontext pointer and libc's
`setcontext` trampoline. `abi-layout.c` checks the imported constants against
target headers. Runtime acceptance checks the actual FP registers and a
backtrace across signal delivery; matching offsets alone is insufficient.

## Cross-build

Use the [current GCC16 cross prefix](../cross/README.md) with its repaired
GMP 6.3 host dependency. A previous bootstrap prefix linked to GMP 6.2.1 is
not interchangeable with the accepted compiler, even if both print 16.2.0.
Provide a complete AArch64 NetBSD 11 sysroot with GCC16 CRT/C++ runtime,
GMP 6.3, MPFR 4.2.2, Expat, Readline 8.3 and zstd development files.
Record their package revisions and the compiler's input receipt.

```sh
GMAKE=/absolute/host/bin/gmake PKG_CONFIG=/absolute/host/bin/pkg-config JOBS=2 \
    sh profiles/development-toolchain/gdb/cross-build.sh \
    /absolute/gdb-18.1.tar.xz /absolute/current-gcc16-prefix \
    /absolute/sysroot /absolute/new-gdb-work
```

GNU make, host pkg-config, a build-host C/C++ compiler, Bison and Texinfo are
build dependencies. Paths must be absolute and contain no whitespace or
shell metacharacters. The script verifies the archive before extraction,
applies the canonical recipe patches with zero fuzz and records input/output
hashes. Host pkg-config reads only sysroot metadata, including `libzstd.pc`.
It never executes a target ELF on the Mac or installs into a shared prefix.
The bundled Libtool infers runtime paths from absolute dependency locations.
`libtool-sysroot.sh` removes the sysroot prefix only from those inferred
paths; build-time library search paths remain intact. The final ELF must
contain exactly `/usr/pkg/gcc16/lib:/usr/pkg/lib`. The staged executable is
stripped; the unstripped build output remains available for diagnosis.

The C configure probes use GNU C17 because upstream's ptrace return-type
probe relies on pre-C23 non-prototype declarations. The compiler stays
GCC16, with its DWARF5 default. No hardcoded ptrace type answers are supplied.
Target GMP, MPFR, Expat, Readline, curses, zlib, liblzma and zstd are reused.
Python/Guile scripting, debuginfod, Intel PT, Babeltrace and gdbserver are not enabled
in this focused CLI build. This is an explicit feature boundary, not a
fallback to older dependencies.

## Acceptance on the target

First generate the external-object fixtures with the OS repository's
[CTF/DWARF contract](https://github.com/oxtech-ember/EmberBSD/blob/main/external/cddl/osnet/docs/dtrace-dwarf.md).
Use the complete output directory; `.dwo` and `types.sup` files must remain
alongside their corresponding objects. Compile the live workload separately:

```sh
sh profiles/development-toolchain/gdb/build-fixtures.sh \
    /absolute/current-gcc16-prefix/bin/aarch64--netbsd-gcc \
    /absolute/sysroot /absolute/new-runtime-fixtures
```

Transfer the staged GDB, both fixture directories and `test-target.sh` to
the VM. The stage's prefix is `/usr/pkg`; runtime libraries must be the same
accepted versions as the sysroot. Run without loader overrides:

```sh
sh test-target.sh /absolute/staged/gdb /absolute/external-fixtures \
    /absolute/runtime-fixtures /absolute/new-results
```

This checks four GCC/Clang split objects and four standard supplementary
objects across DWARF32/64 and `ref_sup4`/`ref_sup8`, including inherited
types. Malformed metadata must produce diagnostics without a crash or
successful type lookup. Live DWARF32/64 programs exercise breakpoints,
locals, memory writes, FP register reads/writes, stack frames, signals and
normal exit. Logs are retained in the new results directory.

Use the resulting `/usr/pkg/bin/gdb` as the one active debugger after
acceptance. Keep any replaced base executable only in a private rollback
directory, outside executable search paths. The build script stages files
only; installation and the active selection remain explicit deployment steps.
VM acceptance does not establish physical-board debugging, kernel core dump
support, every DWARF form or the full upstream GDB testsuite.

The current standalone helper shares the accepted package patches and requires
zstd. Its updated patch application and target pkg-config metadata were checked;
a complete new standalone rebuild has not been repeated. The package remains
the accepted installable route.

## Verified result

On 2026-10-08, the GCC16 cross build and native NetBSD 11/AArch64 UTM run
passed all eight external-DWARF cases and seven malformed-supplement cases.
Both live DWARF32/64 programs passed, including distinct saved FPCR/FPSR
values across signal delivery. The installed `/usr/bin/gdb` selects GDB 18.1
from `/usr/pkg/bin/gdb`; the previous base executable is outside PATH.
Unicode conversion uses libc iconv, and the ELF has only the two target
runtime directories above. The full upstream selftests/testsuite were not
run; upstream selftests are disabled in this release build.
