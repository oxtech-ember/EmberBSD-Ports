# Wayland GCC16 checks

The AI-assisted `chromium-wayland-enum-terminal-gcc16.patch` changes ten
production translation units, one inline implementation header and its GN owner.
It adds thirteen terminal `NOTREACHED()` calls after exhaustive internal enum
switches. Valid mappings, text-input serials, cursor requests, popup constraints,
color fallbacks and supported keyboard-hook results stay unchanged.

Unknown server text-input modes and types still return `std::nullopt`.
Unsupported color-space mappings still return `std::nullopt`. Unknown image
protocol values still map to the existing gfx invalid value. The transform
Mojo union is closed. Its existing wire validator rejects unknown tags before
deserialization; this source proof does not execute a malformed-wire test.

The compositor-name table moves inside its existing non-BSD conditional.
BSD retains its existing `kOther` result. The Wayland platform includes the
complete `NativeDisplayDelegate` type for its existing null unique_ptr result.
The inline input-types header includes `base/notreached.h`; its GN owner exports
`//base` through `public_deps`. No backend or compiler diagnostic is disabled.

## Production command replay

Use the original target GCC16 commands and complete generated inputs for:

- `ui/base/wayland/wayland_client_input_types.cc`
- `ui/ozone/platform/wayland/common/wayland_util.cc`
- `ui/ozone/platform/wayland/host/wayland_cursor_shape.cc`
- `ui/ozone/platform/wayland/host/wayland_wp_image_description.cc`
- `ui/ozone/platform/wayland/host/wayland_wp_color_manager.cc`
- `ui/ozone/platform/wayland/host/xdg_popup.cc`
- `ui/ozone/platform/wayland/host/zwp_text_input_v3.cc`
- `ui/ozone/platform/wayland/host/zwp_text_input_v1.cc`
- `ui/ozone/platform/wayland/ozone_platform_wayland.cc`
- `ui/ozone/platform/wayland/mojom/wayland_overlay_config_mojom_traits.cc`

Preserve source-local quoted-include lookup when replaying copied source bodies.
All ten original commands fail on the scoped return, unused-table or incomplete
type diagnostics. All ten patched commands compile with unchanged GCC16 flags.
All twenty paired preprocessing and Clang Static Analyzer commands complete.
Analyzer diagnostic signatures match for every pair. All twenty Cppcheck inputs
stop at unchanged dependency parser errors; this is incomplete analysis.

## Header export contract

A real GN `--check` fixture uses the exact changed owner and both consumer
target blocks with the complete implementation header. Other preexisting graph
nodes are inert. The missing dependency fails ordinary include checks and an
explicit base-header export control. A private dependency passes the current
include-only consumers but fails that export control. The public dependency
passes both. These six controls verify the bounded header ownership contract.
They do not replace a complete Chromium generation.

Upstream input round-trip, unknown-wire, content-type and transform tests were
inspected. They were not executed. These compile and analysis checks do not
establish Wayland runtime, GPU, keyboard, Electron or browser acceptance.
