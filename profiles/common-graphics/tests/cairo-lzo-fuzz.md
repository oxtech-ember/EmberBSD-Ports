# Cairo Script LZO fuzz pilot

The fuzz target enters the public Cairo Script Interpreter with a bounded
script template. The template places mutated LZO2A bytes in an image or Type42
font source. It reaches the scanner, dictionary/operator dispatch, and the
production decoder paths without executing an arbitrary input script or opening
an input-selected path.

The three modes cover the direct one-pixel ARGB32 image path, the A8 image
file fallback, and the embedded Type42 font source. Their decoded-size field is
bounded to 1 through 65536 bytes. The seed generator uses LZO2A compression to
create one matching-size and one deliberately undersized declaration for each
mode. A seventh seed declares one byte more than the font payload expands to.
The seven seeds are tracked in `cairo-lzo-corpus/`.

`cairo-lzo-fuzz.c` builds as a Clang libFuzzer target with ASan and UBSan. The
Cairo and LZO static archives must carry the same sanitizer instrumentation.
Build a second replay executable from the same harness and patched source with
GCC16 and ASan/UBSan. The replay binary accepts one corpus filename. Both
binaries remain host diagnostics and must stay outside packages and sysroots.
The Cairo recipe keeps LZO enabled for this pilot.

## Manifest and run

The evidence adapter checks the Cairo and LZO archive hashes against Ports
`distinfo`, checks the Meson archive hash, and records the prepared Cairo and
LZO source trees, applied recipe patches, generated build configurations,
tools, binaries, corpus and build logs. Use the work-tree layout created by
the local build procedure. `results/accepted/` contains the successful setup,
compile, link and negative-control logs.

The adapter does not record files from the moving SDK checkout. It runs
`git archive` for the checkout's `HEAD` commit and extracts the fuzz-check
modules to `<work-root>/sdk-snapshots/<commit>/`. The manifest lists those
read-only copies with that commit, and the adapter imports the SDK from them.
A later SDK commit therefore leaves `verify --manifest` valid, while a changed
snapshot file still fails it. A rerun reuses an existing snapshot only when it
matches the commit exactly. Run `fuzz-check.py` from the same snapshot.
The regression check clones the SDK checkout, adds a later `process.py`
commit, and alters the snapshot copy:

```sh
python3 profiles/common-graphics/tests/cairo-lzo-evidence-sdk.py \
  --sdk-root /absolute/EmberBSD-SDK
```

```sh
python3 profiles/common-graphics/tests/cairo-lzo-evidence.py \
  --ports-root /absolute/EmberBSD-Ports \
  --sdk-root /absolute/EmberBSD-SDK \
  --work-root /absolute/cairo-lzo-work \
  --distfiles /absolute/distfiles \
  --clang /absolute/clang-23 --gcc /absolute/gcc-16 \
  --python /absolute/python3.15 --ninja /absolute/ninja \
  --pkg-config /absolute/pkg-config --cppcheck /absolute/cppcheck \
  --output /absolute/cairo-lzo-work/results/build.json

SDK=/absolute/cairo-lzo-work/sdk-snapshots/$(git -C /absolute/EmberBSD-SDK rev-parse HEAD)
python3 "$SDK/scripts/fuzz-check.py" run \
  --manifest /absolute/cairo-lzo-work/results/build.json \
  --output /absolute/cairo-lzo-evidence \
  --runs 10000 --seed 1 --max-len 65536 \
  --timeout 300 --input-timeout 10 --rss-limit-mb 2048 \
  --memcheck optional
python3 "$SDK/scripts/fuzz-check.py" verify \
  --evidence /absolute/cairo-lzo-evidence \
  --manifest /absolute/cairo-lzo-work/results/build.json
```

The SDK runner hashes its initial inputs, applies a finite libFuzzer budget,
records the generated corpus, then replays every initial and generated file
once with the GCC16 binary and once with the separate LSan binary when enabled.
The manifest adapter requires a clean Ports checkout and rejects archives that
differ from the repository's pinned hashes. Keep the evidence directory outside
Git.

## Leak and Memcheck binaries

Build the positive control with the diagnostic host Clang. It deliberately
leaves one allocation live so the SDK runner can confirm LeakSanitizer is
active before replaying Cairo inputs:

```sh
"$CLANG" -O1 -g -fsanitize=address -fno-omit-frame-pointer \
  profiles/common-graphics/tests/cairo-lzo-lsan-probe.c \
  -o /absolute/cairo-lzo-work/bin/cairo-lzo-lsan-probe
```

The SDK runner first checks `lsan_probe`; its expected nonzero exit is accepted
only when its report names the intentional direct leak. The RSS-limited
libFuzzer and GCC16 replay use `detect_leaks=0` because libFuzzer's process-life
RSS monitor has process-exit allocations on this host. The runner replays every
initial and generated corpus file with `lsan_replay` under
`ASAN_OPTIONS=abort_on_error=1:detect_leaks=1`. A Cairo leak fails that replay.
Unretained mutations are not covered by the separate LSan replay.

