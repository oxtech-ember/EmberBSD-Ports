# Xwayland 24.1.14 source-analysis boundary

Origin: EmberBSD (AI-assisted).

The baseline contains 678 C/header files identical to the pinned upstream
archive. The recipe had no C source patches before `nb1`.
The `nb1` delta contains only the input and BUG_WARN format fixes.
Unchanged upstream files need no invented before/after source difference.

The reviewed real compilation database contains these five units:

- `glamor/glamor.c`: glamor initialization and teardown.
- `hw/xwayland/xwayland-glamor.c`: Xwayland's EGL context integration.
- `hw/xwayland/xwayland-glamor-gbm.c`: GBM buffer integration.
- `hw/xwayland/xwayland-input.c`: input device handling.
- `hw/xwayland/xwayland-xtest.c`: libei and portal integration.

`glamor/glamor_egl.c` is not compiled into this Xwayland target.
The Xwayland EGL entry points are in `xwayland-glamor.c`.
The configured target enables glamor, GBM, DRI3, GLX, libei and its portal path.
This scope excludes the other X server units and dependency implementations.

## Method

Use the actual Meson `compile_commands.json`. Preserve source macros,
GNU C99 flags, generated headers and the EmberBSD AArch64 sysroot.
Map explicit target `/usr` include paths through the same sysroot as the
pkgsrc compiler wrapper. Remove only output/dependency options and terminal
color. Keep commands, compiler versions, hashes and unfiltered logs.

Cppcheck 2.22 consumes GCC 16.2.0's real preprocessed inputs with line markers.
Use `--language=c --std=c99 --platform=unix64 --library=posix`,
`--enable=warning,style,performance,portability` and `--error-exitcode=1`.
Clang 23.1.3 uses the same source configuration with
`--target=aarch64--netbsd11.0 --analyze -Xanalyzer -analyzer-output=text`.

For the patched comparison, map source include directories to a separate
patched tree. Keep generated build headers and target dependencies unchanged.
Run the complete input unit with GCC's additional `-Wformat-signedness`,
`-Werror=format` and `-Werror=format-signedness`. The original has four
format diagnostics from the three expressions. Both patches remove them.

## Findings and limits

All five Clang invocations complete before and after the patches.
Cppcheck also completes for all five configurations. It reports inherited
style and model findings, so the whole scope is not a clean Cppcheck pass.
No diagnostic category is disabled or silently suppressed.

The three confirmed type mismatches are fixed in `nb1` and have actual-source
format regressions. Clang's full input-unit analysis reports no finding.
Cppcheck's seat-format warning is absent after the patch. The extra GCC
format gate checks the tablet and BUG_WARN diagnostics too.

The remaining Clang report in `glamor.c` assumes initialization without
`GLAMOR_USE_EGL_SCREEN`. The actual Xwayland caller always supplies that flag
and installs the context callback. The standalone unit report does not
establish a failing Xwayland path.

Clang also reports a possible use-after-free through the intrusive list in
`xwayland-xtest.c`. The source removes an entry before freeing it and uses
the safe iterator. Cppcheck reports ownership escape at list insertion.
These model findings are not confirmed runtime defects. Keep them assigned
to the Xwayland Ports maintainer for separate lifetime-contract review.

Cppcheck does not model the libepoxy `glGetIntegerv` function-pointer outputs
and reports potentially uninitialized format/type variables in `glamor.c`.
It also reports inherited style findings in pixman headers and callback code.
Keep these results separate from the resolved formatting errors.

Source analysis and native expression tests do not establish GPU execution,
Wayland/libei integration, target Valgrind results or an accelerated Plasma login.
