# RTAB-Map validation record

Checked on 2026-10-15. The build uses GCC 16.2.0, the fork's coherent
AArch64 base at `267ee85eee1027198175809a8b7b0572df36ad1e`, and the
existing `aarch64--netbsd` ABI. Native controls use Linux x86-64 with GCC16;
those controls are separate from actual EmberBSD execution.

## Toolchain status

Every result below was measured with GCC 16.2.0 and its `libstdc++.so.7`
runtime on 2026-10-15. The probe scripts now use the Ports Clang 23.1.4
toolchain with libc++ (`/usr/pkg/llvm/lib/libc++.so.1`), compiler-rt and
libunwind, and no longer use GCC. Clang validation of the cross build, the
native controls, the installed consumer test and the target acceptance run is
pending; until it is recorded here, the GCC results are historical and do not
establish the Clang build.

## Shared package boundary

RTAB-Map 0.23.8 installs two DSOs and 195 package paths. OpenCV 5.0.0
installs thirteen DSOs and 306 paths; expanded PCL 1.15.1nb1 installs thirteen
DSOs and 758 paths. SQLite 3.54.0 installs twelve paths. PNG 1.6.59 has twenty
expanded libtool payload paths; libjpeg-turbo 3.2.0nb2 has forty-one.
All target libraries and consumers are AArch64. Installed CMake exports and
runtime search paths contain no build-host directory. The native resource
generator runs on the host and is excluded from the library package.

The target package set contains Eigen, Boost headers/libraries, GCC16
libatomic, LZ4, FLANN, Boost.Iostreams, PCL, GTSAM, PNG, JPEG, SQLite, OpenCV
and RTAB-Map. Base zlib remains the provider. The PCL expansion replaces its
previous package payload; the other common providers retain their versions.

## Native runtime and memory controls

- Sixteen installed RTAB/OpenCV consumer CTests pass, including analytic
  persistence/localization, compression, private index roundtrip, dynamic
  loader, threads and repeated lifecycle checks.
- The recorded RGB-D example and independent checker pass their complete CLI
  workflow: 74 separate Memcheck executions, with zero errors, suppressions,
  definite, indirect or possible losses. Invalid input, PNG error cleanup,
  existing-output safety and finite/nonfinite corrupted exports are exercised.
- The map contains twelve nodes, eleven graph constraints, 2,400 stored visual
  word observations and 10,859 colored points. A new mapper reopens the database
  and recovers the stored RGB and float-depth bytes exactly.
- Fourteen real PCL upstream programs pass all 175 GoogleTests. All fourteen
  programs, the four original contract modes and three expanded contract modes
  pass strict Memcheck. These PCL runs free every allocated heap block.
- Thirty-seven selected real OpenCV upstream cases pass normally and under
  Memcheck, using actual production core definitions, C++17, `-O2` and signed
  char. There are no failed, disabled or skipped cases.
- Eleven PNG/JPEG checks pass under Memcheck: PNG roundtrip/transforms, JPEG
  roundtrip, YUV, 16-bit lossless, CLI encoding/decoding, empty and truncated
  inputs. SQLite's C API and valid/invalid CLI controls also pass.

Memcheck 3.24.0 reports all leak categories and treats errors and definite,
indirect or possible losses as failures. No project suppression is used.
Reachable OpenCV framework/global allocations are reported separately; the
37-case upstream run retains 2,344 bytes. Two JPEG fatal-input CLI cases retain
944 reachable stdio bytes each. These are not reported as lost blocks.

## Confirmed defects and regressions

Local patches repair unaligned compression metadata access, signed RVL word
arithmetic and truncated RVL decoding. Real complete source translation units,
actual generated headers and actual libraries reproduce the original problems;
five strengthened API modes pass both UBSan and strict Memcheck afterward.
Known RVL words, extreme/decreasing depth values and unaligned byte buffers
also verify that the wire format is retained. The legacy size-less RVL decoder
remains for trusted buffers; wrappers use the new size-bounded overload.

Helgrind reproduces utilite's plain-state race, invalid mutex unlock at
destruction and natural-completion handle race. The state, mutex and self-join
patches produce zero errors in the selected state/natural-completion tests.
POSIX join now waits for OS termination and TLS destructors, reaps completed
workers before reuse, and serializes concurrent joiners. A gated TLS fixture
fails with the old detached-worker barrier and passes after the fix. Normal,
Memcheck and Helgrind controls cover the ordinary paths; a real Linux
child-only resource limit also verifies creation failure under normal execution
and Memcheck. That deliberately failed pthread call is excluded from the
ordinary Helgrind mode, whose zero-error result is recorded separately.
Class size/alignment remain 136/8 on the selected 64-bit platforms. Raw handle/ID
access still requires external lifecycle coordination.

