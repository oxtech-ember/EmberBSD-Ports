# PulseAudio 17.0 for the common desktop stack

The full PulseAudio 17.0nb9 package cross-builds on macOS for EmberBSD/AArch64.
It retains the normal Avahi/X11 options, clients, server, modules, development
files, documentation, translations and completions. TDB and libdaemon have
[separate cross-build and CM5 acceptance records](audio-dependencies.md).
PulseAudio is part of the Qt Multimedia dependency chain; it does not prove
working speakers, GPU video decoding or an accelerated Plasma desktop.

The [upstream archive](https://freedesktop.org/software/pulseaudio/releases/pulseaudio-17.0.tar.xz)
and its SHA256 are pinned in [sources.tsv](sources.tsv). This is the current
published upstream release. The inherited pkgsrc recipes, licences and RCS
identifiers remain. The additional patches and tests are AI-assisted EmberBSD
work, with no upstream submission or acceptance claim.

## Portability fixes

The recipe separates host Bash for `git-version-gen` from target Bash for
installed helpers and completions. It checks atomic-header availability in the
target sysroot. Normal installation uses pkgsrc's existing service-account
hooks; installing files into a sysroot does not create accounts on the host.

Two defects were reproduced on CM5 before source changes:

- Locale conversion passed an empty encoding name to `iconv_open`. EmberBSD
  libc does not implement that GNU extension, so even ASCII conversion failed
  and `parec` could not set its media name. The patch resolves the current
  codeset through `nl_langinfo(CODESET)` and keeps invalid-input refusal.
- The `dladdr` fallback of `pa_get_binary_name` returned an allocated path
  without filling the caller's buffer. Clients then read uninitialized bytes
  as their process name. The patch copies the basename into the bounded
  buffer, releases the temporary path and returns the supplied buffer.

`tests/pulseaudio-api.c` fails independently for both original paths. After
fixing them, C and UTF-8 locale round trips, malformed input, the returned
pointer, basename and tiny-buffer truncation all pass. Compile it with the
target compiler, C11, warnings-as-errors, `--export-dynamic`, the sysroot's
PulseAudio headers and `-lpulse`; use the ordinary `/usr/pkg/lib` RPATH.
Run its `locale` and `name` modes on the installed board.

## Finite audio check

Generate and inspect the deterministic PCM on the build host:

```sh
ruby profiles/common-media/tests/pulseaudio-pcm.rb generate NEW_PCM
# Transfer PCM and the runtime script to the installed board, then run there:
sh pulseaudio-runtime.sh PCM NEW_RESULTS
# Copy the capture back and compare on the build host:
ruby profiles/common-media/tests/pulseaudio-pcm.rb check PCM RESULTS/capture.s16le
```

The runner creates a private server, protected Unix socket, home directory and
null sink. It opens no hardware audio device and starts no persistent service.
It waits for real monitor capture before playback and uses short silence guards
around the 12,000 deterministic mono samples. Those guards allow the null-sink
monitor's startup/rewind latency to settle; the payload comparison remains
exact. The test also rejects a missing file, checks that playback streams are
released and waits for server shutdown. An outer 60-second timeout is advised.

## Accepted bounded run

On 2026-10-12 the same CM5 and experimental fan/V3D kernel as the
[dependency receipt](audio-dependencies.md) passed both API regressions and the
private-server check. All 12,000 payload samples and both silence guards match
byte-for-byte at 48 kHz, signed 16-bit mono. The captured stream contains
38,751 samples; the complete padded fixture starts at sample 5,892.
`pkg_admin check` verifies all 226 recorded regular package files. Boot time
did not change. No physical output, network sound service or long soak was tested.

Cppcheck 2.22 processes the two patched implementation units and the new C
regression using actual cross-compiler preprocessing. It reports inherited
style diagnostics but no warning/error in that scope. This is not an audit of
every PulseAudio module. Valgrind was unavailable.

| Artifact | SHA256 |
|---|---|
| PulseAudio 17.0nb9 | `5b7071de1ca55236cfc0cd065fdb8a479c80e75fad374fc58aa180786e410966` |
| Private-server results | `310d86f69a215ec7bbf2b61aefb087820f6a0a6d6682076838ff405785b3fd78` |
