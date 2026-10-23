# Common multimedia source packages

The [CIX P1 media prerequisites](cix-vpu/README.md) add native stateful V4L2
M2M header selection and checked failure cleanup. Cross-build diagnostics
and EmberBSD/AArch64 missing-device execution pass. Native CIX attachment,
platform control and M2M queues remain unfinished; hardware H.265 is unverified.

The [four-stream Qt CPU profile](qt-four-streams/README.md) cross-builds
Qt 6.12 for EmberBSD amd64 with GCC16 and the common FFmpeg9 provider.
It adds a bounded raster viewer, runtime payload checks and an independent
framebuffer reader. See its [measured validation limits](qt-four-streams/results.md).

The [H.265 RTP CPU SDK](rtp/README.md) adds GCC16.2 cross builds for AArch64
and AMD64. Installed FFmpeg/GStreamer C APIs pass bidirectional transport,
packet faults and receiver restart checks in full-system QEMU. All 13 packages
pass real installation and removal/reinstallation; see [results and limits](rtp/results.md).

The [GCC16 CPU cross package](cross/README.md) passes real installation,
dependency protection, exact FFV1/PCM checks and removal/reinstallation in
EmberBSD AArch64 QEMU. It retains built-in codecs and uses current OpenSSL/XML;
normal external-codec and CM5 results keep their separate selection and scope.

The [complete speech packages](speech.md) also provide tested Sonic, eSpeak NG,
Flite and speech-dispatcher for Qt/KDE on CM5.

The profile pins the complete [GStreamer 1.28.8 source family](gstreamer.md)
for the export. Its core cross-build corrections preserve introspection.
Complete [base/bad plugin packages](gstreamer-plugins.md) now pass bounded
CM5 introspection, conversion and parser checks; other plugin packages remain separate.
The complete [LAME 4.0 MP3 dependency](lame.md) cross-builds with GCC 16;
encoding, Unicode tags and decoding passed a bounded installed check on CM5.
The [x265 4.2 cross recipe](x265.md) also preserves its full package; CM5 NEON
and scalar streams decode independently to the exact source pixels.
The complete [PulseAudio 17.0 package](pulseaudio.md), together with
[TDB and libdaemon](audio-dependencies.md), now has cross-build and bounded CM5
acceptance. PulseAudio passes locale/buffer regressions and exact null-sink PCM
playback/capture; this does not validate physical audio output.

This profile moves Plasma's media consumers to one **FFmpeg 9.0.2** package.
Qt Multimedia 6.12 and KFileMetadata both select `multimedia/ffmpeg9`.
The complete Qt Multimedia package now passes an [installed CM5 player check](../../probes/plasma-mobile/toolkit/tests/qt-multimedia/README.md)
with exact software-decoded pixels and failure controls.
The profile composes common tools and graphics with the final `/usr/pkg`
prefix. The [full FFmpeg package](ffmpeg-runtime.md) now passes bounded CM5
file-codec scenarios. Qt Multimedia playback and the complete Plasma Mobile
session remain unaccepted.

The recipe updates pkgsrc's existing FFmpeg 9.0.1 package. It retains normal
encoding, decoding, filters, network protocols, static development libraries,
shared libraries, command-line tools and the default external codec options.
It does not substitute the deliberately limited [media probe](../../probes/media/README.md).
The versioned pkgsrc paths (`ffmpeg9`, `lib/ffmpeg9`, `include/ffmpeg9`) identify
this one selected provider. Older FFmpeg packages conflict at installation;
old recipes are rejected by the common profile. Rebuild every installed media
consumer before retiring the recovery stack; never alias old SONAMEs.

## Prepare

```sh
sh scripts/prepare-pkgsrc.sh /absolute/new-pkgsrc
```

Use this order in the staging build's private MAKECONF:

```make
.include "/absolute/prepared-pkgsrc/EMBERBSD-COMMON-TOOLS-MK.CONF"
.include "/absolute/prepared-pkgsrc/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
.include "/absolute/prepared-pkgsrc/EMBERBSD-COMMON-MEDIA-MK.CONF"
```

The export replaces the upstream FFmpeg recipe. Preparation
changes only the new export. Native package builds inherit GCC16 and the
platform, prefix, Python and graphics requirements of the common profiles.
The media profile rejects old recipes, another source version, dependency
provider overrides and command-line replacement of configure arguments.

## Features and provenance

