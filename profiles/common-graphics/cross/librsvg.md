# Cross-packaged librsvg

The common graphics profile selects librsvg 2.63.4, including its C library,
`rsvg-convert`, the dynamic GdkPixbuf SVG loader and Rsvg GIR/typelib.
Embedded AVIF is enabled through dav1d 1.5.4. xxHash 0.8.4 supplies dav1d's
build dependency. [GdkPixbuf and shared MIME data](gdk-pixbuf.md),
[GLib metadata](introspection.md#glib-2901-metadata-package), and the
[native Rust toolchain with target std](../../common-build-tools/rust-target-std.md)
are prerequisites, not alternate dependency stacks.

## Current validation boundary

The 2.63.4nb2 package builds on macOS and installs in the EmberBSD AArch64
cross sysroot. The locked AVIF/pixbuf build compiled its recipe-patched
Cargo closure, including num-derive 0.5.1 and av-data 0.4.4. Source checks cover
the patched lock, selected crate versions and complete patch inventory. Rsvg
GIR and typelib generation used a successful real target GType query. The
rebuilt CSS-only C API consumer adds ID, adjacent-sibling and child-selector
pixel coverage; these new target assertions have not yet run against nb2. The
earlier nb1 consumer pass covered pixel colors, `:lang`, malformed SVG
rejection and pseudo/at-rule diagnostics; it does not validate the selectors/
servo_arc adapter.

The recipe follows the current CSS and HTML/XML dependency family: cssparser
0.38 with cssparser-color 0.6, selectors 0.42 and servo_arc 0.6;
markup5ever/xml5ever 0.40;
and string_cache 0.11 with PHF 0.14 and web_atoms 0.3. `patch-Cargo.toml` and
`patch-Cargo.lock` update source constraints and the lock together, while
`cargo-depends.mk` and `distinfo` select and checksum only that resolved
closure. The old cssparser/selectors, markup5ever/xml5ever, string_cache and
PHF generations are absent from the active lock. A focused source patch adapts
librsvg to cssparser 0.38's owned parse errors and selectors' error API;
CSS diagnostics use the rule/declaration boundary exposed by stylesheet
iterators and retain unknown pseudo-class and at-rule names in owned errors.
The selectors/servo_arc refresh and cascade-wide Copy-handle adapter are
packaged as 2.63.4nb2. The final target package build passed; its new target
CSS runtime assertions remain pending hardware runtime validation.

Historical 2.63.2 evidence: the packaged consumer passed four CPU-rendering
lifecycles on physical CM5 with C API RGB pixels, CLI PNG, the dynamic
GdkPixbuf SVG loader, embedded AVIF, text with Ahem, and construction through
the Rsvg typelib. Malformed SVG was rejected through both the C API and CLI;
recursive providers were hash-checked before and after execution. Those CM5
results used the 2.63.2 package and a GCC16 consumer; they were not repeated for
2.63.4. The earlier 2.63.4nb1 Zero3W result above is the focused CSS C API
check and does not validate the nb2 selectors adapter.

The earlier loader failure was a test-bundle defect: GdkPixbuf uses GIO MIME
detection, but the isolated consumer omitted the shared MIME database.
The corrected bundle verifies all 84 shared-mime-info package files and
generates a private database from its original XML before image detection.
It sets both XDG data directories explicitly. GError diagnostics now name
the failing domain and code. The CLI negative accepts only normal exit 1;
an actual-process regression rejects missing exec, signals and setup errors.
Omitting only MIME database generation reproduces the original format error
with the same packaged renderer and library providers.
The conditional AVIF/dav1d consumer buildlink correction is saved;
downstream labwc packaging and its accelerated session remain separate work.

The final exporter passed 99 refusal checks and a complete common-graphics
export. All five added recipe directories matched the exported copies byte
for byte. Other profile compositions were not rerun at this checkpoint.
This accepts the bounded packaged SVG consumer, not the full upstream suite,
GPU rendering or a complete desktop.

Sources come from [GNOME](https://download.gnome.org/sources/librsvg/2.63/),
[VideoLAN](https://downloads.videolan.org/pub/videolan/dav1d/1.5.4/) and
[xxHash upstream](https://github.com/Cyan4973/xxHash/releases/tag/v0.8.4).
Their versions and SHA256 values are in [sources.tsv](../sources.tsv).
The upstream Cargo.lock in the release archive remains untouched. The recipe's
patched lock, dependency list, vendor inputs and archive checksums are checked
together; pkgsrc verifies the separately recorded archive digests before
extraction. Cargo builds offline with `--locked`.

## Cross adaptation

The recipe uses pkgsrc's `RUST_TYPE=native` mode with declared host tool
dependencies: Rust 1.99.1, cargo-c 0.10.25 and the matching target std package.
GI's validated target metadata selects one coherent provider set:

| pkgsrc architecture | GNU tools | Rust ABI | Native std data package |
| --- | --- | --- | --- |
| aarch64 | aarch64--netbsd | aarch64-unknown-netbsd | rust-std-aarch64-netbsd |
| x86_64 | x86_64--netbsd | x86_64-unknown-netbsd | rust-std-x86_64-netbsd |

Meson's triplet, `nm`/`strip`/`ar`, Cargo target linker and target C/C++ keys
use that same selection. Unknown or mixed target metadata fails.
The native Cargo linker key comes from the actual shared compiler's host
triple after checking its official 1.99.1 release and producer commit.
It does not assume that the build host has the target architecture.
Native build scripts and
procedural macros use the selected native-prefix compiler and archiver;
target code uses the selected Clang wrapper, fork sysroot and runtime. No Rust,
LLVM or GCC rebuild is part of this consumer recipe. Rust source locations are remapped so panic
strings do not retain private build paths.

Before configure, the recipe checks the selected cross-wrapper identities,
matching Cargo, and the official shared Rust 1.99.1 compiler producer.
The selected std directory must resolve inside that same native provider.
Exactly one nonempty, regular, nonsymlink `std` and `core` rlib must exist there.
The actual compiler then imports std with `--emit=metadata` and records
`WRKDIR/target-std-check.rmeta`. Foreign or incompatible metadata is an error,
including E0461 and E0514. This check does not invoke a linker or target file.
The std data package retains its own full payload and ELF validation contract.

Meson's cross machine file selects the target ELF `nm` and `strip` tools.
The scanner canonicalizes include paths. A recipe-local compiler transform
maps the real sysroot prefix back into the declared buildlink tree, including
when the configured sysroot is a symlink. A negative control removes just
this transform and reproduces the missing Cairo header failure.

The explicit `emberbsd_gi_cross` path selects native scanner/compiler tools and
the shared [real target query launcher](introspection.md). Native builds keep
upstream behavior. A cross build without that explicit path still refuses
enabled introspection. No executable emulator or false `can_run_host_binaries`
answer is used.

The same explicit cross configuration supplies the SVG module installation
directory under the target prefix. This prevents pkg-config's sysroot-rebased
lookup path from appearing in the package; native directory selection is
unchanged. The regression executes both selections and checks the actual
module installation path in Meson's generated target metadata.

The inherited pkgsrc big-endian fixes were refreshed for matrixmultiply
0.3.11, memchr 2.8.3, wide 1.7.1 and zune-jpeg 0.5.15. New matching NEON branches
in wide use the same scalar fallback. These changes retain their pkgsrc
authorship and checksum records. This work validates little-endian AArch64;
it does not establish big-endian runtime support.

Upstream Meson and Cargo wrappers still use Python. These are existing build
dependencies, not new project-owned Python helpers. The optional `doc` option
remains off by default; upstream Vala bindings require an independently selected
native Vala provider. Neither is part of the default pkgsrc payload.

## Build and checks

Prepare the common graphics export, the shared native tool packages, the
accepted cross sysroot, and the GI query configuration described in the linked
instructions. Keep work, temporary files and packages on the selected build
volume. Use a bounded `MAKE_JOBS`, such as 2. Coordinate target access before
the build reaches GIR generation.

```sh
# Provide a verified source-data export at /absolute/new-pkgsrc. See the root README.
cd /absolute/new-pkgsrc/graphics/librsvg
env TMPDIR=/absolute/build-tmp MAKECONF=/absolute/cross.mk.conf bmake package
env TMPDIR=/absolute/build-tmp MAKECONF=/absolute/cross.mk.conf bmake install
```

`install` registers the package in the private cross sysroot. It does not
install base files or packages on the board. Keep sysroot source revisions,
artifact hashes and accepted provenance limitations with the build record.
The inherited NetBSD ABI names do not authorize an upstream base replacement.

The consumer helper writes `runtime-library-dirs.txt` from the selected
package's ELF dependencies. Use that value for the query configuration's
`library_dirs`; it is the selected target runtime directory when required and
empty otherwise. This keeps the executable and its dependencies on the same
runtime provider.
The AVIF option also admits dav1d through librsvg's consumer buildlink because
the generated pkg-config metadata lists it in `Requires.private`.

The following regressions check the actual patched source and completed build:

```sh
/absolute/native/python3.15 -B -I -S \
  profiles/common-graphics/tests/librsvg-inputs.py \
  /absolute/original-librsvg-source /absolute/built-librsvg-source \
  /absolute/librsvg-work/vendor
ruby profiles/common-graphics/tests/librsvg-cross.rb \
  /absolute/built-librsvg-source /absolute/native-prefix \
  /absolute/cross-tools/bin/aarch64--netbsd-clang /absolute/new-selection-work
```

The first checks the patched lock against `cargo-depends.mk`, selected shared
crate versions, the AVIF dependency chain and the patched `av-data` manifest in
the vendor tree. The package `checksum` target verifies crate archives and
patch checksums; Cargo's locked build checks resolvability. The second checks
the header transform and executes the real Meson guard fragments for native,
default cross and explicit cross configurations, then checks native generator
selection, the target module installation path and actual full-build outputs.

The target selection and std guard also have a separate host regression:

```sh
EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK BMAKE=/absolute/native/bmake \
  /absolute/native/python3.15 profiles/common-graphics/tests/librsvg-targets.py \
  /absolute/native-prefix /absolute/cross-tools /absolute/new-target-check
```

It evaluates both canonical target metadata sets with real `bmake` and rejects
unknown or mixed inputs. The actual native Rust 1.99.1 provider imports its
official amd64 std metadata. A private fixture copies genuine native Darwin
std/core bytes to a target sysroot and delegates all queries to the real
compiler; E0461 rejects that foreign data. No Cargo responses are fabricated.
Duplicate std archives fail before the metadata import.
This check does not build Cargo dependencies, librsvg, GIR data or a package.
The 2.63.4nb2 package and target GType query are current AArch64 results. The
focused Zero3W CSS consumer result is from nb1. Full four-cycle CM5 consumer
acceptance remains the historical 2.63.2 result; the nb2 target runtime and
amd64 renderer build remain pending. The target receives no compiler or
development tools.

## Packaged target consumer

[`prepare-librsvg-package.py`](../tests/prepare-librsvg-package.py) compares
every installed renderer and MIME package file and symlink against the archives and cross-builds
[`librsvg-package.c`](../tests/librsvg-package.c). It embeds those exact files,
their required metadata, and two hash-pinned fixtures from the upstream source:
the Ahem font and `rectangle.avif`. The embedded font retains its public-domain
notice. Upstream font notes, authors and LGPL text accompany the fixtures.

```sh
/absolute/native/python3.15 -B -I -S \
  profiles/common-graphics/tests/prepare-librsvg-package.py \
  --css-only --sdk-source /absolute/EmberBSD-SDK \
  /absolute/cross-tools /absolute/sysroot \
  /absolute/librsvg-work/.destdir/usr/pkg \
  /absolute/build-root/new-css-consumer
env EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK \
  EMBERBSD_GI_QUERY_CONFIG=/absolute/query.json /absolute/native/python3.15 -B -E -S \
  pkgsrc/devel/gobject-introspection/files/target-query.py --execute \
  /absolute/build-root/new-css-consumer/librsvg-css-package
```

The staged-prefix argument points to the package's `.destdir/usr/pkg` tree;
the helper checks the linked renderer against that exact package stage before
execution. The CSS-only query checks its C API path and belongs inside the
configured query build root. The full consumer renders known
red, green and blue pixels through the C API, CLI PNG and dynamically queried
SVG loader. It also checks embedded AVIF pixels, text with the isolated Ahem
font, and a constructor invoked through the installed Rsvg typelib. Four
create/render/destroy cycles must pass; malformed SVG must fail in both C and
CLI paths. Loader or transport failures are failures, not passing negatives.

The launcher stages the recursive target ELF providers in a private temporary
directory, verifies hashes, enforces a timeout, records status and cleans up.
The consumer creates its own loader cache, MIME database and font configuration there. No
board package registration, global loader cache or font cache is changed.

`librsvg-package --loader-only` isolates format detection and loading when
executed directly in a fresh target scratch directory with the same providers.
`ruby profiles/common-graphics/tests/librsvg-cli-status.rb /absolute/new-work`
tests the production CLI status predicate and reproduces the old false
positives with real missing-executable and signal exits.
With `EMBERBSD_GI_QUERY_CONFIG` set, run
`python3.15 profiles/common-graphics/tests/librsvg-mime-regression.py --sdk-source /absolute/EmberBSD-SDK /absolute/prepared-consumer /absolute/new-work`
to reproduce the MIME omission using the real target loader. Both directories
must be inside the configured query build root. The negative control must
fail specifically at SVG format detection and clean its target directory.

This is bounded CPU renderer acceptance. GPU rendering, a Wayland surface,
labwc integration, the complete upstream test suite and long-duration operation
require their own checks. Renderer warnings remain in the private build log.
