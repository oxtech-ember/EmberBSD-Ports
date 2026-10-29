# Stored GObject Introspection dumps

`g-ir-scanner` learns GType hierarchies, signals and properties by running
a small dumper program linked against the library it scans. A cross build
cannot run that program, so the recipes route it through `GI_CROSS_LAUNCHER`
([target-query.py](../../../pkgsrc/devel/gobject-introspection/files/target-query.py)).
The launcher either asks a live EmberBSD target or replays a dump that was
captured from one earlier and stored with the recipe.

## Modes

[devel/gobject-introspection/cross.mk](../../../pkgsrc/devel/gobject-introspection/cross.mk)
selects the mode with `EMBERBSD_GI_DUMP_MODE`:

| Mode | Target | Needs `EMBERBSD_GI_QUERY_CONFIG` | Result |
|------|--------|----------------------------------|--------|
| `replay` (default) | none | no | writes the stored dump |
| `live` | yes | yes | writes the target's dump |
| `capture` | yes | yes, and `EMBERBSD_GI_DUMP_CAPTURE_DIR` | as `live`, and stores the normalized dump |

A recipe that also executes target programs can set `EMBERBSD_GI_EXECUTE=yes`
before the include; it then needs the query configuration in every mode.
`gdk-pixbuf2` does not: its loader cache and MIME list follow the same modes
(see below). `talloc` and `tdb` replay stored Waf answers instead
([waf-answers.md](../../common-media/cross/waf-answers.md)). The configure-time check
`emberbsd-gi-inputs` refuses a wrong mode, a missing query configuration
outside replay and a missing capture directory. Fetch is never refused.

In replay, `emberbsd-gi-native` checks that
`${PKGDIR}/files/gi-dump/${CROSS_OPSYS}-${CROSS_OS_VERSION}-${MACHINE_ARCH}`
exists instead of running the target `--check`.

## Stored dump format

One file per dumper program, named after its basename (the GIR
`Namespace-Version`), for example
`pkgsrc/x11/gtk3/files/gi-dump/NetBSD-11.0-aarch64/Gtk-3.0.xml`:

```xml
<!-- EmberBSD GI dump 1
platform: NetBSD-11.0-aarch64
recipe: x11/gtk3
package: gtk3+-3.24.52
program: Gtk-3.0
types-sha256: <sha256 of the scanner's type list>
dump-sha256: <sha256 of the body below>
-->
<?xml version="1.0"?>
<dump>
...
```

The body is normalized: strict UTF-8, LF line ends, no trailing blanks, one
final newline, well-formed XML with a `<dump>` root. The header names no
host, address or user; the guard test keeps it that way.

Replay ([gi_dump.py](../../../pkgsrc/devel/gobject-introspection/files/gi_dump.py))
refuses, without writing any output, when the dump is missing, has no
header, or any field differs from this build: platform, recipe, package
version (`PKGNAME_NOREV`, so `PKGREVISION` bumps keep dumps), program, or
the type list that the scanner passed. It also refuses a body that differs
from `dump-sha256` or is not normalized, and an existing output file. A
changed source release or type list therefore needs a new capture.

## Capturing

Any EmberBSD target works: a VM installed by the EmberBSD VM install guide,
or a board. Recipes and profiles never name it. Keep the target in a private
query configuration outside the Git tree, for example:

```json
{
  "target": "aarch64",
  "ssh": "root@<target>",
  "build_root": "/absolute/work",
  "sysroot": "/absolute/sysroot",
  "cache": "/absolute/gi-cache",
  "readelf": "/absolute/tools/bin/aarch64--netbsd-readelf"
}
```

The key set is checked by `target-query.py --check` (see
[introspection.md](introspection.md)). Each query uses one remote
`mktemp -d /tmp/ember-gir.XXXXXXXX` directory that it removes afterwards;
nothing is installed on the target. Then build the consumer with its
dependencies already in the sysroot:

```sh
mkdir /absolute/gi-capture
bmake EMBERBSD_GI_DUMP_MODE=capture \
  EMBERBSD_GI_QUERY_CONFIG=/absolute/private/query.json \
  EMBERBSD_GI_DUMP_CAPTURE_DIR=/absolute/gi-capture build
```

Dumps appear under `/absolute/gi-capture/PLATFORM/CATEGORY_NAME/`. Review
them and copy them to `pkgsrc/CATEGORY/NAME/files/gi-dump/PLATFORM/`.
Capture refuses to overwrite an existing captured file.

## GdkPixbuf target data

`graphics/gdk-pixbuf2` also needs the output of two target programs at build
time: `gdk-pixbuf-query-loaders` (the build-time loader cache; the installed
cache is generated on the target at package install) and
`gdk-pixbuf-print-mime-types` (the thumbnailer MIME list). Both depend only
on the release and the loader module set.
[target-tools.py](../../../pkgsrc/graphics/gdk-pixbuf2/files/target-tools.py)
follows `EMBERBSD_GI_DUMP_MODE`. In replay it answers from
`files/target-data/PLATFORM/loaders.cache` and `mime-types.txt`
([pixbuf_data.py](../../../pkgsrc/graphics/gdk-pixbuf2/files/pixbuf_data.py))
without the SDK, a query configuration or a target. Each file has a
`# EmberBSD GdkPixbuf target data 1` header naming platform, recipe,
package, query, the sorted loader module file names and the data checksum;
module paths are stored as `@MODULE@/<file name>`. Replay refuses another
platform, recipe, package or module set. A capture build also writes
`/absolute/gi-capture/PLATFORM/graphics_gdk-pixbuf2/loaders.cache` and
`mime-types.txt`; copy them to `files/target-data/PLATFORM/`. Its remote
directories are `/tmp/ember-pixbuf.XXXXXXXX`, removed after each query.

## Tests

- [gi-dump.py](../tests/gi-dump.py) runs the launcher without a target:
  replay, every identity refusal, body hash, header, existing output,
  normalization, capture round trip and the unchanged live path.
- [gi-dump-modes.py](../tests/gi-dump-modes.py) checks the recipe wiring
  with a real cross MAKECONF: default replay directory and environment,
  replay without a query configuration, the live `--check`, capture and
  mode refusals, `EMBERBSD_GI_EXECUTE`, GdkPixbuf target data replay and
  WebKit's CMake environment.
- [pixbuf-data.py](../tests/pixbuf-data.py) runs the GdkPixbuf runner in
  replay without SDK or target: round trip, identity, module-set and
  checksum refusals, capture normalization and the unchanged live path.
- [gi-configure-inputs.py](../tests/gi-configure-inputs.py) checks the
  query configuration in live mode.
