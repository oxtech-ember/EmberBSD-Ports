# Mesa with the common LLVM 23.1.3 runtime

On 2026-10-12, complete MesaLib 26.2.4nb4 was cross-built on macOS ARM64
with GCC16.2 and the accepted common LLVM23.1.3. Normal package checks and
sysroot replacement passed. The matching package was installed normally on
CM5 Rev 1 / BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B. No private runtime
provider or hardware-driver override was used.

This revision updates the common LLVM dependency and handles a sysroot
accessed through a symlink. LLVM metadata paths are compared with the real
sysroot. Canonical include paths map into the consumer's declared buildlink
headers. The native metadata helper is sealed against the actual installed
LLVM package; its query outputs still come from upstream LLVM code.

## Accepted execution

- Installed package files, symlinks and all 106 recorded runtime library paths
  match the cross-package manifests. The live loaders use installed providers.
- Automatic surfaceless and explicit render-node discovery report
  `V3D 7.1.10.2`, EGL 1.5 and GLES 3.0. Four small shader/pixel lifecycles
  pass per discovery mode.
- All 38 upstream invocations pass, including V3D QPU, VirGL staging and seven
  LLVM JIT tests. `Cache.List` skips internally; nine NIR cases remain disabled.
- An explicit CPU comparison passes four cycles with
  `llvmpipe (LLVM 23.1.3, 128 bits)`. This override is confined to the comparison.
- Five further independent runs pass 20 total V3D lifecycles at 1280x800.
  Each checks shader rejection, clear/triangle/outside pixels and teardown.

One earlier 1280x800 run failed BO allocation with `GL_OUT_OF_MEMORY`.
The board then had about 3.3 GiB of free pages and no other GPU client.
Without rebooting, both nb4 and the retained nb3 package passed the same
16x16, 640x480 and 1280x800 consumer. nb4 was restored normally and passed
the complete suite and 20 large lifecycles above. Thus a persistent new-Mesa
regression was not reproduced; the intermittent allocation failure remains
unresolved. The native driver requires contiguous BO storage. Fragmentation
is a hypothesis, not an established cause. Do not report sustained reliability.

The kernel and boot remained unchanged. Kernel SHA256:
`6c5aa74d3c33fb6e84ea5c04d6f3df48928deb021cdc908ee972a42df03c7bf5`.
Existing [desktop GL, PRIME and Qt evidence](mesa-cm5.md) belongs to the earlier
package closure until each consumer is repeated. HDMI, KWin/Plasma, Vulkan,
and a sustained remote session are not established by this test.

## Reproduce and identities

Use the [full package workflow](mesa-package.md) with MesaLib 26.2.4nb4
and the [sealed LLVM helper](llvm-config.md). Run the generated bundle with
expected renderer `V3D`. Run its `bin/mesa-render` separately with
`/dev/dri/renderD128 V3D 1280 800` for large-buffer acceptance.
Preserve the original result from every failed run.

| Artifact | SHA256 |
| --- | --- |
| MesaLib 26.2.4nb4 package | `ae296474059b85e28078f3af7e2b1d4ade22eba76d6e82961126b4af964f8bdc` |
| Complete test bundle | `99cd69a13207246624de7f1da30a5615e84999bc801368862263119ee296d199` |
| CM5 result archive | `bb80ce6209014c999b8dc7db63a3caf4f1e9e54ee0b2f93c9c3e677bd9108775` |
| Full invocation/large-render log | `b46b579af6735504323663e07b204d6a21bac6abe61204047b6f8a1fa8646ee9` |
| Same-boot package comparison log | `a6985de8a1c1b38be45cd02fb2e351fcfa19981725c8889f5eebd4daa3b4cf6a` |

No Mesa C/C++ source changed in nb4. The earlier source-analysis findings
remain recorded in the CM5 receipt. This run adds no Valgrind coverage.