Build `lsan_replay` from `cairo-lzo-fuzz.c` and the Clang-instrumented Cairo and
LZO archives. Use the GCC16 replay link line as the source of include and
library arguments. Add `-DCAIRO_LZO_FUZZ_REPLAY`, retain the sanitizers used by
those archives (`-fsanitize=address,undefined` in this build) and
`-fno-omit-frame-pointer`, and remove `-fsanitize=fuzzer`. This executable has
the one-input replay `main`; it must not link libFuzzer. Keep the full command
and output in the accepted build logs.

On a supported Valgrind host, prepare a separate `gcc16-memcheck` Cairo/LZO
build with the same source revisions, patches, Meson feature settings and
headers as the GCC16 replay build. Remove every ASan/UBSan flag from the
compile and link commands. Build `cairo-lzo-fuzz.c` with
`-DCAIRO_LZO_FUZZ_REPLAY`, `-O1`, `-g` and `-fno-omit-frame-pointer`, and link it
against those uninstrumented Cairo and LZO archives as
`bin/cairo-lzo-replay-gcc16-memcheck`. Keep its Meson command line, compile
database, link command and logs in the manifest. The SDK refuses to use the
sanitized GCC replay as the Memcheck executable.

Valgrind shows all leak classes, tracks origins and fails on definite,
indirect or possible leaks and memory errors. It reports still-reachable blocks
without counting them as lost. The SDK runner handles every initial and
generated corpus file and saves Valgrind's XML report for each replay.

## Recorded campaign

Clang 23.1.4 on macOS arm64 completed the declared 10,000-run campaign with
seed 1 and a 65,536-byte maximum input. It reported no ASan or UBSan finding.
The final corpus was retained, and the GCC 16.2.0 ASan/UBSan replay passed for
every initial and final-corpus file. SDK v1 evidence verification passed
against the current manifest.

The upstream negative control reproduced an ASan heap-buffer-overflow from the
oversized direct-image seed. This confirms the seed reaches the vulnerable
decoder path. It does not establish absence of other defects or a coverage
threshold.

The negative control builds the same harness against Cairo 1.18.6 with the
LZO repair patches omitted. The `direct-oversized` seed produced an ASan
heap-buffer-overflow in the old `lzo2a_decompress` path. The patched fuzzer
must process all seven seeds without an ASan or UBSan finding. LSan replay must
also pass the `font-size-mismatch` seed, which regresses the previously leaked
source reference and FreeType face-data allocation. A negative-control finding
is expected evidence; it is not a failure of the patched build.

The LZO Ports patches express byte alignment for optimized unaligned-access
aliases in both the library and bundled minilzo. They also reject dictionary
addresses outside the input range before calculating a match distance. This
avoids forming an out-of-bounds pointer in the non-deterministic compressor
path. No sanitizer category is disabled.

The full LZO 2.10 `make check` and `make test` pass with both Clang 23.1.4 and
GCC 16.2.0 under ASan/UBSan with `halt_on_error=1`. This includes the previous
`lzo_init()` alignment finding and the LZO1A, LZO1B and LZO1F pointer-overflow
findings. Cppcheck 2.22.0 analyzed GCC16-preprocessed `lzo1a.c`, `lzo1b_1.c`
and `lzo1f_1.c`: pinned upstream and patched source each report 92 normalized
findings with no delta. GCC16 `-fanalyzer` and Clang Static Analyzer 23.1.4
report no findings in those three translation units. The separate comparison
of `lzo_init.c` and bundled `minilzo.c` still has the same 37 existing
diagnostics before and after the alignment patch. These checks do not claim
analysis of every LZO translation unit or target EmberBSD execution.

Cppcheck 2.22.0 analyzed GCC16-preprocessed pinned-upstream and patched LZO
sources with the same Unix64 host model. Both runs report the same 37 findings,
including existing portability and style diagnostics; the patch adds none.
GCC16 `-fanalyzer` and Clang Static Analyzer 23.1.4 report no findings in the
two touched translation units. Static analysis here covers `lzo_init.c` and
the bundled `minilzo.c`, not every LZO translation unit.

## Scope and future assurance

This pilot covers the three LZO decoder call sites through the real Cairo
Script Interpreter on macOS arm64. The finite run does not cover arbitrary
Cairo scripts, the full Cairo test suite, EmberBSD ABI execution, a device, or
all dynamic dependencies. Host Pixman and FreeType are not ASan/UBSan
instrumented. Existing schema 1 campaign evidence was produced with leak
detection disabled; a new run must use the LSan positive control above before
claiming a LeakSanitizer result. Valgrind's current platform matrix does not
support macOS arm64, so an optional Memcheck result on this host is
`unsupported`, not a pass. Run Memcheck on a supported Linux or FreeBSD host.
The SDK's portable evidence is unsigned and confirms internal consistency only;
it does not attest source origin or compiler identity and is not a certificate.

An independent certification effort would need an authority-specific test
profile, a complete dependency and toolchain closure, signed and independently
retained provenance, coverage goals, reproducible campaigns, and target ABI and
device qualification. This pilot supplies a bounded test case and structured
evidence to build on; it does not claim those certification properties.
