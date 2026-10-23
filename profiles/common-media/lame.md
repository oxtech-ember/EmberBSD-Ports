# LAME 4.0: cross-built MP3 dependency

The complete `audio/lame` recipe supplies the MP3 encoder used by the common
FFmpeg provider. LAME 4.0 is the [current stable upstream release](https://lame.sourceforge.io/).
The package retains the CLI, shared/static library, development headers,
pkg-config metadata, manual, HTML documentation and default Unicode support.
The original archive is pinned in [sources.tsv](sources.tsv).

## Portability changes

`4.0nb3` retains pkgsrc's recipe, three patches, RCS identifiers and upstream
licences. The additional [encoding patch](recipes/audio/lame/patches/patch-zz-frontend-encoding)
is AI-assisted EmberBSD work; it has not been submitted or accepted upstream.

- The internal ID3 dispatcher accepts an encoding-discriminated payload.
  UTF-8 setters receive character strings; UTF-16 setters receive wide strings.
  The inherited UTF-16 parameter caused eight incompatible-pointer errors.
  The recipe no longer suppresses incompatible-pointer or implicit-declaration diagnostics.
- UTF-8/UTF-16 conversion uses standard iconv names. EmberBSD's Citrus iconv
  rejects the GNU `//TRANSLIT` suffix; the old CLI silently wrote empty tags.
  Latin-1 retains GNU transliteration where supported and otherwise opens the
  standard converter. This does not add GNU transliteration to the base library.
- User-supplied UTF-8 fields use the UTF-8 setter after validating `ID=value`.
  The inherited generic setter interpreted those bytes as Latin-1.

The patch follows the inherited pkgsrc patches in lexical order, matching
pkgsrc's real patch application. The source gate uses that same order.

## Reproduce the bounded runtime check

Prepare the export with the usual
[profile instructions](README.md). Cross-build full `audio/lame` and its
`audio/mpg123` dependency against a verified EmberBSD sysroot. Install both
packages on the target; the build host does not execute target programs.

On the development host:

```sh
ruby profiles/common-media/tests/lame-fixtures.rb prepare NEW_FIXTURES
cp profiles/common-media/tests/lame-runtime.sh NEW_FIXTURES/
# Transfer the fixtures and packages, verifying SHA256 at both ends.
```

On EmberBSD, run with the installed packages and `timeout` available:

```sh
sh NEW_FIXTURES/lame-runtime.sh NEW_FIXTURES NEW_RESULTS
```

Copy the results back and verify the actual MP3 tags and decoded audio:

```sh
ruby profiles/common-media/tests/lame-fixtures.rb verify COPIED_RESULTS NEW_FIXTURES
```

The test generates one second of mono 44.1-kHz PCM, encodes both UTF-8 and
UTF-16 metadata, then decodes with the installed mpg123. It checks eight text
fields including accented and non-Latin characters, exact sample count and
signal-to-noise ratio above 20 dB. A malformed custom field must fail without
an encoded output. No audio device is opened. The host verifier understands
ID3v2.3/UTF-16 and ID3v2.4/UTF-8 frame sizes.

## CM5 acceptance, 2026-10-12

CM5 Rev 1.0, BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B ran the complete packages
built on macOS/AArch64 with GCC 16.2.0 and the existing EmberBSD sysroot.
The kernel source revision was `ab6f88f04ca73c6958adb39d0e1c717f629e7901`;
its SHA256 was `c8600af1c6a31404fe6b3a3995196a910efda594c708194369925adb54ff1886`.
This check preserved the configured fan kernel. The boot timestamp was unchanged.

Both encodings preserved all eight expected fields and decoded to 44,100
samples with 30.46 dB SNR. The original conversion returned empty title tags;
the byte verifier rejected that baseline. Malformed `--tv` input was rejected.
All 50 installed files from LAME/mpg123 matched the cross sysroot by SHA256;
`pkg_admin check` passed. Standard package file, interpreter, permission,
PIE/RELRO, RPATH and work-directory checks also passed.

| Object | SHA256 |
|---|---|
| Original `lame-4.0.tar.gz` | `3df5124d5ad3a98312ffd7ba6a9b36230e4f8a3e66d3ce0f425e336c32d216eb` |
| `lame-4.0nb3.tgz` | `6381a6b2127a3ba459045723a858c0e8043dedc9e7f7ae94e576908d44ecdbd5` |
| `mpg123-1.33.7.tgz` | `4aad719efd0100781294d36ebca0e085bbf6de02f529dbf4c289597ae1718934` |
| Target result archive, including installed-file manifest | `8ca5d8f466b3712d59b1b93dc818559bf6bd98d3e043fca9ffaa105aed028dd9` |

All 11 original media archives and their patch hashes passed verification.
The new LAME patch also applied to a clean archive without fuzz; a real clean
pkgsrc build confirmed patch ordering. Both media export modes rejected a
missing adaptation or an altered LAME source pin before creating a destination.

Cppcheck 2.22 analyzed 28 actual C compilation units. The whole upstream tree
is **not clean**: allocation, bounds, pointer and portability findings remain.
The changed `parse.c` has no warning/error findings in the repeat, but inherited
style findings still make the strict command nonzero. No findings were suppressed.
Valgrind was unavailable, so this is not a Valgrind or exhaustive memory-safety pass.

This accepts a short installed MP3 scenario. It does not accept all codec
modes, streaming, audio-device output, the full FFmpeg package, Qt Multimedia
playback or an accelerated Plasma desktop.
