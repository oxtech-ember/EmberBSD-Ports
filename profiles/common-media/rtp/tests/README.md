# Causal FFmpeg RTP regressions

These small tests exercise the actual FFmpeg 9 source and installed C API.
They do not vendor FFmpeg source or replace its RTP clock, HEVC parser or UDP
implementation. Own harnesses use MIT licensing; included upstream code and
generated support retain their original licenses. See the [media profile](../../README.md).

## Clock and parser position

Prerequisites are a configured GCC16 FFmpeg 9.0.2 build, its matching installed
prefix, Ruby on the development host, and Valgrind for native execution.
`SOURCE` is the actual FFmpeg source tree and `BUILD` contains `config.h` and
`ffbuild/config.mak`. `PREFIX` contains `include/ffmpeg9` and `lib/ffmpeg9`.
The driver uses that build's real compiler, configuration flags and headers.

Obtain `CHECKER` and a clean `RECEIVED.rtp` from the
[Examples H.265/RTP API acceptance](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/media/h265-rtp).
Use its 40-frame, 10 fps mathematical fixture, RTP PT 96, timestamp offset 0 and a
clean receive capture from the fault relay. No model or binary fixture is stored
in this repository. The independent Ruby RFC7798 checker verifies actual RTP
headers and reconstructs real NALs. A temporary instrumented copy records each
NAL's observed RTP timestamp. The driver rejects changed checker instrumentation anchors;
no timestamp is synthesized. Each record is BE32 byte length, BE64 timestamp,
then the exact reconstructed AnnexB bytes.

```
ruby ffmpeg-rtp-regressions.rb SOURCE BUILD PREFIX CHECKER RECEIVED.rtp NEW_OUT
```

`NEW_OUT` must not exist. The driver retains real commands, input hashes,
exact support-function extraction, capture validation, JSON observations and
strict Memcheck logs. All tests run with the selected installed prefix.

`ffmpeg-rtp-clock.c` includes the actual RTP translation unit to call its static
packet finalizer and RTCP parser. `ffmpeg-rtp-info.c` includes the actual RTSP
translation unit to call its RTP-Info parser. Only the exact unchanged upstream
`ff_parse_ntp_time` support function is extracted locally, preserving its license.
The patched source must pass 52 checks: zero/nonzero/high-bit origins, wrap,
RTCP before/after media, valid/absent/invalid RTP-Info, entry-presence reset and
the real PLAY/seek timestamp-reset helper, plus initialized SDP NPT bounds for
empty/unsupported syntax and valid fractional/open-ended ranges. UINT32_MAX is tested as an RTP-Info
origin; the existing incoming RTP_NOTS_VALUE sentinel ambiguity is outside scope.

`ffmpeg-parser-position.c` calls the actual source `av_parser_parse2` with
renamed entry points and the installed real HEVC parser callback. It checks 40
actual AUs with PTS 0..351000 at packet positions -1 and 0. Returned position metadata
must remain unchanged. Unknown internal byte offset normalization is tested
separately from the RTP clock origin. Records and total bytes are bounded;
partial records and timestamps outside the stated fixture contract fail.

To reproduce the original defects, use pristine pinned FFmpeg 9.0.2 source with
the same configuration/API ABI and add `--baseline`. The expected controls are
44 clock/range checks with 17 functional failures, missing first PTS at position -1,
and a passing position 0 control. These expected functional failures return 1;
Memcheck must still report zero errors, zero remaining heap and zero suppressions.
The patched controls require zero functional failures.

For cross compilation append `--build-only` and use the target's actual
SOURCE/BUILD/PREFIX. This produces `rtp-clock`, `parser-position` and
`observed-nals.bin` without executing target code. Their RPATH is
`/usr/pkg/lib/ffmpeg9:/usr/pkg/lib:/usr/pkg/gcc16/lib`. Copy the three files into
a target VM with matching runtime packages, then run under a bounded runner:

```
./rtp-clock
./parser-position ./observed-nals.bin -1
./parser-position ./observed-nals.bin 0
```

The clock emits JSON lines ending with `{"checks":52,"failures":0}`.
Both parser invocations emit `ok:true`, 40 frames, actual PTS and packet positions.
Cross-build success alone is not target execution acceptance.

## Partial RTP/RTCP open cleanup

Use the installed native Examples `ffmpeg-h265-receive` C API consumer and
its runtime libraries. `FF_LIBDIR` selects the actual libavformat DSO;
additional native dependency paths can be supplied through `LD_LIBRARY_PATH`.
`PORT` is an available localhost UDP port in 10000..65000; its adjacent RTCP port
is deliberately occupied by the test. `NEW_OUT` must not exist.

```
ruby ffmpeg-rtp-open.rb RECEIVER FF_LIBDIR NEW_OUT PORT
```

The consumer has 700 ms maximum and 200 ms idle bounds. The test makes a real
occupied RTCP bind through FFmpeg's UDP/RTP stack. It requires failed reception,
zero frames, strict Memcheck without errors/leaks/suppressions, and successful
socket rebinds after cleanup. No RTP packets are fabricated.

For the preserved native 64-bit FFmpeg 9 pre-cleanup DSO, add `--expect-leak`.
That causal control requires exactly 187 direct + 66,357 indirect lost bytes,
three Memcheck contexts and child exit 99. It is an expected memory failure,
not a clean Memcheck pass. The patched invocation requires child exit 1 for the
open failure and zero memory errors. This separates the real partial-open leak
from ordinary reception failure and verifies both sockets are released.

The neighboring `cxx-runtime` sources independently exercise installed GCC16
string ownership, cross-DSO exceptions, threads and DSO TLS. Their successful
runtime JSON contains 15 checks; this does not qualify an entire compiler.
