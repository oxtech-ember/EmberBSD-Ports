# Common Node24 recipe

The canonical recipe is `lang/nodejs24` in the prepared pkgsrc tree.
The ordered `pkgsrc-nodejs24-current.patch` updates its source to
[Node.js 24.22.1 LTS](https://nodejs.org/en/blog/release/v24.22.1).
It uses the official `node-v24.22.1.tar.xz` release archive.
The official SHA256 is recorded in `sources.tsv`.
The recipe `distinfo` records BLAKE2s, SHA512 and archive size.

This is the 2026-10-21 security release.
Keep consumers on this common Node24 recipe.
The update retains all 25 pkgsrc portability patches and their checksums.
It retains the shared dependency configuration, supported platforms, package
file list and upstream `check` target. Compiler and target ABI selection stay
with the consumer.
The recipe requires shared Brotli 1.2.1 or newer and c-ares 1.34.9 or newer.
These constraints keep the shared dependencies at the security fixes used by
this release. A source update alone does not qualify those dependencies.

Build and test the normal package with the selected native Ports compiler.
Clang/LLVM is the default; a platform profile may explicitly select GCC for a
documented LLVM limitation. A configure failure must not select another compiler.
Check the installed `node --version` result, upstream tests, package contents
and complete native runtime closure. Cross packages must retain separate
build-host tools and target outputs. Do not execute a target Node on the host.
Source checksum and patch-context checks do not establish that acceptance.

The Blanc package controller requires exactly host Node.js 24.22.1.
Chromium keeps its separate upstream host-Node pin. Selecting this common
provider for Chromium requires an explicit source-owned executable route and
JavaScript compatibility checks. This recipe update does not change that route.

The ordered `pkgsrc-nodejs24-python315.patch` adds Python 3.15 to the existing
configure version check and updates Node's embedded GYP-next checked parser to
use `ast.Constant`. It accepts string constants only, preserving rejection of
other values, duplicate keys and executable expressions. The selected host
Python and its declared `py-packaging` dependency remain recipe inputs; no pip
installation or interpreter fallback is introduced.

Run the source regression with the selected Python 3.15 and patch executable:

```sh
"$HOST_PREFIX/bin/python3.15" -B -I -S \
  profiles/common-build-tools/tests/node-python315.py \
  --pkgsrc "$PREPARED_PKGSRC" \
  --distfile "$DISTDIR/node-v24.22.1.tar.xz" \
  --patch "$HOST_PREFIX/bin/nbpatch" --work "$NEW_WORK_DIRECTORY"
```

Check that the common source exporter applies the same patch with the selected
absolute Git and GNU patch paths used for the export:

```sh
"$HOST_PREFIX/bin/python3.15" -B -I -S \
  profiles/common-build-tools/tests/nodejs24-export.py \
  --git "$EXPORT_GIT" --patch "$EXPORT_GNU_PATCH" \
  --work "$NEW_EXPORT_TEST_DIRECTORY"
```

The regression verifies source and patch checksums, reproduces both unpatched
Python 3.15 failures, runs the real configure entry with `--help`, and generates
a GYP diagnostic backend with `--check`. Its negative cases preserve the version
boundary and parser refusals. It does not run the full shared-dependency Node
configure, compile Node, validate the Darwin tool route or execute target code.
The ordinary package build and runtime checks above remain necessary.

The explicit EmberBSD Darwin profile requires `NODE_GYP_XCODE_VERSION_PLIST`
(or the common caller variable `EMBERBSD_DARWIN_XCODE_VERSION_PLIST`) alongside
`OSX_SDK_PATH`. Setting either plist variable also selects this route in another
Darwin profile. An automatically discovered SDK alone does not enable it.
Supply the absolute path to the genuine
Xcode `Contents/version.plist` associated with the selected host ABI inputs.
For example, pass `NODE_GYP_XCODE_VERSION_PLIST="$XCODE_VERSION_PLIST"` to the
ordinary package invocation. This is metadata; it does not select Xcode build
tools. Source fetch/checksum does not require that file.

The `pkgsrc-nodejs24-darwin-metadata.patch` passes the selected SDK and plist to
both configure and make. GYP reads the actual SDK name/version and Xcode
version/build with `plistlib`, without `xcrun`, `xcodebuild`, `pkgutil` or
`softwareupdate` discovery. Missing metadata and a conflicting `SDKROOT` fail
instead of selecting another SDK. Compiler, linker and archive tool remain
separate native prefix inputs. Other hosts and the unselected upstream route
retain their existing behavior.

This selected route covers ordinary macOS Node executables and libraries.
Additional SDK metadata queries for iOS, XCTest or bundle packaging are not
implemented; they fail explicitly. Such consumers need their own declared
platform inputs before that scope can be enabled.

`tests/node-darwin-metadata.py` runs the common exporter and source regression,
checks the unselected recipe route, rejects legacy
metadata subprocesses and missing/mismatched inputs, and runs actual GYP make
generation plus a tiny C archive/C++20 executable with selected native Clang,
LLVM libtool and LLD. Its `--help` lists the explicit tools and ABI inputs.
That check does not establish a complete Node package or target runtime.

The ordered `pkgsrc-nodejs24-corefoundation.patch` makes Abseil's macOS
CoreFoundation dependency a GYP `link_settings.libraries` entry. GYP propagates
it through static libraries to the final link; LLVM's static archive tool no
longer receives `-framework`. Other platforms do not acquire the framework.
The Darwin regression also uses the real patched Abseil settings for two tiny
static archives and an executable that calls CoreFoundation. It checks final
link flags and execution, reproduces the old archive-tool refusal, and proves
that deleting the library or limiting it to direct dependents breaks the final
link. Unrelated archive/link flags remain intact. The non-mac check covers
metadata generation only. Full Node package/runtime acceptance is separate.

## V8 hash consistency

The ordered `pkgsrc-nodejs24-v8-hash.patch` backports
[V8 65ce14d8731e929584344a0d65d6efd2296fa797](https://github.com/v8/v8/commit/65ce14d8731e929584344a0d65d6efd2296fa797)
to the pinned V8 13.6 sources in Node 24.22.1nb6. The broad partial
specialization of `std::hash` could select a different hash for the same type
in different translation units. With the selected Darwin libc++ headers,
Inspector inserted session ID 1 into a set but could not find it when emitting
`Runtime.executionContextDestroyed`.

The backport removes that specialization and explicitly chooses `base::hash`
for both WebAssembly canonical group sets. Upstream's profiler change is not
applicable here: this branch's `line_ticks_` map has integer keys, while the
newer upstream map uses pairs. The standard integer hash is retained.
These headers affect Node/V8 broadly. Rebuild the ordinary Node package;
replacing only Inspector objects cannot establish a consistent program.

`tests/node-v8-hash.py --help` describes the source and compiler inputs for the
regression. It uses the real common exporter, verifies recipe patch checksums
and the complete source patch series, then links separate translation units.
The original V8 header must reproduce an inserted-but-unfindable integer;
the patched header must pass with the same native Clang/libc++ inputs.
Explicit V8 hashing for custom keys and pairs must continue to work.
This focused regression does not replace a complete Node build and its
Inspector, WebAssembly, profiler and normal JavaScript runtime tests.

## GC timeout test

The test-only `node-gc-net-timeout.patch` accepts a peer's `ECONNRESET` on
client sockets, matching the existing server-side allowance. For an aggregate
connection error, every child must also be `ECONNRESET`; unrelated errors still
fail. The original timeout callback, collection observer, counters and complete
collection condition remain unchanged. This does not alter the Node runtime or
installed package payload, so it does not require a package revision change.

Run the causal regression against the selected native Node 24.22.1:

```sh
"$HOST_PREFIX/bin/python3.15" -B -I -S \
  profiles/common-build-tools/tests/node-gc-net-timeout.py \
  --sdk-source "$SDK_SOURCE" --host-prefix "$HOST_PREFIX" \
  --archive "$DISTDIR/node-v24.22.1.tar.xz" --work "$NEW_WORK_DIRECTORY"
```

It extracts the checked upstream test and common helpers into its own directory.
A real peer `resetAndDestroy()` reproduces the unhandled client error before the
patch; the patched test must collect every client and still observe its original
timeout callback. Additional cases cover normal execution, aggregate resets,
rejection of other or mixed errors and a deliberately lost collection callback.
The checks use the installed native Node, without rebuilding or replacing it.
They do not establish the full upstream suite or target Node acceptance.
