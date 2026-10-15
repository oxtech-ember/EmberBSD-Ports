# GObject Introspection for EmberBSD cross builds

The graphics profile supplies `gobject-introspection-1.86.0nb5`, built on
macOS for EmberBSD/AArch64 with GCC16, Python 3.14.8 and GLib 2.90.1.
Its complete selected pkgsrc payload is preserved: library, tools, Python
scanner extension, GIRepository GIR/typelib, headers and test sources.
The GLib-family GIR files belong to the separate `glib2-introspection` package.
Its current 2.90.1nb1 cross package and target metadata checks are described below.

The original [GNOME archive](https://download.gnome.org/sources/gobject-introspection/1.86/gobject-introspection-1.86.0.tar.xz)
has SHA256 `920d1a3fcedeadc32acff95c2e203b319039dd4b4a08dd1a2dfd283d19c0b9ae`.
The [recipe](../recipes/devel/gobject-introspection/Makefile) preserves the
pinned pkgsrc import and attribution. EmberBSD's patches are not submitted
upstream. They separate native generators from target libraries and retain
installed test source data that upstream omits during cross builds.

## Build and execution roles

Use the [common graphics cross profile](profile.md) with an
[EmberBSD sysroot](../../common-build-tools/cross/sysroot.md). A matching native
GI 1.86.0 is a declared tool dependency. Meson runs native Python and native
`g-ir-scanner`/`g-ir-compiler`; pkgsrc's target sysconfig remains responsible
for Python headers, extension ABI and installed `/usr/pkg/bin/python3.15`
shebangs. A Meson native machine file keeps its C compiler on macOS.
Cross `readelf` obtains ELF SONAMEs instead of invoking a host loader.

GType discovery executes small cross-built queries on an authorized EmberBSD
AArch64 VM or board over SSH. The supplied runner resolves target ELF libraries
from the build tree and sysroot, rejects incompatible/conflicting providers,
and transfers copies into a newly allocated private temporary directory.
It checks hashes before and after execution, limits each query to 60 seconds,
disables core dumps and removes the allocated directory. It installs no package
and changes no base system. This is actual target execution, not a host GType
substitute. A user with temporary-directory execution permission is sufficient.

Create an existing private cache outside the sysroot and a private JSON file:

```json
{
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
tool. Add these private MAKECONF settings:

```make
EMBERBSD_GI_RUBY=/absolute/native/ruby
EMBERBSD_GI_QUERY_CONFIG=/absolute/private/query.json
```

Then use ordinary host `bmake ... package install` for the exported
`devel/gobject-introspection` recipe. `install` populates only the private
cross sysroot. Do not set `gi_cross_pkgconfig_sysroot_path`: pkgsrc's pkgconf
already roots target include/library paths, so a second prefix duplicates it.
Keep diagnostic query logs and manifests; successful runs remove transferred
copies and archives. Failed cleanup is an error and reports the exact directory.
XML is published to the scanner only after successful cleanup and unchanged
local source hashes. The scanner still performs its ordinary XML parsing.

## Compiled configure probes

The same runner accepts `--execute BINARY` for no-argument configure probes.
It preserves target stdout, stderr and exit status independently, including
negative feature results. The same ELF-provider checks, 60-second limit,
hash receipts and cleanup apply. This mode does not accept arbitrary target
commands or additional arguments. TDB's Waf cross executor uses it while all
compilation stays on the development host. The target writes an execution
receipt only after its post-run manifest check. The runner verifies that receipt
against the SSH status before accepting a negative feature result.

An enclosing configure step can set `EMBERBSD_GI_FAILURE_MARKER` to an absolute
file inside the configured build root. Infrastructure or cleanup failures leave
that marker; verified target exits, including nonzero feature results, do not.
TDB clears it before configure and rejects configuration if it appears, so a
lost connection cannot silently disable a required feature. Keep this hook
when integrating the executor into another build system.

An optional `host_key_alias` JSON field selects an already verified SSH host
key when the destination uses a numeric address. Strict key checking remains
mandatory. Keep addresses and this machine-specific configuration private.

`tests/target-execute.rb CC SYSROOT QUERY_CONFIG NEW_WORK` compiles two target
probes and verifies their real stdout/stderr, exit codes 0 and 7, receipts and
cleanup. `NEW_WORK` must be inside the configured build root. The existing
`gi-query-contract.rb` also tests this mode with controlled transport failures
and rejects invalid host-key aliases and unsupported probe arguments.

## Acceptance and limits

The normal package passes PLIST, interpreter, RPATH, PIE/RELRO, shared-library
and work-reference checks. All 180 payload files/links match the installed
package; its 186 recorded entries include six metadata files. Actual target
queries produce GLib, GModule, GObject, Gio and GIRepository metadata.
On CM5, unchanged upstream `gthash-test` passes its build/retrieve case;
`cmph-bdz-test` passes ordinary and packed search. These use the selected
current GLib and EmberBSD libc in temporary directories.

Accepted package SHA256:
`24c970a890a14083bfdae22426515a12023aea7901dc59fc7f78699fde0cf83f`.
The installed regular-file manifest has SHA256
`e7dedd45cc6eb3d6cc76cc42b6b0a5d33b55b231cf18c54194e6930c83f074c1`.

`tests/gi-query-contract.rb CROSS_TOOLS NEW_WORK` builds real AArch64 ELF
fixtures and checks provider aliases, SONAME inspection and seven refusals
before SSH. Injected transfer, query, readback, invalid-output, cleanup and
input-change failures prove that failed runs publish no XML. A successful
transport fixture publishes it only at the end. These transport fixtures are
separate from the actual CM5 execution. `tests/export.sh NEW_WORK` checks all
six profile compositions and the required recipe, helper and patch inputs.
The final export passed all six compositions and 75 preflight refusals.

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
Seven real GType queries ran on EmberBSD/AArch64 CM5 in temporary directories.
All query exits and cleanup statuses were zero. Package SHA256:
`9c577a6a88dddc170ba98e76fa8cbe175494590c87d94ed6a5afd18df3ca0b0a`.

The selection regression extracts the actual patched Meson code. It checks
default cross refusal, explicit cross generators, unchanged native behavior,
and all 14 generated package rules. The target consumer verifies that installed
typelib bytes match the archive, then embeds those exact bytes in an ELF fixture.
Four CM5 cycles load all seven namespaces and invoke `g_get_monotonic_time`
through introspection/libffi with a checked return value. Malformed metadata
and an incorrect argument count are rejected. This checks target metadata
loading and invocation, not the complete GLib or installed scanner test suites.

```sh
ruby tests/glib-introspection-cross.rb /path/to/built/glib-2.90.1 \
  /path/to/native-host-prefix /path/to/cross-tools/bin/aarch64--netbsd-gcc \
  /path/to/new-selection-check
ruby tests/prepare-glib-typelib.rb /path/to/cross-tools /path/to/sysroot \
  /path/to/glib2-introspection-2.90.1nb1.tgz /path/to/work/new-typelib-check
EMBERBSD_GI_QUERY_CONFIG=/path/to/private/query.json ruby \
  recipes/devel/gobject-introspection/files/target-query.rb \
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
