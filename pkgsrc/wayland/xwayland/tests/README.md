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
