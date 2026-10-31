# LVGL C software package

This package builds upstream LVGL 9.6.0 as a static C library with the
software renderer and RGB565 as its default format. Applications select
`LV_DISPLAY_RENDER_MODE_PARTIAL`, provide the draw buffers and flush callback,
and attach their own display and input drivers. The package does not access a
framebuffer, input device, or MMIO itself. It uses the C library allocator;
no target C++ SDK, operating-system adapter, bundled codec, or ThorVG renderer
is required. Its configuration header is installed with the headers and must
match the library. Enable optional features through a separately reviewed
package configuration, not by changing that header in an application.

The default built-in font is generated from Montserrat and Font Awesome font
files, so their OFL notices are installed together with the LVGL MIT notice.
The files in `files/` reproduce the official notices from Google Fonts commit
`76fca9fd0bb4ea46583f92e978660f3984ab9442` and Font Awesome Free 5.15.4;
the exact font source versions used by upstream to generate its bitmap are not
identified in the LVGL release. `COPYRIGHTS.md` retains upstream attribution.

`tests/smoke.c` uses an in-memory RGB565 display with a small partial draw
buffer and a label. It checks multiple flushes and painted pixels. It exercises
no device and does not establish target runtime, touch, or camera support.

For a native package or a pkgsrc staged prefix, run the memory-only smoke test
with the selected native tools:

```sh
"$HOST_PREFIX/bin/python3.15" tests/run-native.py \
    --host-prefix "$HOST_PREFIX" --lvgl-prefix "$LVGL_PREFIX" \
    --output "$WORK/lvgl-smoke"
```

The C test itself is instrumented with ASan/UBSan; this command does not
instrument an already-built LVGL archive. It checks partial RGB565 rendering
and synchronous flush callbacks in memory; it does not test a real display,
input device, or target runtime. For a target, compile the same C source and
link against the target package and its compatible EmberBSD C foundation.
