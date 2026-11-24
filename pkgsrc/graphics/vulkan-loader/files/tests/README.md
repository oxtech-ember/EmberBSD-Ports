# Vulkan loader smoke test

Compile `loader-smoke.c` with the selected target compiler and the common
Vulkan headers. Run it on the target after installing `vulkan-loader`; it
loads `libvulkan.so.1` (`libvulkan.1.dylib` on Darwin), resolves the public loader entry point and reports the
loader API version. This does not require an ICD or a GPU and does not test
instance creation, driver discovery or rendering.

An optional library path selects an exact loader file from a staged package.
For example, run `./loader-smoke /path/to/staged/lib/libvulkan.so.1` to verify
the staged Vulkan 1 loader without changing the installed library.

On Darwin, run `python3 darwin-manifest-relocation.py /path/to/libvulkan.1.dylib`
with the portable package library. The test moves the library to another prefix,
enumerates explicit layers and applies loader settings from its data and configuration
directories. It also checks `VK_LAYER_PATH` and XDG overrides. It does not require an installed Vulkan driver.