Actual installed mapping Memcheck originally reports 1,456 definitely and
2,224 indirectly lost bytes. Repeated lifecycle controls also reproduce the
ownership defects. The patch frees the marker detector and strategies recreated
by `close()` during final destruction, preserving reusable init/close behavior.

The private KD-tree's leaf split value was serialized before initialization;
Memcheck traced the undefined bytes through the real LZ4HC save path. The
constructor patch initializes this field without changing the index format or
allocator. A saved/restored 100-by-32 index checks independently known nearest
neighbors. Its compressed save path currently allocates and zeroes about 1 GiB;
this is bounded acceptance, not a small-memory implementation claim.

The private bundled LZ4 formerly exported public `LZ4_*` symbols. A real
RTAB-Map-to-common-FLANN load order selected version 10701 rather than 11000.
Hiding only the private LZ4 C objects retains the common provider. A loader
regression verifies the final 11000 result. OpenCV's NetBSD plugin-loader
branches now include the actual POSIX open/symbol/close operations; its fixture
checks missing inputs and load/unload state. The C loader host explicitly
links pthread at startup. Four actual target diagnostic variants isolate an
exit-time crash after late pthread loading/unloading in a plain C host;
startup-pthread and C++ hosts complete normally. This profile does not repair
or claim support for that separate late-runtime/unload case. The OpenCV foundation consumer
joins its two-worker pool at scope exit, removing the 320-byte lost TLS report
without disabling parallel processing inside the test.

## Source analysis and limits

Cppcheck 2.17.1, Clang Static Analyzer 19.1.7 and GCC16 `-fanalyzer` use real
compilation databases, target definitions, generated headers and recorded
header hashes. Paired RTAB analysis covers eleven actual upstream units:
Rtabmap, Memory, SQLite persistence, Compression, UThread, FlannIndex,
RegistrationVis, GTSAM optimization, RVL and both private LZ4 C files.
The two OpenCV core/filesystem units and selected PCL surface/segmentation
units are checked separately. New consumers and example sources also use
actual target compilation contexts.

This is not a claim that all upstream code has clean static analysis.
Cppcheck cannot parse the selected PCL registration macros; a real
GCC-preprocessed translation-unit attempt also fails in its parser.
Clang retains inherited null-dereference candidates in navigation/GPS paths
outside this example, and event-ownership modeling warnings. These remain
upstream review items, not verified failures of the recorded-map scenario.
SQLite's full amalgamation reaches the bounded Cppcheck/fanalyzer time limits;
fanalyzer also reports incomplete paths. PNG/JPEG C analysis has inherited
complexity warnings. The example PNG reader's fanalyzer run stops on its
production `-Werror` complexity diagnostics; actual production compilation,
CLI failures and Memcheck PNG cleanup succeed. No fake APIs or replacement
platform headers are used to produce a clean claim.

## Target acceptance

The final Cortex-A72 AArch64 QEMU/TCG run passes on EmberBSD 11.0 with the
pinned fork kernel and GCC16 `libstdc++.so.7`. Fourteen real pkgtools packages
are created/reused, installed, integrity checked, dependency-protected, removed
and reinstalled. Both mapping runs pass; their poses.csv, cloud.csv and map.ply
are byte-identical. The independent host checker also accepts both exported
results. All 19,211 package payload entries have a retained mode/content/link
manifest for the replay comparison; archive control timestamps may vary.

Target checks pass the sixteen installed contracts, fourteen PCL upstream
programs/175 tests, 37 OpenCV upstream cases, eleven codec cases and the SQLite
consumer. The analytic map has six nodes and corrects the supplied 25 cm pose
error to x=0.2 m. The recorded map has twelve nodes, eleven constraints and
10,859 points. Target CLI controls reject unknown arguments, missing input,
existing output and a corrupted nonfinite cloud export. The VM unmounts cleanly.
The accepted run takes about 579 guest seconds under TCG; this is not a board
performance measurement.

Physical-board, camera, calibration, visual odometry, full-sequence SLAM,
real-time and sustained-operation behavior remain unverified.
