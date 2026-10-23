# GdkPixbuf packages for EmberBSD cross builds

The graphics profile supplies recipes for `gdk-pixbuf2-2.44.8nb3` and
`shared-mime-info-2.5.1`. The selected payload loads raster formats and exposes
GdkPixbuf through GObject Introspection. The current packages cross-build on
macOS with GCC16 for EmberBSD/AArch64 and pass ordinary package/install checks.
EmberBSD Ports owns the recipes, target-query adaptation and acceptance tests.

The selected upstream releases were checked on 2026-10-09:

| Source | SHA256 |
| --- | --- |
| [GdkPixbuf 2.44.8](https://download.gnome.org/sources/gdk-pixbuf/2.44/gdk-pixbuf-2.44.8.tar.xz) | `919f529512961a12e81cd4b4b466a48c3933469e7f9a310c6513cd4fb252ba3c` |
| [shared-mime-info 2.5.1](https://gitlab.freedesktop.org/xdg/shared-mime-info/-/archive/2.5.1/shared-mime-info-2.5.1.tar.bz2) | `b75b420da9b0be9a3d99b1bee6ed87957b56ab54583ac1a97fbd0dc98ddddb25` |

GNOME's [release directory](https://download.gnome.org/sources/gdk-pixbuf/2.44/)
identifies 2.44.8 as current. The
[shared-mime-info tag list](https://cgit.freedesktop.org/xdg/shared-mime-info/)
identifies 2.5.1. The imported recipes preserve pkgsrc attribution and existing
patches. Four EmberBSD GdkPixbuf patches are AI-assisted and have not been
submitted upstream. The MIME update adds the upstream Kabyle translation to
the package list and retains the pkgsrc path adaptation.

## Build and execution roles

Use the [graphics cross profile](profile.md) and accepted
[GI and GLib metadata packages](introspection.md). GdkPixbuf keeps its ordinary
selected payload: shared library, headers, utilities, thumbnailer, man pages,
translations, eleven dynamic loaders and built-in PNG/JPEG loaders.
Introspection remains enabled by default for cross builds. Both GdkPixbuf and
GdkPixdata GIR/typelib pairs are installed. The normal pkgsrc options remain:
`others=enabled`, `glycin=disabled`, tests off and documentation off.

Native GI 1.86 generates the GIR/typelib files using target GLib 2.90.1
includes and real target GType queries. The separate `glib2-introspection`
dependency provides target GIR files; it is not a native tool dependency.
Native Python runs the existing upstream thumbnail metadata generator.
Native GLib utilities remain build tools. No target executable runs on macOS.

The opt-in Meson cross properties select these native generators and preserve
the thumbnailer during cross builds. Unselected cross and native Meson paths
keep their generator selection. The existing upstream Python script now also
preserves a printer's failure status when it has emitted output.
The project-owned target runner uses native Python 3.15 and SDK host API 1.
Select an absolute SDK source with `EMBERBSD_SDK_SOURCE`. The cross recipe
checks it with the runner before configuration. Missing inputs, relative paths
and a foreign SDK API fail before any SSH request. Revision 3 records this host
recipe contract. The intended target payload and ABI stay unchanged.

The scoped [target tool runner](../../../pkgsrc/graphics/gdk-pixbuf2/files/target-tools.py)
executes the target loader and MIME queries with the target modules. It checks
ELF architecture and provider roots, resolves the runtime closure, verifies
hashes before and after each query and removes its private remote directory.
It publishes output only after successful execution, cleanup and unchanged
local inputs. Each query is limited to 60 seconds. The target receives no
package or base-system installation. Strict SDK JSON parsing rejects duplicate
metadata keys. The runner retains the optional pinned `host_key_alias`.
The Python host migration passes the scoped guards on Darwin. The revision-3
build also completes real target loader, MIME and GIR/typelib generation.

Set up the private query JSON and MAKECONF as in the GI instructions. For a
GCC16 runtime closure, select its provider consistently in the JSON:

```json
"library_dirs": ["/absolute/target-sysroot/usr/pkg/gcc16/lib"]
```

This field belongs inside the existing JSON object. The runner rejects
conflicting providers of the same SONAME; it does not replace target libraries
with host libraries. Keep build products and the private query cache outside
the sysroot. Use ordinary package targets from the exported pkgsrc tree:

```sh
bmake -C /path/to/pkgsrc/graphics/gdk-pixbuf2 \
  MAKECONF=/path/to/private/mk.conf package install
```

Normal dependency traversal builds the selected shared-mime-info package and
any missing build tools. Accepted native compilers, GLib and GI can be reused.
The cross install targets populate only the private sysroot. Retain the
[sysroot provenance record](../../common-build-tools/cross/sysroot.md): the
accepted libc repair and this bounded package check do not establish a
complete verified base release or SDK.

## Acceptance

The revision-3 package/install checks pass, including PLIST, interpreters,
permissions, PIE, RELRO, runtime search paths and work-directory references.
All 147 GdkPixbuf payload files/links and 84 shared-mime-info payload
files/links match the installed packages. Accepted package SHA256 values:

| Package | SHA256 |
| --- | --- |
| `gdk-pixbuf2-2.44.8nb3.tgz` | `54263763b6bea137c40361d144e9b69d650c1bdf667521acc68c0e356ce18277` |
| `shared-mime-info-2.5.1.tgz` | `0cf32ca0e3dce5ad34c510f2c4ff1ed815b155d917ff95e6dca7c913c4a12dbb` |

The current normal build completes real AArch64 GType, loader-cache and
thumbnail MIME queries through the production target transport. Generated
GIR/typelib files and all installed package payload bytes are verified.

The preceding revision-2 installed-package consumer passed on 2026-10-09
on EmberBSD/AArch64 CM5, running EMBER64 #5
from source `4eb2495`. It embeds the installed modules, nine typelibs and MIME
source data; the target `update-mime-database` creates a temporary database.

Four cycles decode PNG, JPEG, TIFF, BMP, ICO, ANI, GIF, QTIF, XPM, XBM, PNM,
TGA and ICNS, both complete and in seven-byte increments. Every decoded pixel
is checked, with a small tolerance for JPEG. PNG/JPEG/TIFF/BMP/ICO also use
target encoders. Metadata loads include both packaged Gdk namespaces and the
seven GLib namespaces. An introspection/libffi call constructs a GdkPixbuf
and checks its width. Wrong argument counts and malformed PNG data fail as
expected. The consumer and remote cleanup both exit zero.

These are bounded CPU image and metadata checks. The complete upstream test
suite, thumbnailer CLI operation and long-running application behavior are
not covered. They establish neither display output nor GPU acceleration.
Board firmware and hardware revision were not re-audited by these tests.

## Printer source analysis

The actual configured MIME printer remains byte-identical to pinned upstream:
`thumbnailer/gdk-pixbuf-print-mime-types.c` has SHA256
`bfea22e9f5118b48ed062831cc333dfcf1f3183ce152221936ca3b15b25c9cc6`.
The eight project headers included by this unit are also unchanged.
The paired checks use the real Meson compilation database, wrapper-expanded
GCC16 arguments, AArch64 headers and generated feature/enum headers.
The checks retain hashes for the real input files. Generated headers are kept
as built; no replacement configuration is used.

GCC 16.2.0 `-fanalyzer` and Clang Static Analyzer 21 report no findings for
this unit before or after the recipe patches. This is selected-unit coverage.
Cppcheck 2.18 and current 2.22 both stop in GLib 2.90.1 autoptr macro/pragma
syntax when they read the actual GCC-preprocessed unit. Cppcheck 2.22's Clang
importer also fails on an AST scratch-space location with the real target and
sysroot restored. These parser failures establish no completed Cppcheck
coverage. No diagnostic category or source check is suppressed. These source
checks do not establish whole-library, dynamic memory or GUI acceptance.

## Reproduce the checks

Run from `profiles/common-graphics`, using new absolute work directories.
`BUILT_SOURCE` below is the accepted source directory containing `output/`.
Host selection checks use the accepted native prefix and cross compiler.

```sh
ruby tests/gdk-pixbuf-source.rb /path/to/gdk-pixbuf-2.44.8.tar.xz \
  /path/to/BUILT_SOURCE /path/to/new-source-check
python3.15 tests/gdk-pixbuf-cross.py --sdk-source /absolute/EmberBSD-SDK /path/to/BUILT_SOURCE \
  /path/to/native-prefix /path/to/cross-tools/bin/aarch64--netbsd-gcc \
  /path/to/new-selection-check
python3.15 tests/gdk-pixbuf-guards.py --sdk-source /absolute/EmberBSD-SDK /path/to/BUILT_SOURCE \
  /path/to/native-python /path/to/sysroot \
  /path/to/cross-tools/bin/aarch64--netbsd-readelf /path/to/new-guard-check
ruby tests/gdk-pixbuf-prepare.rb /path/to/cross-tools /path/to/sysroot \
  /path/to/BUILT_SOURCE /path/to/gdk-pixbuf2-2.44.8nb2.tgz \
  /path/to/shared-mime-info-2.5.1.tgz /path/to/work/new-consumer
EMBERBSD_SDK_SOURCE=/path/to/EmberBSD-SDK \
EMBERBSD_GI_QUERY_CONFIG=/path/to/private/query.json /path/to/native/python3.15 \
  ../../pkgsrc/devel/gobject-introspection/files/target-query.py \
  /path/to/work/new-consumer/gdk-pixbuf-consumer
```

The consumer preparation command above reproduces the revision-2 board check;
that helper still requires its exact `nb2` package. It does not accept `nb3`.
The current revision-3 target queries run during the normal package build.
The consumer directory must be inside the query JSON's `build_root`.
The source check verifies the upstream hash, applies eight patches without
fuzz and compares the six affected files to the accepted build. The Meson
check exercises native, ordinary cross and explicit cross selection; missing
native Python fails. It also checks all four real metadata build rules and
thumbnail MIME output. The Python guards link real GCC16 ELF fixtures.
Twenty-three refusal controls fail before SSH. Twelve mocked loader/MIME transports
check pinned host aliases, provider/module hashes, path rewrites, cache transfers,
cleanup and output refusal. Three native shell controls execute the production
pre/post hash loops with a native query stub. They do not execute target ELF.
The guard source input needs the patched upstream generator; a full GdkPixbuf
build is not required for that check.
A printer that emits MIME output but exits unsuccessfully must publish no
thumbnail metadata. The consumer preparation verifies package identity and
all installed payload bytes before compiling the target fixture. Keep its
input hashes and the runner's output, exit and cleanup logs with the private
build artifacts.
