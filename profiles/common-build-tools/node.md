# Common Node provider

The prepared pkgsrc tree uses `lang/nodejs` with [Node.js 26.12.1](https://nodejs.org/en/blog/release/v26.12.1). The official archive SHA256 is recorded in `sources.tsv`; recipe `distinfo` records BLAKE2s, SHA512, size and portability patch checksums. `pkgsrc-nodejs-current.patch` updates the common upstream recipe and `node-gc-net-timeout.patch` adjusts only the upstream test. The version family removes replaced versioned recipes from the prepared catalog.

The source-owned `src/node_version.h` defines EmberBSD's unregistered native-addon module ABI revisions: 1162674177 for standalone Node and 1162674178 for Electron. These values identify separately built EmberBSD runtimes; they are not upstream registrations or compatibility claims for other distributions. Rebuild V8/Node C++ addons against the matching runtime headers and configuration, rather than using foreign prebuilt binaries. Node-API has its separate ABI contract and remains subject to its documented API and external-library limits. Advance the affected revision when its native-addon ABI changes. `tools/getmoduleversion.py` reads this header for standalone configuration; `--electron` selects the Electron value for its GN arguments, headers and config.

The common recipe selects shared dependencies, including Ada, Abseil, Highway, simdjson, simdutf, llhttp, nbytes, merve, uvwasi, LIEF and Temporal. The Node configure patch preserves `pkg-config` compile definitions and other compiler flags in GYP. The host and target use their selected Ports compilers and ABI inputs independently; a target Node must not be executed on the build host.

For native Darwin bootstrap, GYP build and install both use the selected SDK
shell link launcher for host and target links. The shared launcher variable
has priority over the legacy GCC bootstrap variable. If CMake link control is
selected but neither shell form exists, build and install request an updated
native configuration; source fetch and checksums remain available.

The Darwin profile passes `OSX_SDK_PATH` and `NODE_GYP_XCODE_VERSION_PLIST` (or the common caller variable `EMBERBSD_DARWIN_XCODE_VERSION_PLIST`) to GYP. The plist supplies metadata, not a compiler selection. Missing or conflicting selected metadata fails without searching for other tools. Additional iOS, XCTest and bundle metadata queries are outside this route.

The source regression verifies the release checksum, applies the complete pkgsrc patch series with zero fuzz and checks the Python/GYP, Darwin and V8 contracts:

```sh
"$HOST_PREFIX/bin/python3.15" -B -I -S profiles/common-build-tools/tests/node26-source.py \
  --archive "$DISTDIR/node-v26.12.1.tar.xz" --recipe "$PREPARED_PKGSRC/lang/nodejs" \
  --patch "$HOST_PREFIX/bin/gpatch" --work "$NEW_WORK_DIRECTORY"
```

`tests/node26-torque-producer.py` takes the prepared Node source, selected host
Python and selected GNU make. It generates and builds a small fixture in native
and cross toolset modes, checking that each shared Torque output has one writer.
`tests/node26-gyp-host-link.py` takes the prepared Node source and host Python;
it checks generated Darwin native, Darwin-to-NetBSD and simulated Linux-to-NetBSD
link commands against the original GYP templates. Actual host and target builds
remain separate checks.

`tests/node26-export.py --help` exercises the actual pkgsrc exporter and compares its resulting recipe to the selected expected recipe. `tests/node26-pkgconfig-flags.py --help` describes the selected native inputs for the generated GYP rule regression. `tests/node-darwin-metadata.py --help` covers selected metadata and the Darwin CoreFoundation dependency through static archives, including negative and non-macOS generation cases. These checks do not replace a full package build, installed runtime and target tests.

The GC regression retains the timeout callback and complete collection condition while permitting peer `ECONNRESET`, including aggregate errors only when every child matches. Run `tests/node-gc-net-timeout.py --help` with the installed selected host Node and the release archive. The Electron 44 to 45 transition is in progress: its target runtime and host tools are being moved to this common Node26 source and provider; the existing Electron 44 source pin remains until that transition is complete.

On macOS, Node’s `--build-sea` produces an unsigned executable. The host OS signing service must ad-hoc sign it (`codesign --sign -`) before execution, as documented in [Node SEA instructions](https://nodejs.org/api/single-executable-applications.html); the signer does not select the compiler or linker.

The Node GN integration accepts an optional `node_embedder_cppheap_pointer_tag`
selected by the embedder. With no selection, standalone Node retains V8's
default tag. Sandboxed embedders must select a non-overlapping tag and check
their own wrapper ranges. The internal embedder ESM callbacks retain Node's
per-realm handlers even when the embedder owns isolate callbacks. The native
regression `tests/node-embedder-runtime.py` requires the selected Node and
cctest binaries and their build work, and exercises both default and
embedder-owned ESM callbacks and concurrent worker teardown.
