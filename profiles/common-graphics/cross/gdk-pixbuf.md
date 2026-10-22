# GdkPixbuf packages for EmberBSD cross builds

The graphics profile supplies `gdk-pixbuf2-2.44.8nb2` and
`shared-mime-info-2.5.1`. Applications can load the selected raster formats
and use GdkPixbuf through GObject Introspection. Both packages cross-build on
macOS with GCC16 for EmberBSD/AArch64 and install into the private sysroot.
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
No new project-owned Python helper is introduced.

The scoped [target tool runner](../recipes/graphics/gdk-pixbuf2/files/target-tools.rb)
executes the target loader and MIME queries with the target modules. It checks
ELF architecture and provider roots, resolves the runtime closure, verifies
hashes before and after each query and removes its private remote directory.
It publishes output only after successful execution, cleanup and unchanged
local inputs. Each query is limited to 60 seconds. The board receives no
package or base-system installation.

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

Normal package/install checks pass, including PLIST, interpreters,
permissions, PIE, RELRO, runtime search paths and work-directory references.
All 147 GdkPixbuf payload files/links and 84 shared-mime-info payload
files/links match the installed packages. Accepted package SHA256 values:

| Package | SHA256 |
| --- | --- |
| `gdk-pixbuf2-2.44.8nb2.tgz` | `4c660c73876ca4cc5ecb21657126f90f7522461f0f0a173d90a63b4278c20ac0` |
| `shared-mime-info-2.5.1.tgz` | `64b6f76d49a629e0ed59e96b7ee6d87ba266ad5c4db847d1f1b8b673119dbc47` |

Two real GType queries, the loader-cache query and the thumbnail MIME query
completed on CM5 with zero exit and cleanup statuses. On 2026-10-09 the
installed-package consumer passed on EmberBSD/AArch64 CM5, running EMBER64 #5
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

## Reproduce the checks

Run from `profiles/common-graphics`, using new absolute work directories.
`BUILT_SOURCE` below is the accepted source directory containing `output/`.
Host selection checks use the accepted native prefix and cross compiler.

```sh
ruby tests/gdk-pixbuf-source.rb /path/to/gdk-pixbuf-2.44.8.tar.xz \
  /path/to/BUILT_SOURCE /path/to/new-source-check
ruby tests/gdk-pixbuf-cross.rb /path/to/BUILT_SOURCE \
  /path/to/native-prefix /path/to/cross-tools/bin/aarch64--netbsd-gcc \
  /path/to/new-selection-check
ruby tests/gdk-pixbuf-guards.rb /path/to/BUILT_SOURCE \
  /path/to/native-python /path/to/sysroot \
  /path/to/cross-tools/bin/aarch64--netbsd-readelf /path/to/new-guard-check
ruby tests/gdk-pixbuf-prepare.rb /path/to/cross-tools /path/to/sysroot \
  /path/to/BUILT_SOURCE /path/to/gdk-pixbuf2-2.44.8nb2.tgz \
  /path/to/shared-mime-info-2.5.1.tgz /path/to/work/new-consumer
EMBERBSD_GI_QUERY_CONFIG=/path/to/private/query.json python3.15 \
  recipes/devel/gobject-introspection/files/target-query.py \
  /path/to/work/new-consumer/gdk-pixbuf-consumer
```

The consumer directory must be inside the query JSON's `build_root`.
The source check verifies the upstream hash, applies eight patches without
fuzz and compares the six affected files to the accepted build. The Meson
check exercises native, ordinary cross and explicit cross selection; missing
native Python fails. It also checks all four real metadata build rules and
thumbnail MIME output. Seven helper refusal controls must fail before SSH.
A printer that emits MIME output but exits unsuccessfully must publish no
thumbnail metadata. The consumer preparation verifies package identity and
all installed payload bytes before compiling the target fixture. Keep its
input hashes and the runner's output, exit and cleanup logs with the private
build artifacts.
