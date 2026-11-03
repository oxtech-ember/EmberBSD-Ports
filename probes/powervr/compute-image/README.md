# PowerVR CPU compute image

This producer prepares a bounded CPU-only compute submission for Mesa 26.2.6
and the exact BVNCs `36.56.104.183` (BXM) and `22.102.54.38` (GE8300).
It does not open a GPU or prove DMA, firmware submission, cache visibility,
or shader execution. The legacy `probes/a733-accelerators` paths remain
available as compatibility links.

Use the shared Mesa generator with the PowerVR profile, and follow
[the compiler instructions](../host-tools/README.md) to generate a receipt
and shader table. The optional last argument to `generate-usclib.rb` is the
BVNC; its default preserves the BXM common-shader path. The GE invocation uses
`22.102.54.38`, producing an actual BVNC-specific probe symbol and common
Mesa helper programs. Identical output bytes do not imply cross-profile support.

```sh
ruby build.rb "$MESA_SOURCE" "$MESA_BUILD" "$NEW_GENERATOR"
ruby extract-usclib.rb "$PROGRAMS_C" "$RECEIPT" "$NEW_SHADER_DIR" "$INPUTS_JSON"
ruby run.rb "$NEW_GENERATOR" "$INPUTS_JSON" "$NEW_IMAGE_DIR"
ruby check-images.rb "$GE_IMAGE_DIR" "$BXM_IMAGE_DIR"
```

The extractor verifies the receipt and chooses the probe symbol for its exact
profile. The runner rejects profile mismatches, stale artifact hashes, changed
shared-header layout and shaders that differ from the verified compiler output.
Its six binary images and JSON manifest preserve resource sizes, GPU virtual
addresses, permissions, and SHA256 digests. Scratch VA `0x8000000000` is a GPU
virtual address, not a physical address; only instance zero writes the
`0x13579bdf` canary. IDFWDF uses texture slots 0–3, sampler slots 4–7, and
address slots 8–9. The GE command has a 36-byte main stream followed by the Mesa
8-byte BRN49927 extension; the BXM command has a 44-byte main stream. Both
append four bytes of DRM flags.

Mesa warns that the GE profile lacks compressed-format border entries. The
bounded shader uses only an uncompressed F32 IDFWDF texture, so the adapter
records this limitation and preserves the zero-filled compressed entries.
Other unsupported Mesa warnings, barriers, BRN62269, unknown profiles and
unsupported shader metadata remain fatal. The GE producer uses heap-relative
PDS and USC offsets without the legacy BXM diagnostic aliases. Integration of
these CPU images with the target OS and any resulting hardware execution must
be validated separately.

The extraction preserves upstream function bodies, source pins and MIT
copyright in generated headers. `sources.tsv` pins the relevant Mesa inputs;
`LICENSE` contains the applicable notices. Build and compiler receipts record
the selected tools, commands, input hashes, and generated files.
