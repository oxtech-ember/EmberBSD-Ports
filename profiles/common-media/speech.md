# Complete speech packages on EmberBSD

Sonic, eSpeak NG 1.52.0nb5, Flite 2.2nb3 and speech-dispatcher 0.12.1nb6
cross-build on macOS for EmberBSD/AArch64 and pass bounded CM5 tests.
They provide the speech dependency chain for Qt TextToSpeech and KDE.
Ports owns the complete recipes, source pins and portability patches.
The [Qt consumer](../../probes/plasma-mobile/toolkit/tests/qt-speech/README.md)
checks the installed plugins and private speech service. Physical audio and
a complete Plasma session are not established by these checks.

The original archives and SHA256 are in [sources.tsv](sources.tsv).
[eSpeak NG](https://github.com/espeak-ng/espeak-ng/releases),
[Flite](https://github.com/festvox/flite/releases) and
[speech-dispatcher](https://github.com/brailcom/speechd/releases) use their
current published releases. Sonic has no current formal release: the recipe
pins the maintained `b93885dcb70aae50c6f76b0fe4e0868f029a077e` snapshot from
2026-03-14 as `0.3.0.20260314`, replacing the inherited 2024 snapshot.
Original licences, copyright and pkgsrc RCS identifiers remain intact.
Adaptations and new tests are AI-assisted EmberBSD work; no upstream acceptance
or submission is claimed.

## Cross-build changes

- Sonic's `UNAME`, compiler, archiver and flags describe the target. Host
  `uname` previously selected Darwin shared-library flags for an ELF link.
  The full CLI, header, static library and shared library remain packaged.
- eSpeak builds its target executables and all language/phoneme/MBROLA data.
  A private native compiler of exactly the same version generates the data;
  the target ELF executable is never run on the Mac. The native builder
  checks the source hash and records its compiler, tools and output hashes.
- Flite retains its existing programs, headers and static archives, and adds
  shared voice libraries and PIC archives on the target BSD ABI. Its
  buildlink dependency now includes runtime installation. Qt discovers the
  package library directory and reads the actual process environment.
- speech-dispatcher retains all three original, version-checked manpages
  instead of running target programs through host help2man. Native builds
  still regenerate them. All packaged manuals equal the archive byte-for-byte.
- The dummy module now wakes and joins its worker cooperatively. Asynchronous
  cancellation previously left the module hanging after `QUIT`; the fixed
  module also checks semaphore creation and retries interrupted waits.
  This does not disable or remove the fallback module.

Build the native eSpeak compiler first:

```sh
AUTORECONF=/absolute/native-autoreconf GMAKE=/absolute/native-gmake \
  CC=/absolute/native-cc CXX=/absolute/native-c++ JOBS=4 \
  sh profiles/common-media/cross/build-espeak-host.sh DISTFILES NEW_WORK
```

Set `EMBERBSD_ESPEAK_HOST=NEW_WORK/build/src/espeak-ng` in the cross MAKECONF.
eSpeak NG depends on MBROLA 3.3, which uses the `gnu-agpl-v3` licence.
pkgsrc builds it only after `ACCEPTABLE_LICENSES+= gnu-agpl-v3` in the
MAKECONF. Without that line, the MBROLA, eSpeak NG, speech-dispatcher and
Qt TextToSpeech builds stop at the licence check.
The accepted generator host is macOS/arm64; generated integer tables require
an explicit ABI check before accepting a different host. This limitation
belongs to this data-generator recipe, not the general EmberBSD build system.
Build the normal four packages from a common-media or plasma-mobile export.
No old parallel library or reduced target package is introduced.

## Reproduce the runtime checks

Compile `tests/sonic-runtime.c` with target GCC16, C11, `-Wall -Wextra -Werror`,
linking the installed sysroot's Sonic and libm with the target package RPATH.
Run it on the board. Generate the standard tone with `tests/lame-fixtures.rb
prepare NEW_FIXTURES`; run installed Sonic with speeds 1 and 2 on that WAV.

For eSpeak, cross-build the upstream `tests/encoding.test` and
`tests/ieee80.test` targets in its configured source tree. Copy the unchanged
`tests/` directory and the actual ELF test executables into `BUNDLE/tests`
and `BUNDLE/bin`. Libtool shell wrappers are not target executables.
Run `tests/espeak-runtime.sh BUNDLE NEW_RESULTS` on the installed board.
The script uses private scratch and six unmodified language/CLI suites.
`tests/speech-fixtures.rb RESULTS SONIC_INPUT_WAV` validates retrieved WAVs;
keep eSpeak results under `RESULTS/espeak-results-r1` and Sonic outputs as
`RESULTS/sonic-normal.wav` and `RESULTS/sonic-fast.wav`.

Run `tests/speech-dummy-runtime.sh /usr/pkg/libexec/speech-dispatcher-modules/sd_dummy
NEW_RESULTS` for the real module protocol. It replaces only the test child's
external player with a private no-op, so no physical audio device is opened.
`GMAKE=/absolute/native-gmake ruby tests/speech-manpages.rb SOURCE ARCHIVE PACKAGE`
checks the actual make rules and all three packaged manuals.

## Accepted CM5 run, 2026-10-12

CM5 Rev 1.0, BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B; firmware revision unknown.
Kernel `EMBERV3DRENDER #0`, source `ab6f88f04ca73c6958adb39d0e1c717f629e7901`,
remained unchanged, with the same boot time throughout. The kernel SHA256 is
`c8600af1c6a31404fe6b3a3995196a910efda594c708194369925adb54ff1886`.

- Sonic preserves all 48,000 streaming input samples at speed 1; speed 2
  produces 23,755 samples with preserved pitch. The CLI preserves the input
  exactly at speed 1 and produces 21,828 samples at speed 2, measured at 436.39 Hz.
- All six selected eSpeak CLI suites, including language phoneme/WAV hashes,
  pass. Encoding and IEEE80 C tests pass. Two independent processes produce
  identical English/Russian WAVs: 45,532 and 33,557 samples respectively.
  Missing input and an unknown voice are refused.
- The unchanged dummy module times out on the regression. The replacement
  passes 24 INIT/QUIT cycles, covering immediate/delayed shutdown and queued speech.
- Full package payloads match the common sysroot before transfer. Package
  checks cover Sonic 6, eSpeak/dependencies 554, Flite/QtSpeech 187,
  and speech-dispatcher 461 regular files. These are bounded runs, not a soak.

Cppcheck 2.22 passes the new Sonic and QtSpeech consumers. Sonic's two upstream
units retain style diagnostics. The dummy source's target preprocessing hits
an unsupported GLib pragma in Cppcheck; it is not a clean static audit.
GCC16's analyzer compiles the changed dummy source and Qt consumer, with
inherited unused-parameter warnings in dummy. Valgrind was unavailable.

| Artifact | SHA256 |
|---|---|
| Sonic | `a74a2cb39e2f5c1372b222186cfc22789aa4d9a72e93b42ae7c1b93c329c404a` |
| eSpeak NG | `308b264289a9f4db9e7084284d22cb642ad52cc836a86d062c50211ad0c1fd60` |
| Flite | `b7ca90267e97c215990a38fc31bb0bf1a5ff7aa62b957ce11be4bf4ddae4c337` |
| speech-dispatcher | `e15d18848f174d6978986c52bb06044aa26eec12f9ef703a9ab8c4d7a34d02fb` |
| Sonic/eSpeak results | `a39bb58e5bddec75a676efb49ff624b96be7073f19a7b6017c2f05b154d209af` |
