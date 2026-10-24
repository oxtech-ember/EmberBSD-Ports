# Dawn type and flag dispatch checks with GCC16

The two AI-assisted patches apply to Dawn3bcc1c8f97fcf1d72c54c64d0722c3ce90c42327.
Apply them with strip1 and fuzz0 from the Chromium root, after the NetBSD
adaptations. Apply chromium-dawn-complete-types-gcc16.patch first.

The complete-types patch moves the GetOrCreateViewFromCache template body below
the complete TextureViewBase definition. Its body remains unchanged.
WGPUHelpers.h includes Buffer.h before its fixed Result-returning templates.
Result alignment checks, pointer tagging, member layout and reference ownership
remain unchanged. Both headers already belong to the native sources target.

The dispatch patch retains all twenty VulkanImageLayout labels and case bodies.
A converter accepts TextureUsage before converting it to uint64_t. This matters:
combined flags use a proxy with both enum and bool conversions. A direct integer
cast can select bool and collapse distinct flags to1. A uint32_t conversion can
truncate the generated uint64_t bitmask. No public flag value is added.
Tint handles its two existing private buffer-binding values before the public
typed enum switch. The same map receives the same binding. The lambda returns
at the same boundary. The public switch retains its exhaustiveness diagnostics.

## Production regression

Export the four actual commands from the configured GCC16 NetBSD Ninja graph:

```sh
ninja -C /absolute/CHROMIUM_OUT -t commands \
  obj/third_party/dawn/src/dawn/native/sources/Texture.o \
  obj/third_party/dawn/src/dawn/native/sources/WGPUHelpers.o \
  obj/third_party/dawn/src/dawn/native/sources/TextureVk.o \
  obj/third_party/dawn/src/dawn/native/sources/ShaderModuleVk.o
```

Replay them with separate object and dependency outputs. Keep the original
flags, definitions, include roots and diagnostics. For copied source files, keep
the original source directory as an iquote root. Compare each input on both
sides. Keep the complete-types patch on both sides of the dispatch comparison.
Do not execute target objects on the build host.

The executed GCC16.2 AMD64 comparison gives these results:

- Texture.cpp and WGPUHelpers.cpp fail before the complete-types patch with
  incomplete-type SFINAE diagnostics. Both patched commands succeed.
- TextureVk.cpp reports twelve flag-switch diagnostics before the dispatch
  patch. ShaderModuleVk.cpp reports two private-enum switch diagnostics.
  Both patched commands succeed with the same complete-types control.
- All eight GCC preprocessing commands succeed.
- Seven paired compile controls give14 expected outcomes. They check both
  header orders, pointer-size Result layout and incomplete opaque pointer
  clients. Four underaligned success/error types still fail the original
  two-reserved-bits static assertion on both sides.
- Compile-time assertions use the real generated TextureUsage and bitmask
  operators. They check all twenty independent literal label values. Two more
  checks retain bit40, alone and with TextureBinding. This tests conversion
  width; it does not admit an unknown flag through WebGPU validation.
  A direct-cast bool-collapse mutant and a uint32_t truncation mutant fail.

## Analysis limits

Eight paired Clang Static Analyzer21 calls complete for NetBSD11 AMD64. They
add no warning signatures. Both sides retain the Abseil forwarding-reference
warning. Texture.cpp and TextureVk.cpp retain a CommandAllocator dead store.
ShaderModuleVk.cpp retains a moved-from reference_wrapper finding in Stream.h.
These inherited findings remain unconfirmed.

Cppcheck2.22 receives the actual GCC-preprocessed inputs. All eight calls stop
at unmatched-brace parser errors in libc++ addressof.h or integral_constant.h.
The errors match within each pair. This is incomplete analysis. No clean
Cppcheck result is claimed. Keep complete diagnostics and input hashes.

These checks cover four translation units and the listed type controls. They
do not establish full Dawn, Vulkan, Electron or Blanc runtime acceptance.
