# GObject Introspection for EmberBSD cross builds

The current `gobject-introspection-1.86.0nb6` recipe releases the temporary
typelib hash keys and the upstream hash test's packed buffer. This two-line
ownership repair preserves the ABI, hash format and complete build graph.
Its normal native GCC16 package verifies all 180 installed entries. With the
current setuptools test mock, all 64 upstream Meson invocations pass.
The Linux GCC16 AArch64 package also verifies all 180 installed SDK entries.
Five real GType queries pass in an EmberBSD AArch64 E34 VM.
Its complete selected pkgsrc payload is preserved: library, tools, Python
scanner extension, GIRepository GIR/typelib, headers and test sources.
The GLib-family GIR files belong to the separate `glib2-introspection` package.
Its current 2.90.1nb1 cross package and target metadata checks are described below.

The original [GNOME archive](https://download.gnome.org/sources/gobject-introspection/1.86/gobject-introspection-1.86.0.tar.xz)
has SHA256 `920d1a3fcedeadc32acff95c2e203b319039dd4b4a08dd1a2dfd283d19c0b9ae`.
The [recipe](../../../pkgsrc/devel/gobject-introspection/Makefile) preserves the
pinned pkgsrc import and attribution. EmberBSD's patches are not submitted
upstream. They separate native generators from target libraries and retain
installed test source data that upstream omits during cross builds.

## Typelib hash memory ownership

`_gi_typelib_hash_builder_prepare()` duplicates keys into a NULL-terminated
vector. Bundled CMPH borrows that vector; its adapter destructor frees only
the adapter and wrapper. After both CMPH destructors, `g_strfreev()` releases
the keys and vector on the existing success/failure cleanup path. The finished
BDZ hash owns its hash state and lookup arrays independently. The upstream test now
also frees its packed buffer after all four lookup assertions.

The [causal check](../tests/gi-gthash-memory.rb) compares the original archive
with the two configured modules, applies the reviewed patch, and builds both
variants using the actual native pkgsrc compiler/link commands. It reuses the
unchanged real CMPH archive and records its members' hashes. Run it against
a completed **unpatched** native revision-5 build:

```sh
ruby ../tests/gi-gthash-memory.rb /absolute/gobject-introspection-1.86.0/output \
    /absolute/gobject-introspection-1.86.0.tar.xz \
    /absolute/gcc16 /absolute/gcc16-ar /absolute/new-results
```

GCC 16.2.0 and Valgrind 3.24.0 reproduce 80 bytes definitely lost and
55 bytes indirectly lost in the original test. Both become zero after the
repair; all four lookup assertions still pass. Both variants retain exactly
23,424 reachable bytes in eleven GLib initialization/test contexts. Strict
`--errors-for-leak-kinds=all` therefore exits 99 in both runs, with fourteen
versus eleven error contexts. No suppression is used, and this is not an
all-leak-clean result. The helper verifies that the reported contexts are
leak records and rejects invalid-memory diagnostics or changed inputs.

Both complete modules, before and after, pass GCC16 `-fanalyzer` and Clang
Static Analyzer 19.1.7 with empty diagnostics. Cppcheck 2.22 reads the actual
compiler database but reports the same 89 diagnostics in each variant,
including five parser failures in GLib headers. Supplying GCC's actual
preprocessed translation units still encounters unsupported `_Pragma`/typedef
syntax in GLib cleanup declarations. This Cppcheck coverage is incomplete;
the raw inherited findings remain recorded without suppressions.

All eleven recipe patches pass pkgsrc checksums and apply without fuzz to the
pinned archive. Actual native/cross metadata selects revision 6. The exporter
rejects a missing, altered or jointly omitted patch/checksum before export.
These source checks do not imply target execution or a complete GI/GLib
memory audit.

## Native package and upstream tests

The normal Linux GCC 16.2.0 package `gobject-introspection-1.86.0nb6` passes
pkgsrc package checks and verifies all 180 installed files and links. Its
archive SHA256 is
`8784c50ab507d06128b213ef6443ba19e54ec8335a11a6593b31076e65b8c98d`.
The test-only patch below changes no installed file; all 180 entries have
identical bytes, modes and link targets before and after the test run.

Run the normal pkgsrc test phase in the completed native recipe directory:

```sh
bmake do-test
```

Use the same native `MAKECONF` and work-directory settings as the package.
This invokes Ninja's test target with pkgsrc's compiler and `pkg-config`
environment. Ninja first builds the upstream `meson-test-prereq` graph,
including the test GIR and typelib files. Direct `meson test --no-rebuild`
does not build those prerequisites. A scanner test also needs the package's
GLib `pkg-config` provider.

Current setuptools executes compiler commands through `Compiler.call`.
The upstream argument tests previously mocked only `Compiler.spawn`, so
their dummy command names escaped the mock. The
[test patch](../../../pkgsrc/devel/gobject-introspection/patches/patch-tests_scanner_test_ccompiler.py)
selects `call` when present and retains `spawn` for older distutils interfaces.
It preserves every argument assertion and all upstream skips and expected
failures. It changes only the uninstalled `tests/scanner/test_ccompiler.py`.

The [causal check](../tests/gi-compiler-mock.rb) runs both archive-derived
variants against the configured scanner and the actual native interpreter:

```sh
ruby ../tests/gi-compiler-mock.rb /absolute/native/output \
    /absolute/gobject-introspection-1.86.0.tar.xz \
    /absolute/native/python3.15 /absolute/new-results
```

All 19 cases remain present. Thirteen original mock errors become zero;
the same two skipped cases and two expected failures remain. The full normal
pkgsrc test phase then passes all 64 Meson invocations with zero failures.
The current native package uses Python 3.15 and GLib 2.90.1. This does not
establish target execution, an older-distutils runtime result or a complete
memory-clean GI/GLib suite. The hash-test memory limits above still apply.

## Build and execution roles

Use the [common graphics cross profile](profile.md) with an
[EmberBSD sysroot](../../common-build-tools/cross/sysroot.md). A matching native
GI 1.86.0 is a declared tool dependency. Meson runs native Python and native
`g-ir-scanner`/`g-ir-compiler`; pkgsrc's target sysconfig remains responsible
for Python headers, extension ABI and matching installed target shebangs.
The current common interpreter installs `/usr/pkg/bin/python3.15` shebangs.
The accepted Linux AArch64 package uses Python 3.15 and GLib 2.90.1.
A Meson native machine file keeps the build compiler on the development host.
Cross `readelf` obtains ELF SONAMEs instead of invoking a host loader.

Cross builds use installed native Flex from `${TOOLBASE}/bin/flex` through
the normal pkgsrc version check and an explicit tool dependency. GI supplies
its own `yywrap`; its generated lexer does not require target `libfl`.
Missing or unsuitable native Flex fails before dependency recursion. Native
package routing is unchanged.

Run this bounded check with an exported tree, the existing cross MAKECONF
and a new absolute work directory. Its prerequisites must already be installed:

```sh
ruby profiles/common-graphics/tests/gi-native-flex.rb \
  /absolute/pkgsrc /absolute/cross.mk.conf /absolute/new-flex-check
```

The check compares real baseline/fixed and native metadata, rejects three
invalid providers, and runs ordinary private `patch` and `wrapper` phases.
It then runs native Flex/Bison on the complete upstream lexer/parser and
compiles the lexer through the target GCC16 wrapper. The AArch64 run passed
with Flex 2.6.4 and no unresolved `yywrap`. This is a source/tool-routing
check; it does not build or install the complete GI package or execute a
target binary.

GType discovery executes small cross-built queries on an authorized EmberBSD
VM or board of the selected architecture over SSH. The runner resolves ELF libraries
from the build tree and sysroot, rejects incompatible/conflicting providers,
and transfers copies into a newly allocated private temporary directory.
It checks hashes before and after execution, limits each query to 60 seconds,
disables core dumps and removes the allocated directory. It installs no package
and changes no base system. This is actual target execution, not a host GType
substitute. A user with temporary-directory execution permission is sufficient.

Create an existing private cache outside the sysroot and a private JSON file:

```json
{
  "target": "aarch64",
  "build_root": "/absolute/work",
  "sysroot": "/absolute/target-sysroot",
  "cache": "/absolute/query-cache",
  "readelf": "/absolute/cross-tools/bin/aarch64--netbsd-readelf",
  "ssh": "builder@ember-target.local"
}
```

The target must already be accessible with noninteractive SSH and a verified
host key. It needs `tar`, `sha256`, `timeout` and its compatible base loader.
The JSON must agree with the recipe's work directory, sysroot and inspection
tool. `target` accepts only `aarch64` and `amd64`. An omitted field retains
the original AArch64 contract. It never selects the build-host architecture.
For amd64, set `target` to `amd64` and select the matching
`x86_64--netbsd-readelf`. The common cross profile maps that target to pkgsrc
`MACHINE_ARCH=x86_64` and GNU `x86_64--netbsd` metadata. Unknown or mixed
target metadata fails. The same configuration serves `glib2-introspection`
and the other consumers of GI's shared cross fragment.

The optional `transfer_timeout_seconds` field sets the input archive transfer
deadline. It accepts an integer from 1 to 3600. The default is 180 seconds.
Select a bounded value that allows the archive to cross the selected link.
This field does not extend allocation, execution, XML readback or cleanup.
The target program still has its separate 60-second execution deadline.

Add these private MAKECONF settings:

```make
EMBERBSD_CROSS_BUILD_PYTHON=/absolute/native/python3.15
EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK
EMBERBSD_GI_QUERY_CONFIG=/absolute/private/query.json
```

The GI launcher and its host contracts use Python with the standard library.
Production helper commands pass `-E -S` to the selected host Python.
They ignore target Python site settings and use the explicitly selected SDK.
The target library environment and command arguments remain unchanged.
The GdkPixbuf loader/MIME runner uses the same selected Python. It also uses
SDK host API 1 through the explicit `EMBERBSD_SDK_SOURCE` setting.
`EMBERBSD_GI_PYTHON` remains an alias for the common Python provider. If both
selectors are set, they must name the same executable.

Then use ordinary host `bmake ... package install` for the exported
`devel/gobject-introspection` recipe. `install` populates only the private
cross sysroot. Do not set `gi_cross_pkgconfig_sysroot_path`: pkgsrc's pkgconf
already roots target include/library paths, so a second prefix duplicates it.
Keep diagnostic query logs and manifests; successful runs remove transferred
copies and archives. Failed cleanup is an error and reports the exact directory.
XML is published to the scanner only after successful cleanup and unchanged
local source hashes. The scanner still performs its ordinary XML parsing.

The optional `executable_layout` JSON field accepts only `flat` and
`prefix-bin`. The default `flat` layout runs the verified ELF as `ROOT/query`.
`prefix-bin` runs the same bytes as `ROOT/bin/query`. Both layouts keep
libraries in `ROOT/lib`. The private `ROOT` remains the only transfer and
cleanup directory. Use `prefix-bin` for a program that derives its prefix
from its executable location. No arbitrary executable path is accepted.
The layout does not add library aliases or change resource declarations,
arguments, manifests, loader settings or execution checks.

A program can discover an SDK DSO by filename without linking it. Declare
that file with `library_inputs`, for example
`[{"name": "libLLVM-23.so", "sha256": "<exact lowercase SHA256>"}]`.
The optional list accepts at most 32 unique basenames. It accepts no paths.
Each name must select one direct SDK symlink to a regular file in the same
canonical SDK library directory. Absolute links, link chains and ambiguous
sources fail. The provider must be target ELF64 ET_DYN with a safe SONAME
and the declared SHA256. The runner adds it to the ordinary recursive ELF
closure. It records source/link identities in `library-inputs.json`.
It creates only a checked alias to the transferred SONAME below `ROOT/lib`.
Both manifest passes check the bytes. Separate link checks reject replacement
of the alias. Source identity checks run before transfer and after execution.
An omitted or empty list retains the ordinary closure. This interface does not
install a library or permit arbitrary executable or resource inputs.

## Compiled configure probes

The same runner accepts `--execute BINARY [ARG...]` for configure probes.
It preserves target stdout, stderr and exit status independently, including
negative feature results. The same ELF-provider checks, 60-second limit,
hash receipts and cleanup apply. Literal probe arguments pass unchanged.
The target writes an execution receipt only after its post-run manifest check.
The runner verifies that receipt against the SSH status before accepting a
negative feature result. TDB's Waf cross executor uses this mode while all
compilation stays on the development host.

Execute callers can declare read-only resource files with two optional JSON
fields. Omit both fields for the ordinary GI contract. For example:

```json
{
  "execute_inputs": [
    {
      "source": "/absolute/sysroot/usr/pkg/share/opencascade/resources/XSTEPResource/STEP",
      "path": "data/occt/XSTEPResource/STEP",
      "sha256": "<exact lowercase SHA256>"
    }
  ],
  "execute_environment": {
    "CSF_LANGUAGE": {"literal": "us"},
    "CSF_STEPDefaults": {"stage_path": "data/occt/XSTEPResource"}
  }
}
```

Each source must be a canonical regular file inside the selected build root or
sysroot. Symlink aliases and escaped ancestors fail. The runner checks the
source identity and SHA256 before transfer and after execution. Each bounded
copy reads at most the snapshot size plus one byte. A file can contain at most
16 MiB; the complete list can contain at most 64 MiB and 1024 files. The runner
records the source identity, digest and declared environment in
`data-inputs.json`. Both target manifest passes cover the transferred data.
Destinations must be unique safe paths below `data/`. A file destination cannot
be a parent of another file. The query, libraries, type list and manifests keep
their existing namespaces.

The environment accepts at most 32 names that start with `CSF_`. Only
`CSF_LANGUAGE` accepts a bounded language literal. Other values must select a
file or directory in the declared data tree with `stage_path`. The runner
resolves that path below its private target directory. Callers cannot replace
`PATH`, loader controls or controller settings. These fields require
`--execute`; they do not change the GI invocation. Data files receive the same
transfer, status and cleanup checks as the ELF closure. Shared root identity
checks compare device, inode and mode; unrelated child creation is allowed.
Per-file identity checks retain size and timestamps.

Waf's `CHECK_COMMAND` also runs `getconf LFS_CFLAGS` on the target.
For this bare command name, execute mode runs the sysroot's `/usr/bin/getconf`.
It must be a regular file, not a symbolic link. Its NEEDED providers resolve
by the normal provider rules. The query never runs a program from the target's
`PATH`. Other bare command names fail before SSH. They leave the failure
marker when the caller sets one. On the amd64 target, TDB configuration
completes, and `getconf` reports the variable as unknown, as on a native host.

An enclosing configure step can set `EMBERBSD_GI_FAILURE_MARKER` to an absolute
file inside the configured build root. Infrastructure or cleanup failures leave
that marker; verified target exits, including nonzero feature results, do not.
TDB clears it before configure and rejects configuration if it appears, so a
lost connection cannot silently disable a required feature. Keep this hook
when integrating the executor into another build system.

An optional `host_key_alias` JSON field selects an already verified SSH host
key when the destination uses a numeric address. Strict key checking remains
mandatory. Keep addresses and this machine-specific configuration private.

`python3.15 tests/target-execute.py --sdk-source /absolute/EmberBSD-SDK CC SYSROOT QUERY_CONFIG NEW_WORK` compiles two target
probes and verifies their real stdout/stderr, exit codes 0 and 7, receipts and
cleanup. `NEW_WORK` must be inside the configured build root. The existing
`gi-query-contract.py` also tests this mode with controlled transport failures
and rejects invalid host-key aliases and extra arguments outside execute mode.
It also checks the sysroot `getconf` selection, a symbolic link in its place,
and other bare commands. Each rejected execute command leaves the
failure marker. Execute-data controls run the actual manifest shell with a
host-only `timeout` adapter. They verify resource exports, staged hash checks,
source byte/metadata changes and root replacement. No target ELF runs in those
controlled transport checks. Actual OCCT runtime acceptance is separate.

## Acceptance and limits

The normal package passes PLIST, interpreter, RPATH, PIE/RELRO, shared-library
and work-reference checks. All 180 payload files/links match the installed
package. Actual target
queries produce GLib, GModule, GObject, Gio and GIRepository metadata.
All five E34 VM query exits, provider checks and temporary-directory cleanups pass.
The revision-6 AArch64 SDK package has SHA256
`ad88282d203b7da8e08a786609af3408720a88c05aca3772b6fe527fe223661e`.
This does not execute the target scanner or complete target upstream test suite.

Separate CM5 checks of the earlier package run unchanged upstream
`gthash-test` through its build/retrieve case;
`cmph-bdz-test` passes ordinary and packed search. These use the selected
GLib and EmberBSD libc in temporary directories.

`python3.15 tests/gi-query-contract.py --sdk-source /absolute/EmberBSD-SDK [--target aarch64|amd64] CROSS_TOOLS NEW_WORK` builds
real ELF fixtures with the selected GCC cross compiler. AArch64 is the default.
The amd64 host contract uses real cross-linked x86_64 ELF and native `bmake`
evaluation of both target metadata sets. It rejects a foreign query or provider,
ELF32, big-endian data, a mismatched JSON target and mixed GNU metadata before
SSH. The production remote identity shell is also checked with explicit host
fixtures. No transport fixture counts as VM execution or target GI acceptance.

Both target paths require ELF64 little-endian files of the selected machine
for every query and recursive provider. Before temporary-directory allocation,
the actual SSH command requires `uname -s=NetBSD` and `uname -p=aarch64` or
`uname -p=x86_64`, as selected. Target query execution, manifests, time limits,
status receipts and cleanup remain mandatory. The amd64 GI/GLib target query
and package acceptance remain pending; the AArch64 receipts above are unchanged.

The contract also checks provider aliases, SONAME inspection and input refusals
before SSH. Injected transfer, query, readback, invalid-output, cleanup and
input-change failures prove that failed runs publish no XML. A successful
transport fixture publishes it only at the end. These transport fixtures are
separate from the actual target execution. `scripts/tests/export-composition.sh
NEW_WORK` exports the tree and compares each exported recipe with its source.

## GLib 2.90.1 metadata package

`glib2-introspection-2.90.1nb1` supplies all seven GIR/typelib pairs: GLib,
GLibUnix, GObject, GModule, Gio, GioUnix and GIRepository 3.0. Build its normal
`package install` targets with the same cross configuration and a query JSON
whose `build_root` contains its new work directory. Installation populates the
private cross sysroot; it does not install anything on the query target.

The recipe reuses GI's native machine file, configuration validation, ELF
inspection and target-query runner. Two GLib patches permit this explicit
cross path and select the matching native `gi-compile-repository` 2.90.1.
The ordinary upstream cross refusal and native compiler selection remain.
The recipe also carries the same target libc printf/strlcpy properties as
`glib2`, and fixes its misspelled GIR build-target variable. Upstream Python
remains a generator dependency; these changes add no project Python helper.

Normal packaging and cross-sysroot installation pass with all 14 payload files.
Seven real GType queries ran in the EmberBSD/AArch64 E34 VM in temporary directories.
All query exits and cleanup statuses were zero. Package SHA256:
`ffe31d4972de18289f23d9b0c62fc8ecccfcdcb20366b7ea7e3b89243c6c9265`.

The selection regression extracts the actual patched Meson code. It checks
default cross refusal, explicit cross generators, unchanged native behavior,
and all 14 generated package rules. The target consumer verifies that installed
typelib bytes match the archive, then embeds those exact bytes in an ELF fixture.
Four E34 VM cycles load all seven namespaces and invoke `g_get_monotonic_time`
through introspection/libffi with a checked return value. Malformed metadata
and an incorrect argument count are rejected. This checks target metadata
loading and invocation, not the complete GLib or installed scanner test suites.
The same bounded load/invoke contract also has separate CM5 acceptance.

```sh
ruby tests/glib-introspection-cross.rb /path/to/built/glib-2.90.1 \
  /path/to/native-host-prefix /path/to/cross-tools/bin/aarch64--netbsd-gcc \
  /path/to/new-selection-check
ruby tests/prepare-glib-typelib.rb /path/to/cross-tools /path/to/sysroot \
  /path/to/glib2-introspection-2.90.1nb1.tgz /path/to/work/new-typelib-check
EMBERBSD_SDK_SOURCE=/path/to/EmberBSD-SDK \
EMBERBSD_GI_QUERY_CONFIG=/path/to/private/query.json /path/to/native/python3.15 \
  ../../pkgsrc/devel/gobject-introspection/files/target-query.py \
  /path/to/work/new-typelib-check/glib-typelib
```

Run these commands from `profiles/common-graphics`. The consumer work directory
must be inside the JSON's `build_root`; the existing runner enforces that bound.
The exporter has two additional missing-patch refusal controls for this change.

The installed target Python scanner and its complete upstream suite have not
yet been accepted on a board. Full current librsvg, its CLI/pixbuf integration,
and a complete Wayland compositor session remain separate work. This package
does not establish hardware GPU or NPU execution.

## Verified local provider reuse

The query launcher now compares installed sysroot providers with their exact
source SHA256 on the target. Matching files are copied into the private query
directory and checked again after copying. Different or missing installed files
are uploaded normally; in-tree libraries always travel with the query. The
complete manifest is still verified before and after execution. No installed
library is modified and no persistent target cache is introduced.

The launcher rejects unknown or duplicate reuse responses. Copy corruption,
query failure, invalid XML, cleanup failure and changed host inputs all prevent
publication. Readback now retains its exit status, size and diagnostic stream;
a bounded rejected XML payload stays in the local diagnostic directory.

The real-ELF contract adds three reuse transport failures and executes the
production shell body for matching, changed, missing and copy-corrupted files.
The existing pre-SSH, alias, SONAME, transport and publication checks still pass.
On CM5 on 2026-10-12, actual Pango GType queries reused 34 byte-identical
libraries and transferred approximately 0.9 MiB per query. Complete manifest
checks, target execution and temporary-directory cleanup passed. This is a
build-time GType result, not acceptance of an installed Pango application.

The [text and GTK consumer receipt](desktop-introspection.md) records full HarfBuzz, Pango, AT-SPI and GTK packages with real CM5 queries. Their graphical sessions and full upstream suites remain separate.
