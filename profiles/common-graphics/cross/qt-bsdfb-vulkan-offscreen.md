# Qt Vulkan offscreen rendering with bsdfb

The `vulkan-offscreen` QtBase option selects the NetBSD cross profile for a
bsdfb raster window and Vulkan offscreen rendering. It retains QtGui and
Vulkan, while disabling OpenGL, EGL, EGLFS, XCB, Wayland and VK_KHR_display.
Select it in the target pkgsrc configuration, separately from native tools:

```make
PKG_OPTIONS.qt6-qtbase+= vulkan-offscreen -gtk3
```

The bsdfb platform creates a basic Vulkan instance through Qt's existing
loader integration. It does not create a window surface or swapchain, and it
reports presentation as unsupported. Qt's basic instance may enable the
`VK_KHR_surface` instance extension if the loader advertises it, but does not
require it. A consumer may use `QQuickRenderControl` to render offscreen and
copy the resulting pixels into the raster window.

The ordinary upstream Vulkan loader and a compatible ICD must be supplied by
the target stack. This source selection does not establish a working driver,
Vulkan device, acceleration, or tablet display. Validate those separately on
the intended target. The normal QtBase configuration of other profiles is
unchanged.

## Rendering and presentation are separate

The shared bsdfb [native-image interface](../../../tests/qt-bsdfb/README.md#direct-image-presentation)
also accepts a completed image directly from a presentation worker.
Resolve `bsdfbPresentImage` and `bsdfbNativeImageFormat` through Qt's platform API.
The plugin owns the framebuffer mapping and serializes presentation and teardown.
The call copies native rows synchronously and retains no source reference.
It requires the exact framebuffer dimensions, native format, and `rotation=0`.
A consumer can rotate its offscreen image on the GPU and select input rotation
separately. This avoids the ordinary backing-store composition and CPU rotation.
It still performs GPU readback and one CPU framebuffer copy. It is not GPU scanout.

Use completion fences before reading a GPU result or recycling a frame slot.
Keep the image alive until the native presentation call returns.
Stop presentation workers before destroying QGuiApplication.
Use the same contracts for every compatible framebuffer; keep board selection
outside the renderer and presenter. DRM/KMS buffer import and page flips require
a separate display backend, with format, modifier, fence, and lifetime support.

The [PowerVR queue and BO checks](../../../pkgsrc/graphics/MesaLib/tests/README.md#powervr-queue-dependencies-across-submissions)
cover asynchronous dependencies and bounded allocation reuse.
They do not establish frame rate, physical presentation timing, or device stability.
The [UI measurement procedure](ui-performance.md) separates those checks.

The source-only options and consumer graph can be checked with:

```sh
"$HOST_PREFIX/bin/python3.15" pkgsrc/x11/qt6-qtbase/tests/vulkan-offscreen-options.py \
    --bmake "$HOST_PREFIX/bin/bmake" --work-parent /absolute/existing/work-directory
```

## Host-visible static uploads

`QT_VULKAN_HOST_STATIC_UPLOADS=1` enables direct static-buffer writes through VMA
for host-visible allocations in idle offscreen frames. VMA retains its flush
handling for non-coherent memory. The default remains the staging-copy path.

The optimization rejects buffers already used by the current frame, pending
offscreen frames, registered swapchains, and frames with external commands.
These cases retain staging copies and their command ordering. It does not
change dynamic buffers or remove texture uploads and framebuffer readback.

The original pure-offscreen implementation ran Qt Quick on A133/GE8300.
The conservative mixed-render guards have a compiled backend-predicate test;
this does not establish mixed-render hardware acceptance or a frame-rate target.
The patched Vulkan translation unit compiles for AArch64 with SDK Clang 23.
Clang Static Analyzer retains the same eight diagnostics as the unpatched unit.
Cppcheck 2.22 stops in Qt's `__has_builtin` preprocessing, so it provides no
translation-unit analysis result. Ordinary package lifecycle checks remain separate.
The test extracts the actual function and controls only its frame/VMA inputs:

```sh
CXX="$HOST_PREFIX/bin/clang++" sh pkgsrc/x11/qt6-qtbase/tests/host-static-uploads.sh \
    /absolute/patched/qtbase/src/gui/rhi/qrhivulkan.cpp /absolute/new-test-output
```
