# GCC16 FFmpeg CPU cross package

Linux GCC 16.2.0 cross-builds FFmpeg 9.0.2 for EmberBSD AArch64. The installed
package passes exact file-codec checks in QEMU on 2026-10-14. It includes both
CLI programs, all seven library interfaces, static archives, headers, examples
and non-HTML documentation. Its 252 files match the canonical FFmpeg9 PLIST.

This option selection retains the complete built-in CPU codec/filter set.
OpenSSL, libxml2, zlib, bzip2 and LZMA are enabled. External x264, x265, AOM,
Opus and other optional providers are outside this selection. The ordinary
recipe and the separate [full CM5 acceptance](../ffmpeg-runtime.md) retain
their normal external-codec options.

## Inputs and build

Use the GCC16 compiler prefix and a sysroot built from EmberBSD source. Keep
the upstream `aarch64--netbsd` triplet and `NetBSD` CMake platform. The accepted
base source revision is `267ee85eee1027198175809a8b7b0572df36ad1e`.
Do not combine libc, headers or runtime modules from a different OS revision.

The sysroot needs the GCC16 CRT/runtime, OpenSSL 3.5.7 and its base pkg-config
files, compression libraries and `libossaudio`. The target needs the fork's
`lib/i18n_module` and `share/i18n` output for iconv encodings. Missing runtime
encoding data made four upstream EUC-JP checks fail in the initial minimal
image. Installing those actual fork components resolved the failures.

The helpers require GCC16 on the host and target, CMake, Ninja, GNU Make,
pkg-config, patch, tar, checksum tools, Perl, pod2man and makeinfo. They reject
existing output paths and verify archives and the complete patch inventory.
The [preflight regression](../../../scripts/tests/cross-preflight.sh) verifies
existing-work preservation and corrupt-archive rejection for all four helpers.

```sh
./build-libxml2.sh /absolute/gcc16-prefix /absolute/emberbsd-sysroot \
    /absolute/cache/libxml2-2.15.4.tar.xz /absolute/new-xml-output
# Copy new-xml-output/stage/usr/pkg into the selected task sysroot's usr/pkg.
./build-ffmpeg-cpu.sh /absolute/gcc16-prefix /absolute/emberbsd-sysroot \
    /absolute/cache/ffmpeg-9.0.2.tar.xz /absolute/new-ffmpeg-output
```

[sources.tsv](../sources.tsv) and [dependencies.tsv](dependencies.tsv) pin
the official archives. FFmpeg's SHA256 is
`8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e`.
The helper applies all 19 native recipe patches with zero fuzz. It records
configuration, build/install logs, tool versions, ELF linkage and stage hashes.
Installed pkg-config metadata uses target paths rather than build-host paths.

libxml2 uses the same current 2.15.4 source as the ordinary provider. Its cross
payload uses upstream CMake defaults and contains 61 files, including programs,
headers, exports and license notices. The native Autotools payload keeps its
normal legacy/zlib/HTTP-compatibility options and PLIST. They are different
build selections of the current provider, not interchangeable file inventories.

The [2.15.4nb1 recipe](../../../pkgsrc/textproc/libxml2) fixes a signed schema-option
shift. GCC16 UBSan reproduces the original failure for options value zero.
The patched regression accepts supported flags and rejects unsupported bits.
Two unchanged test drivers omitted from the release archive are restored from
the verified upstream tag. All 22 upstream tests then pass under UBSan.

## Target acceptance

Create real packages with [package-cross-stage.sh](../../../scripts/package-cross-stage.sh).
Use FFmpeg's stage and resolved canonical PLIST. The XML helper supplies its
exact cross PLIST. Build metadata must record the actual options and external
shared-library requirements. Declare `DEPENDS=libxml2-2.15.4nb1`; the packager
registers that dependency in `+CONTENTS`. Install the actual XML package before
creating FFmpeg so pkg_create also records its installed build dependency.

Run [run-ffmpeg-target.sh](run-ffmpeg-target.sh) with both packages, independently
prepared audio/video fixtures and a new output path. It uses real pkg_add,
pkg_info, pkg_admin and pkg_delete. A missing compiler-package registration is
not replaced by a fabricated database entry.

| Check | Accepted EmberBSD AArch64 result |
| --- | --- |
| Package integrity and loader paths | Both programs and current XML/OpenSSL dependencies resolve |
| FFV1 encode/decode | Four changing 64x64 YUV420 frames match all 24,576 reference bytes |
| Frame timestamps | 0.000000, 0.042000, 0.083000, 0.125000 |
| Inverse filters | Two horizontal flips restore the original frames |
| PCM encode/decode | All 44,100 mono samples and one-second duration match |
| Damaged inputs | Invalid data and truncated Matroska return the specified decoder errors |
| Dependency protection | Removing XML while FFmpeg depends on it fails |
| Removal/reinstallation | Files and registration disappear; both pipelines pass after reinstall |
| Upstream FFmpeg core | Adler32, audio FIFO, CRC, FIFO and hash tests pass |
| XML contracts | Exact provider/version, XPath, serialization and malformed/oversized input checks pass |
| XML upstream target tests | testchar, testdict and testparser pass |

The FFmpeg core executables use the installed library and upstream reference
files. Adler32 uses upstream's return-status check. No reference values are
generated from the target output.

## Source and memory checks

On supported x86_64 Linux, GCC16 controls pass 11 FFmpeg/ffprobe runs under
Valgrind 3.24.0 with zero errors and zero definite/indirect losses. Five core
tests also pass Memcheck with zero retained bytes. The control builds only
the exercised codecs and disables x86 assembly for instrumentation. This does
not certify all built-in codecs or AArch64 assembly paths.

Cppcheck 2.17.1 inspects 13 selected production translation units with the
actual target configuration. Matroska encoding also uses GCC-preprocessed
input because the checker cannot parse one token-paste macro. GCC16
`-fanalyzer` covers seven relevant units. The Sun audio baseline fails modern
API compilation; the existing recipe repair compiles. Diagnostic records
remain available, including SDK-header shifts and unproven lifetime findings.
These checks are bounded analysis, not a clean whole-program claim.

The current XML provider has full production Cppcheck coverage. The confirmed
schema shift is repaired. Remaining pointer-copy, debug allocator and UTF-8
loop diagnostics retain their source context. Five XML native controls pass
Memcheck; the public provider check resolves the real symbol with dlsym so
an ELF executable PLT does not masquerade as the loaded library.

The accepted VM uses QEMU 10.0.13 TCG, Cortex-A72, two CPUs and 2 GiB RAM.
This proves CPU file processing and package behavior. Audio devices, cameras,
network media, hardware codecs, GPU/NPU paths and sustained board operation
remain separate acceptance work.
