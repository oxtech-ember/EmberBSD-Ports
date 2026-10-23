# memtester Bit Spread bounds

The common recipe is [`pkgsrc/sysutils/memtester`](../../pkgsrc/sysutils/memtester).
It replaces the pinned pkgsrc recipe and adds one local patch, with
`PKGREVISION=1`. It keeps upstream memtester 4.7.1 and its GPL-2.0-only license.
The patch is AI-assisted by OpenAI Codex (GPT-6), not submitted upstream.

## Source and semantics

- Original archive: <https://pyropus.ca./software/memtester/old-versions/memtester-4.7.1.tar.gz>
- Release: 4.7.1, December 2024; archive size: 24,590 bytes.
- SHA256: `e427de663f7bd22d1ebee8af12506a852c010bd4fcbca1e0e6b02972d298b5bb`.
- The archive entries in distinfo retain the upstream SHA512 and BLAKE2s.
- Recipe base: [pkgsrc fff4deb639a1a640476203c80f752fb77b6cb14b](https://github.com/NetBSD/pkgsrc/tree/fff4deb639a1a640476203c80f752fb77b6cb14b/sysutils/memtester).

Upstream `README.tests` describes Bit Spread as a surrounding-bit test.
The generator writes two set bits with one clear bit between them, alternating
with the complement. Its old walk reaches shift counts equal to the word width
and one greater. C leaves those shifts undefined. A machine can wrap the shift
count and produce an unrelated low bit.

The repaired walk uses all `W - 2` positions that keep both bits inside a
`W`-bit word. It visits positions `0..W-3` and then `W-3..0`. The turn repeats
the upper endpoint, as the original walk did. There are 60 comparisons on
32-bit words and 124 on 64-bit words. This preserves the two-bit spacing and
both complements without skipping Bit Spread or masking invalid shifts.

Before this fix, current [NetBSD pkgsrc](https://github.com/NetBSD/pkgsrc/tree/trunk/sysutils/memtester),
[OpenBSD Ports](https://github.com/openbsd/ports/tree/master/sysutils/memtester),
[FreeBSD Ports](https://github.com/freebsd/freebsd-ports/tree/main/sysutils/memtester),
[DragonFly DPorts](https://github.com/DragonFlyBSD/DPorts/tree/master/sysutils/memtester)
and [T2](https://github.com/rxrbln/t2sde/tree/master/package/base/memtester)
were checked. None carried a Bit Spread bounds repair. The T2 patch changes
`head` syntax; the OpenBSD size patch changes random-number generation.
This bounds change is local, rather than an attributed downstream backport.

## Reproduce

Extract and verify the original archive first. Use a native GCC16 and a new
output directory. Python uses only its standard library.

```sh
python3 probes/memtester/check.py \
  --source /absolute/memtester-4.7.1 \
  --work /absolute/new-check --cc /absolute/gcc16
```

`bitspread.c` includes the real upstream `tests.c`. It observes generated
buffers at the existing progress-output boundary. It retains the actual
comparator. The expectations are literal patterns, independent of the walk.
The check covers every position in both directions, lengths 0, 1, 2 and 5,
alternating complements, buffer guards and a deliberate mismatch that must
stop the walk. Four mutations exercise loop length, turnaround, reverse
position and complement. The unpatched source must fail before the patched
source passes. Separate UBSan trap builds require an upstream trap and a
patched pass; no sanitizer runtime library is needed. Core dumps are disabled.
The complete program also runs all enabled tests for one loop with 1 MiB.

For a native i386 diagnostic on an amd64 NetBSD host with compatible i386
startup files and libc, add:

```sh
  --cflag=-m32 --cflag=-B/usr/lib/i386/ \
  --cflag=-L/usr/lib/i386 --cflag=-static
```

For paired AArch64 analysis of both production translation units:

```sh
python3 probes/memtester/analyze.py \
  --checked /absolute/completed-check --work /absolute/new-analysis \
  --cc /absolute/aarch64--netbsd-gcc --sysroot /absolute/emberbsd-sysroot \
  --cppcheck /absolute/cppcheck --clang /absolute/clang
```

The analysis uses actual GCC target preprocessing, `-fanalyzer`, Cppcheck and
Clang Static Analyzer. Clang only analyzes source. Each runner records commands,
exit statuses and diagnostics outside Git. The native runner records input and
binary SHA256 values. These local records are not signed certification.

## Validation boundary

On 23 October 2026, GCC 16.2.0 passed both native amd64 and native i386 checks:
RED/GREEN, four detected mutations per ABI, UBSan trap pairs and complete
1 MiB/one-loop program checks. GCC16 also built the static AArch64 program
against an EmberBSD sysroot. This does not establish AArch64 execution,
package lifecycle acceptance or physical RAM stability.

Cppcheck 2.22.0 removed all four `shiftTooManyBits` findings with no new
findings. GCC16 path analysis completed for both source states. Clang Static
Analyzer 21.1.8 retained the same `core.DivideZero` path in `memtester.c`:
it models `sysconf(_SC_PAGE_SIZE)` as zero. This inherited path is unconfirmed
on the tested host. The changed `tests.c` has no CSA findings.

Other inherited Cppcheck findings remain visible: four format findings,
`badBitmaskCheck`, condition/model notices, variable scope, GNU void-pointer
arithmetic and style findings. Native i386 also exposes the upstream
`off_t`/`%lx` physical-address diagnostic mismatch. These belong to upstream
memtester, are outside this bounds repair, and do not establish physical-mode
acceptance. No finding category is suppressed. Valgrind was unavailable on
the test host; the executed substitute is UBSan in trap mode, not Memcheck.

## Linux AArch64 diagnostic artifact

The [native CI workflow](../../.github/workflows/memtester-linux-aarch64.yml)
uses the GitHub `ubuntu-24.04-arm` runner and the official GCC 16.2.0 ARM64
container pinned by digest. It runs the same source regression, causal
mutations and UBSan trap pair. Strict Valgrind Memcheck checks the real
generator/comparator regression. A separate static Linux
binary runs the complete one-loop, 1 MiB smoke check. The container permits
that memory to be locked without reducing the requested test size.

The artifact contains the static ELF64 AArch64 executable, SHA256SUMS,
GPL license, original source archive, common Ports patch, test logs and a
receipt. The receipt records the exact commit, commands, compiler image,
tool versions, input hashes and ELF machine 183. It rejects dynamic-loader
or dynamic-segment requirements. This is a Linux diagnostic candidate.
It does not accept EmberBSD ABI compatibility, package lifecycle or a
physical board. The workflow retains its downloadable artifact for 14 days.
