# A733 compute image generator

Builds a CPU-generated compute submission for the PowerVR BXM GPU
(BVNC `36.56.104.183`) from Mesa 26.2.4 producer functions. The image is
accepted by the EmberBSD diagnostic ladder (stages 18-21) on Orange Pi
Zero 3W; see `ember/boot/a733-gpu-fwcompute.md` in the EmberBSD tree.

## Layout

- `generate.c` — bounded generator: packs the four USC precompiled
  shaders, PDS programs, context-switch state, and the CDM-2 stream.
  `USC_BASE` is `0x2000`: DOUTU execution offsets are 30-bit fields, so
  the USC code heap must live below 4 GiB. Keep the kernel-side mapping
  (`sun60i_a733_gpu_fwheap.c`) in sync with this base.
- `extract-usclib.rb` — extracts the precompiled shaders
  (`probe/store/load/idfwdf.precomp`) from the Mesa `pco_uscgen_programs`
  table after the host build.
- `build.rb` — compiles the generator against the Mesa host objects.
- `run.rb` — acceptance runner: verifies input hashes, runs the
  generator, checks the manifest, and refuses reuse of old outputs.

## Inputs

`probe.precomp`, `store.precomp`, `load.precomp`, `idfwdf.precomp` from
the Mesa host-tools build (`host-tools/README.md` describes that build).
Pin them by SHA256 in the inputs JSON; `run.rb` refuses any mismatch.

## Outputs

`general.bin`, `pds.bin`, `usc.bin`, `static-state.bin` plus
`manifest.json` with hashes, resource VAs, and sizes. The EmberBSD-side
packer (`ember/tools/a733-gpu-compute-firmware.c`) wraps them into the
version-2 firmware file `a733-compute.bin` with the nine-resource table
and the payload digest; install it under `/libdata/firmware/powervr/`
on the board.

## Validation scope

The generator produces compiler bytes on the CPU only. Hardware
execution is the kernel ladder's domain; no GPU, DMA, or firmware
interaction happens here.
