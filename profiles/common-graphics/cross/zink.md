# Zink in the common Mesa package

MesaLib 26.2.4nb6 adds Zink to the existing V3D, VirGL, softpipe and
llvmpipe drivers. Zink translates OpenGL and OpenGL ES calls to Vulkan.
It uses the common Vulkan loader. A working Vulkan ICD remains a separate
requirement. The optional `powervr` package option and its experimental
hardware gate remain unchanged.

## Package contract

Use the normal [common graphics export and cross configuration](profile.md).
Run the ordinary `graphics/MesaLib` package target. The package declares
`vulkan-loader>=1.4.357.0` as a runtime dependency because Zink opens
`libvulkan.so.1` dynamically. The package owns `lib/dri/zink_dri.so` and
`share/drirc.d/00-zink-defaults.conf` in both PowerVR and ordinary GL builds.
All existing renderers, X11, Wayland, EGL, GBM and shared LLVM remain selected.

The [PowerVR selection check](../tests/powervr-selection.rb) parses the real
pkgsrc recipe in both configurations. A causal recipe without the runtime
loader must fail the dependency oracle. The native recipe check is
[selection.sh](../tests/selection.sh).

The [installed-package preparation helper](prepare-mesa-package-tests.rb)
includes the upstream `zink_format_test` from the selected build. It checks
the installed Zink files and recorded loader dependency. This format test
checks conversions without a Vulkan device. It does not prove GPU rendering.
The helper still accepts the earlier nb4 and nb5 receipts with their original
four-driver configuration and 38 target invocations.

## Hardware boundary

A Vulkan API version alone does not prove a usable Zink profile. The selected
Mesa sources define requirements in
`src/gallium/drivers/zink/VP_ZINK_requirements.json`. Zink screen creation
requires the Vulkan `nullDescriptor` feature, timeline semaphores and device
creation. The DRM path also requires external-memory file descriptors.
Render-only sharing requires DRM image-format modifiers.

PowerVR's upstream feature table does not provide every desktop OpenGL
requirement. Preserve its feature bits. Test the actual EGL/GLES profile,
shader compilation and pixels before starting KWin. Record the renderer and
reject software fallback in the GPU test. KWin has a native GLES path;
`KWIN_COMPOSE=O2ES` selects that API without changing Vulkan capabilities.

Then test GBM/EGLImage sharing, synchronization and the compositor output.
Native HDMI/KMS, device ownership, physical input and the complete Plasma
session retain their own acceptance boundaries. Package construction does
not establish any of these results.

The optional upstream `zink_check_requirements` tool uses Vulkan-Profiles.
Its generator is an additional pinned source input. Do not enable automatic
Meson downloads or remove the profile's offline source checks to build it.
