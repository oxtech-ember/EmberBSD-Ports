# Shared mimalloc allocator

This recipe updates the pinned pkgsrc mimalloc provider to upstream 3.6.0.
It keeps the C API, shared library major version 3 and upstream tests. The
source is the official [v3.6.0 release](https://github.com/microsoft/mimalloc/releases/tag/v3.6.0),
with the archive checksums in `distinfo`.

`PKG_OPTIONS.mimalloc` supports `malloc-override`, enabled by default to preserve
the existing package behavior. It selects `MI_OVERRIDE=ON`. The explicit
`-malloc-override` configuration selects `MI_OVERRIDE=OFF`, retaining the
`mi_*` API without replacing the process's ordinary malloc/free entry points.
The two modes are different package configurations; they are not interchangeable.

The `dynamic-tls` option selects `MI_TLS_MODEL=LOCAL_DYNAMIC` for libraries
loaded after startup. The default preserves upstream's `DEFAULT` selection.
`generic-arch` selects `MI_OPT_ARCH=OFF`; without it upstream retains its
architecture-dependent `DEFAULT`, including newer ARM instructions. Consumers
whose baseline excludes those instructions must require `generic-arch`.

The current direct shared-library consumers in the pinned catalog are
`devel/mold` 2.42.1 and `cad/solvespace` 3.1. Pinned Mold selects system mimalloc as its general
malloc replacement and needs the default override mode. SolveSpace explicitly
uses `mi_heap_new`, `mi_heap_zalloc` and `mi_heap_destroy`. Other Cargo consumers
with bundled allocator sources are not accepted as consumers of this provider.
A native Node addon such as Rollup must select the embedding configuration
explicitly and retain its allocator policy when linking the shared provider.

In 3.6.0, Darwin's default in `include/mimalloc/prim/prim-tls.h` uses
`MI_TLS_MODEL_PTHREADS`. It avoids the shared fixed slots described by the older
bundled allocator's Rust workaround. Keep the current upstream default rather
than copying that older `LOCAL`/recursion-guard configuration. Runtime checks
with the selected shared library and Node addon remain required.

The buildlink contract supports `MIMALLOC_REQUIRE_OVERRIDE=yes/no`,
`MIMALLOC_REQUIRE_DYNAMIC_TLS=yes` and `MIMALLOC_REQUIRE_GENERIC_ARCH=yes`.
It checks the selected package options at configure, after normal dependencies.
Fetch/checksum do not require an installed allocator. The pinned Mold recipe
requires override mode; SolveSpace's explicit heap API imposes no override
requirement. Rollup requires embedding mode. These consumers cannot all reuse
one incompatible artifact simply because its version and SONAME match.

Upstream [Mold 3.0.0](https://github.com/rui314/mold/releases/tag/v3.0.0) now uses a Rust `MiMalloc` global allocator whose default
features do not enable malloc interposition;
[SolveSpace 3.3](https://github.com/solvespace/solvespace/blob/v3.3/CMakeLists.txt) explicitly builds
mimalloc with `MI_OVERRIDE=OFF`. Those newer application ports are separate from
this provider change. Their existence does not establish acceptance of the
pinned packages with embedding mode.

Updating the source and exposing the option does not by itself establish build,
allocation/thread/TLS, dlopen or downstream runtime acceptance. Verify the
selected configuration and its affected consumers before reusing its artifact.

The source/options regression uses a completed pkgsrc export and the selected
native control tools. It runs 16 checks: source fetch/checksum in both modes,
actual CMake option metadata and show-options descriptions, pinned Mold's requirements, embedding/TLS/CPU
refusals, unavailable Rust at configure, refusal to execute cross binaries and
preservation of the source policy boundary:

```sh
python3 -B -I -S pkgsrc/devel/mimalloc/tests/pkgsrc-options.py \
  --pkgsrc /absolute/completed-pkgsrc --bmake /absolute/native/bin/bmake \
  --makeconf /absolute/native-mk.conf --shell /absolute/native/bin/mksh \
  --patch /absolute/declared/patch --distdir /absolute/distfiles
```

No CMake configure, allocator compilation or consumer execution is implied by
that check. Normal package, upstream tests, allocator/thread/TLS and selected
Node addon checks follow with the native compiler and shared provider.

The Rust binding tests use `lang/rust/emberbsd-cargo.mk`, with the recipe's
`Cargo.lock` and three checksum-verified build crates. CMake receives the selected
Cargo command and `--offline --locked` arguments. It retains its normal CMake
build/install targets; Cargo only compiles the upstream binding test when CTest
runs it. Cross callers supply the explicit `EMBER_CARGO_TARGET` supported by their
Rust provider. Cross `do-test` refuses to execute target binaries on the host.
No source-fetch phase requires configured Rust or C/C++ tools.

The pprof test's ten allocation functions retain separate frames with a portable
noinline annotation. The existing volatile sink prevented tail calls, but Clang
23 at `-O2` still inlined the functions and collapsed their profile locations.
No library code, compiler optimization flag or test assertion is weakened.
Replay the actual optimized CMake commands and its pkgsrc wrapper configuration:

```sh
python3 -B -I -S pkgsrc/devel/mimalloc/tests/pprof-noinline.py \
  --source /absolute/mimalloc-3.6.0 --build /absolute/cmake-pkgsrc-build \
  --wrapper-config /absolute/pkgsrc-work/.cwrapper/config --work /absolute/new-check
```

The causal control removes only the annotation from a temporary test source and
must fail its distinct-sites assertion; the patched source must pass all eight
assertions. A second injected control makes `pthread_create` return `EAGAIN`: the old
cleanup attempts an invalid join, while the fixed cleanup joins only created
threads and preserves the normal failed-test result. The existing built static
library and source tree remain unchanged.

Native Darwin Clang 23 trial packages passed all upstream CTest tests in both
configurations: 15 with override, 13 with embedding (the two override-only tests
are defined by upstream only when override is enabled). These include the real
Rust binding tests with Rust 1.99.1. `tests/shared-runtime.py` additionally loads
the embedding library after creating worker threads, exercises aligned and
cross-thread allocation/free, SolveSpace's heap API operations and ordinary C++
new/delete behavior. It checks the override mode by preloading the library and
requires both incompatible artifact controls to fail. It deliberately keeps
allocator TLS loaded until process exit. Run it with the two staged libraries,
their matching headers and selected native prefix/SDK/link-lock inputs listed by
`--help`. This covers those consumer API boundaries; full Mold/SolveSpace
applications, other hosts, target execution and live allocator unload are not
qualified by this diagnostic.