The source pin comes from [the original stable release](https://ffmpeg.org/download.html)
and [sources.tsv](sources.tsv). SHA256, BLAKE2s, SHA512, size and the 21
RCS-filtered patch SHA1 hashes are recorded. This is HTTPS/hash verification,
not a claim of release-signature verification. The recipe base is pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`, `multimedia/ffmpeg9`.
All 16 imported patches, RCS identifiers, ownership and licences are retained.
The additional adaptations and tests are AI-assisted EmberBSD work; none has
been submitted or accepted upstream.

The inherited Sun/NetBSD audio port used removed `AVCodecParameters.channels`
and public format registration structures. The added patch follows FFmpeg9's
OSS implementation: channel layout, `FFInputFormat`/`FFOutputFormat`, public
fields under `.p`, and explicit device registration in `alldevices.c`.
It preserves the original audio implementation and authorship. Compiling the
objects alone missed the absent registration; the regression checks both.

The RTP clock adaptation tracks initialization independently of timestamp
values, including zero and wraparound, and retains the first parser PTS when
network input has no byte position. Its regressions use the real RTP clock
and parser implementations; see the [CPU RTP profile](rtp/README.md).

External dependencies are selected explicitly with `PKG_OPTIONS.ffmpeg9`;
opportunistic host autodetection is disabled. Default AV1, H.264/H.265,
VP8/VP9, MP3, Opus, Vorbis, Theora, Speex, subtitles, fonts, WebP, Blu-ray,
GnuTLS and X11 options remain. Base bzip2/xz/zlib/XML support is explicit.
Freetype also selects HarfBuzz, needed by current drawtext. The buildlink
closure now follows the actual codec/SSL options, including aom/dav1d,
rather than checking the nonexistent `av1` option. The existing `ffplay9`
consumer explicitly enables its buildlinked SDL2 with autodetection disabled.

The optional `rpi` option retains MMAL; FFmpeg9 removed OpenMAX and its old
`--enable-omx-rpi` flag. This is not a Raspberry Pi hardware acceptance claim.
OpenSSL3 uses the version3 licensing configuration; the inherited FDK AAC
option still carries its nonfree distribution restrictions. VAAPI/VDPAU
remain conditional on the selected X11 and library options, not promises
of hardware decoding on EmberBSD.

## Verification

```sh
OPENSSL=/path/to/openssl sh profiles/common-media/tests/source.sh DISTFILES NEW_WORK
BMAKE=/path/to/bmake sh profiles/common-media/tests/selection.sh EXPORTED_PKGSRC NEW_WORK
BMAKE=/path/to/bmake sh probes/plasma-mobile/toolkit/tests/dependencies.sh NEW_WORK
sh scripts/tests/export-composition.sh NEW_WORK
# On NetBSD, with already patched original FFmpeg sources:
sh profiles/common-media/tests/native-audio.sh PATCHED_FFMPEG_SOURCE NEW_WORK
```

Source checks verify the original archive, zero-fuzz forward patching,
altered/repeated input rejection and source-derived headers/library versions,
text documentation, examples, executable alternatives and the production
make-generated man-page inventory. Export checks cover all six modes.
The actual BSD make recipe checks retain host-only dlopen/license failures;
they do not pretend to be native package configuration. They verify both
consumer dependencies, default codec selection and forbidden overrides.

On 2026-10-07, native NetBSD11/AArch64 passed with both the existing GCC12.5
and the selected GCC16.2 candidate: all three adapted Sun audio objects
compiled and both input/output registrations were generated.
The old port failed on the removed channel/format API and registered neither
device. This bounded check installed nothing and performed no audio-device I/O.
It does not accept the complete GCC16-built FFmpeg package, linking or audio runtime.

The consumer check uses actual upstream KFileMetadata extractor/support sources,
Qt Multimedia's FFmpeg discovery module and its FFmpeg definitions header:

```sh
qt-cmake -S profiles/common-media/tests/consumers -B NEW_BUILD -G Ninja \
    -DKFILEMETADATA_SOURCE=VERIFIED_KFILEMETADATA_6_30 \
    -DQTMULTIMEDIA_SOURCE=VERIFIED_PATCHED_QTMULTIMEDIA_6_12 \
    -DECM_SOURCE=VERIFIED_ECM_6_30 -DFFMPEG_DIR=INSTALLED_FFMPEG_9_PREFIX
cmake --build NEW_BUILD --parallel 1
sh profiles/common-media/tests/consumers/run.sh \
    NEW_BUILD/consumer-api INSTALLED_FFMPEG_EXECUTABLE NEW_WORK
```

On macOS/AArch64, existing QtCore6.11.2 and FFmpeg9.0.2 passed compilation and
real metadata extraction (dimensions, codec and title), plus malformed-media
rejection. KFileMetadata6.30 requires Qt>=6.9; this test does not alter its
source requirements. Qt Multimedia's complete plugin was not built or played.
This is a host API check, not evidence of an installed Qt6.12/FFmpeg9 native stack.

Full package/check-files and selected installed codecs are now covered by the
[CM5 receipt](ffmpeg-runtime.md). Complete FATE, Qt Multimedia playback and
installed KFileMetadata extraction remain mandatory
before the [common userspace transition](../../probes/plasma-mobile/toolkit/MIGRATION.md).
The PLIST is source-derived; no file is exempted from native checking.
