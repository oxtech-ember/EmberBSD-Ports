# Vulkan loader smoke test

Compile `loader-smoke.c` with the selected target compiler and the common
Vulkan headers. Run it on the target after installing `vulkan-loader`; it
loads `libvulkan.so.1` (`libvulkan.1.dylib` on Darwin), resolves the public loader entry point and reports the
loader API version. This does not require an ICD or a GPU and does not test
instance creation, driver discovery or rendering.

An optional library path selects an exact loader file for a staged package or
compatibility alias check. For example, run
`./loader-smoke /path/to/staged/lib/libvulkan.so.1.4.357` to verify that the
previously published ELF filename still loads the current Vulkan 1 loader.
