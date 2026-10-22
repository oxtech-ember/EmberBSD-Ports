# GStreamer base and bad plugin packages

The complete `gst-plugins1-base-1.28.8nb1` and
`gst-plugins1-bad-1.28.8nb1` packages cross-build on macOS for EmberBSD/AArch64.
The inherited package split and options remain intact. Optional GL and codec
plugin packages are separate; their presence is not implied by these results.

The original cross build tried to execute the target `g-ir-scanner` on the
host. The recipes now select native GLib and introspection generators and use
Ports' shared target-query executor for GType discovery. The Meson patches
pass the newly built target library paths to those queries. Native builds
receive an empty environment and keep their existing generator selection.
All nine base and eleven bad GIR/typelib pairs survive, alongside utilities,
plugins, development files and translations. No output was removed from PLIST.

Installed introspection also exposed a missing dependency: Gst imports
GLib/GObject, whose typelibs now belong to `glib2-introspection`.
`gstreamer1-1.28.8nb1` records that target runtime dependency explicitly.
Having the matching host generator package is insufficient.

These are AI-assisted EmberBSD adaptations of upstream GStreamer and pkgsrc.
Original attribution, licences, archives and patches are preserved. The source
pin and hashes are in [sources.tsv](sources.tsv); no upstream acceptance is claimed.

## Reproduce the checks

Build and install the complete packages using the common-media profile.
The existing cross configuration must supply the shared GI target executor.

```sh
BMAKE=/absolute/native-bmake MAKECONF=/absolute/cross-mk.conf \
  sh profiles/common-media/tests/gstreamer-plugins-cross.sh \
  PREPARED_PKGSRC NEW_BUILD_CHECK
```

This checks actual native tool selection, native-mode selection, all 20
GIR/typelib pairs and every unconditional file in the two package lists.
The file check uses pkgsrc's manual-page rules with the selected `PKGMANDIR`
and `_MANZ`. It retains every source-list entry. Check the metadata oracle with
both manual directories, gzip settings and missing-file controls:

```sh
BMAKE=/absolute/native-bmake /absolute/selected/python3.15 \
  profiles/common-media/tests/gstreamer-plugins-plist.py \
  PREPARED_PKGSRC NEW_WORK
```

These fixtures do not build GStreamer or execute media.

Compile `tests/gstreamer-plugins-gi.c` with the target compiler against the
sysroot's `gobject-introspection-1.0` and `gstreamer-1.0` pkg-config entries.
Use the normal `/usr/pkg/lib` target RPATH. Run it on the installed board via:

```sh
sh gstreamer-plugins-runtime.sh VIDEO_FIXTURES FFMPEG_RESULTS \
  ./gstreamer-plugins-gi NEW_RESULTS
```

Inputs come from the [FFmpeg file-codec check](ffmpeg-runtime.md).
No hardware audio/video device is opened. The runner uses a private plugin
registry, finite timeouts and no loader or typelib path overrides.

## Accepted bounded run

On 2026-10-12 CM5 Rev 1.0, BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B passed with
experimental `EMBERV3DRENDER #0`, source
`ab6f88f04ca73c6958adb39d0e1c717f629e7901`. Firmware revision is unknown;
kernel SHA256 and the same physical board are recorded in the
[FFmpeg receipt](ffmpeg-runtime.md). Boot time did not change.

- All 20 installed typelibs load. Six registered types resolve to real library
  GTypes: VideoInfo, Discoverer, InsertBin, Play, Player and Transcoder.
- Raw video conversion/scaling preserves every byte of four changing
  64×64 YUV420 frames. H.264/H.265 parsers emit byte-stream output which
  FFmpeg independently decodes to the same 24,576 bytes.
- A finite sine-source/audio-conversion/resampling pipeline reaches EOS.
  This checks pipeline execution, not acoustic output or audio fidelity.
- Missing input fails as expected. Installed package checks validate 578
  base/bad files plus 237 core/GLib introspection files.
- The base/bad and target GLib introspection archives match the shared sysroot
  file-by-file before transfer. A host-only archive with the same architecture
  name was rejected by that comparison and was never installed on the board.
- GCC16 warnings-as-errors and Cppcheck 2.22 pass for the new C introspection
  verifier. The portability patches modify Meson configuration; a full static
  audit of all plugin C sources and Valgrind were not performed.

| Artifact | SHA256 |
|---|---|
| GStreamer core 1.28.8nb1 | `f08f20c038fdac4ace7ac0f995feb130537a0d0c0bdf3f9bdca06dcad8233056` |
| Base plugins 1.28.8nb1 | `51a7eac0809ee1449ebd3139cb7f7749ea3911408fb6b6f5a8bc7b6b9e95d06a` |
| Bad plugins 1.28.8nb1 | `c6d7b9032b0f4e8f9053e75fd4d67d1e44f96415d6a1f0a43df049e69b9ad6e2` |
| Target results | `2c5353a83352f27fa221d0d24ece587bc047f5e1bfbff2e4e97acdc882f7b3a2` |

The [earlier core receipt](gstreamer.md) records 106 upstream test cases.
This additional run accepts selected plugin and introspection scenarios.
It does not establish GL playback, the remaining plugin family, a long soak,
Qt Multimedia playback or a complete accelerated Plasma desktop.
