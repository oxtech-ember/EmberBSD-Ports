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

The source-only options and consumer graph can be checked with:

```sh
"$HOST_PREFIX/bin/python3.15" pkgsrc/x11/qt6-qtbase/tests/vulkan-offscreen-options.py \
    --bmake "$HOST_PREFIX/bin/bmake" --work-parent /absolute/existing/work-directory
```
