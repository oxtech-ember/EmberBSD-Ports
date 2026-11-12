# Input formatting checks

Origin: EmberBSD (AI-assisted). Xwayland source copyright remains unchanged.

The `nb1` patches use `PRIu32` for the seat identifier and tablet button.
Both fields have type `uint32_t`. The shared BUG_WARN diagnostic uses `%d`
for `__LINE__`. The selected compilers confirm that predefined value has
signed `int` type. The patches preserve message text, control flow and protocols.

Run the source-expression regression with the common target GCC and sysroot:

```sh
HOST_CC=/absolute/native/clang \
TARGET_CC=/absolute/cross/bin/aarch64--netbsd-gcc \
TARGET_SYSROOT=/absolute/emberbsd-sysroot \
ruby tests/input-format.rb \
    /absolute/upstream/hw/xwayland/xwayland-input.c \
    /absolute/patched/hw/xwayland/xwayland-input.c \
    /absolute/upstream/hw/xwayland/xwayland-input.h \
    /absolute/upstream/include/misc.h \
    /absolute/patched/include/misc.h \
    /absolute/new-results
```

The regression extracts the three real formatting expressions. It verifies
source field types instead of replacing the formatting implementation.
Diagnostic output uses a bounded local `snprintf` buffer. No input device,
compositor, protocol message or network connection is created.

The cases include zero, one, `INT32_MAX`, the next unsigned value and
`UINT32_MAX`. The original seat and tablet expressions must produce incorrect
names for the upper range. The corrected expressions must match exact strings.
The positive source-line value keeps the same text in both versions.
The compiler must reject all three original expressions with
`-Wformat-signedness -Werror=format -Werror=format-signedness` and accept
all three corrected expressions. A compile-time type check covers `__LINE__`.
Target object files are not executed on the build host.

The native cases run with ASan/UBSan. Valgrind does not support the
macOS/arm64 build host used for this check. This is not a Valgrind pass.
The generated `compile_commands.json` supports a Cppcheck review of the
regression itself. Use the patched entries for a clean-result gate; the
upstream entries deliberately retain three format warnings.

The complete input translation unit also passes the target compiler's strict
format gate after both patches. Preserve the actual Meson compilation database,
generated headers, analyzer commands and raw logs with the validation receipt.
See [the bounded source-analysis scope](source-analysis.md) for its limitations.

## Anonymous file and installed-path checks

`shm-fallocate.rb` extracts the real `os_create_anonymous_file()` and its
helpers from the upstream and the patched `xwayland-shm.c`. The harness replaces
only the libc `posix_fallocate()` call, so each case sets its result:

```sh
HOST_CC=/absolute/native/clang \
TARGET_CC="/absolute/native/clang --target=x86_64--netbsd" \
TARGET_SYSROOT=/absolute/emberbsd-sysroot \
"$HOST_PREFIX/bin/ruby40" tests/shm-fallocate.rb \
    /absolute/upstream/hw/xwayland/xwayland-shm.c \
    /absolute/patched/hw/xwayland/xwayland-shm.c \
    /absolute/new-results
```

`EINVAL`, `EOPNOTSUPP` and `ENOSYS` must return -1 from the upstream function and
a descriptor of the requested size from the patched one. A successful
`posix_fallocate()` that leaves the file unsized (the NetBSD manual page
documents this) gives an unsized descriptor upstream and a sized one patched. `ENOSPC`, `EFBIG`, `EIO`
and `EBADF` must return -1 with the same `errno` from both. Success and one
`EINTR` followed by success must return a descriptor in both. The native
programs run with ASan/UBSan when the host compiler has them. `TARGET_CC` and
`TARGET_SYSROOT` are optional: with them the script also builds the harness
for the target with warnings as errors and links two programs per source.
`*-target-stubbed` takes the case name and expectation like the native run, for
example `./patched-target-stubbed ENOSPC ENOSPC`. `*-target-real` is built with
`-DREAL_POSIX_FALLOCATE` and calls the unmodified libc. Run them on the target.
On EmberBSD the upstream `real` program prints `posix_fallocate(memfd) = 22` and
`os_create_anonymous_file = -1, errno 22` and exits 1; the patched one maps and
writes 4096 bytes and exits 0.

`xwayland-binary.rb XWAYLAND [PREFIX]` reads a built or installed
`bin/Xwayland` without running it. It fails when the file contains a build
machine or sysroot path (`/Volumes/`, `/home/`, `sysroot`, `stages/` ...), when
`DRI_DRIVER_PATH` is not exactly `PREFIX/lib/dri`, or when the XKB paths are
missing. PREFIX defaults to `/usr/pkg`. The package `nb3` fails this check.


The native run requires `HOST_CC` as an absolute selected SDK compiler path and
uses `$HOST_PREFIX/bin/ruby40`. Sanitizer support is probed with a separate
compiler and runtime test; unsupported is reported explicitly, and each probe,
compile and case retains arguments, exit status, signal and diagnostics. A
failed instrumented harness build is an error when the probe succeeds.

On Darwin the native harness uses the upstream `mkstemp` path in its isolated
results directory; NetBSD target builds use the `memfd` path. SDK Ruby 4.0.9
and Clang 23 ran all 20 upstream/patched native cases with ASan and UBSan; this
does not establish a new target runtime result.
