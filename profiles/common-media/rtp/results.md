# E35 H.265 RTP acceptance

Recorded on 2026-10-15 UTC for the explicit [CPU SDK](README.md) and
[installed C API example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/media/h265-rtp).
Providers are FFmpeg 9.0.2, GStreamer 1.28.8, GLib 2.90.1, x265 4.2,
libxml2 2.15.4, PCRE2 10.49 and libffi 3.8.0, built with GCC16.2.0.

| Environment | Recorded result |
| --- | --- |
| Native x86_64 Linux control | All seven installed FFmpeg/GStreamer API cases passed independent wire, pixel and timestamp checks. |
| AArch64 EmberBSD, full-system QEMU | All seven cases passed; 13 real packages passed installation, dependency protection, removal and reinstallation; both clean cases passed again after reinstallation. |
| AMD64 EmberBSD, full-system QEMU | All seven cases passed; 13 real packages passed installation, dependency protection, removal and reinstallation; both clean cases passed again after reinstallation. |

The accepted kernel/base sources are
`267ee85eee1027198175809a8b7b0572df36ad1e` for AArch64 and
`c5d396f5698b68e956b29ee5b256bc7877e6c517` for AMD64 (NetBSD 11.0 ABI).
The AMD64 base retains GCC12.5; the media applications and selected C++
runtime use GCC16.2.0. This does not claim the entire AMD64 base was rebuilt
with GCC16.
The loader resolved the installed plugins from `/usr/pkg/lib/gstreamer-1.0`,
FFmpeg libraries from `/usr/pkg/lib/ffmpeg9`, and GCC16 C++ libraries from
`/usr/pkg/gcc16/lib`, without a library-path override. The C++ runtime probe
passed 15 checks on each target. All 87 upstream checks passed on each:
17 H.265 RTP and 70 jitter buffer checks, with normal Check fork isolation
and installed test data.

## Wire, pixels and recovery

Each direction sent 40 deterministic lossless 96×64 I420 frames at 10 fps.
Both clean receivers reproduced every pixel of all 40 frames. Independent
capture inspection checked RTP version, sequence numbers, PT 96, SSRC,
RFC 7798 single/AP/FU payloads, complete NAL reconstruction, unchanged
forwarded datagrams and 9,000-tick frame timestamp increments.

Dropping one middle VCL fragment recovered an exact final 32-frame sequence
in each direction. Combined loss, duplication, reordering and a timed blackout
recovered the exact final 20 frames. Each target's FFmpeg receiver emitted
four damaged frames in the single-loss case; the combined case produced
seven on AArch64 and six on AMD64. These were identified separately,
rather than counted as correct recovery.

The receiver-restart case actually destroyed the GStreamer pipeline, closed
its UDP socket, paused and created a fresh receiver. Its two timestamp
segments contained 21 and 12 exact frames; the final 12-frame sequence matched
the fixture. UDP has no connection handshake. Receiver idle termination and
locally injected EOS are reported separately from a wire-level end condition.

## Production fixes and package checks

The FFmpeg CPU build applied all 20 canonical recipe patches. The final
actual-source clock/RTP-Info/reset/NPT suite passed 52 checks on native and
both targets. Both parser-position controls (`-1` and `0`) emitted 40 frames
with the expected PTS and positions. The preserved 19-patch control failed
four NPT-bound checks; the final initialization fix reduced these to zero.

The GStreamer cached-memory mapping regression passed normal, unavailable
input and unavailable cached-parameter modes, with zero live test memory and
balanced successful mappings. Its preserved failing control crashed before
the map-error handling fix.

All 13 package archives for each target were compared with permanent recipe
inventories: exact bytes, links, modes, owners, prefix, dependency directives
and build provenance matched. AMD64 created its archives in the accepted
boot; AArch64 reused SHA256-verified target-created archives. On each target,
`pkg_admin check` verified 1,821 files before removal and after reinstallation.
Wrong-architecture metadata was rejected, and removing four still-required
providers was correctly refused.

Initial image-composition failures were resolved before this acceptance:
the AArch64 base retained its own coherent unwinder across package removal;
`/usr/lib/i18n` and `/usr/share/i18n` restored GLib's 646/ASCII-to-UTF-8 error
conversion; the socket-buffer ceiling was raised to 8 MiB and the relay
verified a 1 MiB receive buffer; upstream tests received their required
whitelist and installed `h265.rtp` fixture. Final logs contain no GLib critical
or unsupported-conversion messages.

## Evidence and limits

The AArch64 `acceptance.tgz` SHA256 is
`416a8bdcdfccc583692dc03c5659487047c49176f55cd6f6af4925abf28f8c7a`.
The AMD64 archive SHA256 is
`3ea001f3b3cfd1f46a0129c1331e27a92074f86a6b1d414d1db07bc79359ec89`.
Each archive's nine scenarios and 13 package archives passed independent host
validation after collection. Raw captures, frames, reports, package hashes
and failed controls are retained with the run.

Native FFmpeg regressions and focused memory-error controls passed raw
Memcheck. Positive GStreamer pipelines retain known GLib process-lifetime TLS
allocations; raw results and narrowly scoped filtered results remain separate
([controls and limits](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/media/h265-rtp/tests/memcheck)).
GCC/Clang analysis retains unrelated upstream diagnostics; exact-preprocessed
Cppcheck/Clang inputs have documented SDK parser/builtin gaps. This does not
establish whole-SDK analysis cleanliness, target Memcheck coverage, hardware
codec support, or performance under production network load.
