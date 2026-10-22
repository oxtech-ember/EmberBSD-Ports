# FFmpeg 9 software media on EmberBSD

The full FFmpeg 9.0.2 package cross-builds with GCC 16.2 and installs into the
common EmberBSD sysroot. Normal external codecs, filters, tools, headers and
libraries remain enabled. CM5 acceptance covers short file-based software
encoding and decoding; it does not establish hardware video codecs, sound
output, Qt Multimedia playback or an accelerated Plasma session.

The separate [cloud CPU cross selection](cross/README.md) now passes installation,
exact FFV1 pixels, timestamps, inverse filters, PCM samples and package cycles
in AArch64 QEMU. That record does not extend the CM5 external-codec scope.

The current libaom recipe selects the stable 3.15.2 bug-fix release.
Its AArch64 dispatch patch is unchanged. The board acceptance below uses
libaom 3.15.0nb1. See the [upstream release notes](https://aomedia.googlesource.com/aom/+log/v3.15.1..v3.15.2).

The 3.15.2 amd64 package also passes GCC 16 cross-build and complete package
payload checks. On NetBSD 11, its staged encoder and decoder round-trip one
16 by 16 I420 frame without loss and reject a malformed AV1 IVF payload.
This bounded, privileged CLI check uses the build sysroot libraries. It does
not extend the board, full codec-suite or memory-analysis acceptance below.

## AArch64 dispatch repairs

The inherited libaom 3.15.0 and libvpx 1.16.0 recipes disabled runtime CPU
detection on AArch64. Modern GCC compiled I8MM and SVE routines, which the
static tables then selected unconditionally. On CM5 the original FFmpeg AV1
encoder trapped on `usmmla`; VP9 trapped on `movprfx` in
`vp9_block_error_fp_sve`. Both failures were reproduced under the target GDB.

The complete recipes now retain runtime dispatch. Their added platform branch
reads the existing `machdep.cpuN.cpu_id` ABI and intersects extension support
across all attached CPUs. A missing or truncated response falls back to the
AArch64 NEON baseline. CRC32 (libaom), DotProd and I8MM are selected only from
known feature values. SVE/SVE2 remain unavailable until the OS establishes a
userspace vector-state preservation contract. Environment masks still allow
upstream's explicit scalar control.

Upstream code, licences, authorship and inherited pkgsrc patches are retained.
The additional code is AI-assisted EmberBSD work, not submitted upstream.
[sources.tsv](sources.tsv) pins the original archives and SHA256; recipe
distinfo retains BLAKE2s, SHA512, size and every patch checksum.
The authoritative dispatch implementations are
[libaom](https://aomedia.googlesource.com/aom/+/refs/heads/main/aom_ports/aarch64_cpudetect.c)
and [libvpx](https://chromium.googlesource.com/webm/libvpx/+/refs/heads/main/vpx_ports/aarch64_cpudetect.c).
Our changes add the EmberBSD/NetBSD ABI branch, not a different codec.

## Reproduce

Prepare the common-media or plasma-mobile profile as described in
[README](README.md), then cross-build `multimedia/libaom`, `multimedia/libvpx`
and `multimedia/ffmpeg9` through the selected shared sysroot. Install the
resulting packages with their complete dependencies on the acceptance board.

Compile the dispatch regressions on the host using the same target compiler:

```sh
"$CC" --sysroot="$SYSROOT" -std=c11 -D_NETBSD_SOURCE -Wall -Wextra -Werror \
  -I"$AOM_SOURCE" -I"$AOM_SOURCE/cmake-pkgsrc-build" \
  profiles/common-media/tests/libaom-cpudetect.c -o libaom-cpudetect
"$CC" --sysroot="$SYSROOT" -std=c11 -D_NETBSD_SOURCE -Wall -Wextra -Werror \
  -I"$VPX_SOURCE" profiles/common-media/tests/libvpx-cpudetect.c -o libvpx-cpudetect
ruby profiles/common-media/tests/lame-fixtures.rb prepare NEW_AUDIO_FIXTURES
ruby profiles/common-media/tests/x265-fixtures.rb prepare NEW_VIDEO_FIXTURES
```

Transfer those executables, fixtures and `tests/ffmpeg-runtime.sh` to the board.
Run both dispatch regressions and the media runner there:

```sh
./libaom-cpudetect
./libvpx-cpudetect
sh ffmpeg-runtime.sh AUDIO_FIXTURES VIDEO_FIXTURES NEW_RESULTS
```

The dispatch checks call the actual patched source with real generated build
configuration. They verify heterogeneous CPUs, absent/truncated data, reserved
bits, unsupported SVE and environment masks. They also report the live kernel's
capabilities. Transfer the results back to the host and verify PCM independently:

```sh
ruby profiles/common-media/tests/ffmpeg-audio.rb RESULTS AUDIO_FIXTURES
```

## Accepted bounded run

On 2026-10-12 CM5 Rev 1.0, BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B passed with
experimental `EMBERV3DRENDER #0`, kernel source
`ab6f88f04ca73c6958adb39d0e1c717f629e7901`. Kernel SHA256:
`c8600af1c6a31404fe6b3a3995196a910efda594c708194369925adb54ff1886`.
The original firmware revision is unknown. The kernel was not replaced, and
boot time stayed unchanged throughout these checks.

- H.264, H.265, AV1 and VP9 each encode four changing 64×64 YUV420 frames.
  Decoded output exactly equals all 24,576 fixture bytes; ffprobe confirms
  dimensions and four frames. Explicit scalar AV1/VP9 encode and decode also
  reproduce every byte. Live dispatch reports NEON/CRC32/DotProd for libaom
  and NEON/DotProd for libvpx, without I8MM/SVE.
- MP3 and Opus each decode to 44,100 PCM samples. Independent host checks
  measured 30.46 dB and 42.33 dB signal/noise respectively. Unicode MP3 title
  metadata survives. These are software files; no sound device was opened.
- Two inverse flips preserve the original pixels. Malformed media is rejected.
- Full package checks passed; target `pkg_admin check` verified 294 files from
  FFmpeg, libaom and libvpx. The transferred package hashes match the host.
  The original dependency bundle was compared file-by-file with the sysroot.
- GCC16 compiled the two dispatch regressions with warnings as errors;
  Cppcheck 2.22 found no diagnostics in the two modified dispatch units and
  their regression sources. This is not an audit of every codec source.
  Valgrind and the complete FFmpeg FATE suite were not run.

| Artifact | SHA256 |
|---|---|
| FFmpeg 9.0.2 package | `a9e41eb774bc50b9d4a5a40412c2b269f2bca1797ac8d1f8f2bb74b7d92adf3a` |
| libaom 3.15.0nb1 package | `b926de6a261190bca6c49d546bb9184823992bef808a314b252c9e5344bc0f5f` |
| libvpx 1.16.0nb2 package | `2812c57e598e46a437c59e0997a85f237e0900bb33c36a6b68c8e9f7c19a521a` |
| Target file-codec results | `457f3720448ec9390bf7be2e7b60010add7c51d4556d79c4b55945c4c901df32` |

The [separate x265 check](x265.md) also decodes NEON/scalar H.265 output with
an independent host FFmpeg. None of these short CPU-codec tests is a GPU
performance measurement or long-running playback acceptance.
