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
