# Shared GStreamer 1.28.8 source family

The common-media and plasma-mobile exports select GStreamer 1.28.8.
This is the [upstream stable bug-fix release](https://gstreamer.freedesktop.org/releases/1.28/#1.28.8)
from 2026-10-08. The [manifest](sources.tsv) records the original HTTPS
archives and SHA256, checked against upstream `.sha256sum` files.
This is not signature verification.

The core, base/good/bad/ugly plugins, libav, editing services, Python bindings
and RTSP server share pkgsrc's `gstreamer1/version.mk`. Their archive metadata
must move together; updating only the core would leave dependent recipes
requesting archives absent from their distinfo files. The imported recipes
retain original pkgsrc identifiers, authorship and licence metadata.
The libav consumer selects the common FFmpeg9 provider; its full build
and runtime compatibility are still unaccepted.

## Core cross build

The core recipe keeps libraries, utilities, core plugins, translations,
test binaries and all five GIR/typelib pairs. Native GLib generators and
Python scripts run on the build host. The former recipe attempted to execute
`/usr/pkg/bin/glib-mkenums` and target Python on macOS; both failures were
reproduced before the corrections.

GObject introspection uses the existing common-graphics target-query launcher.
The native scanner compiles a temporary query and executes it with the real
target libraries on the configured EmberBSD board. No GType replies are
invented. The source patch provides in-tree library paths to that launcher
and preserves the normal native build behavior.

The inherited GTK plugin patch was rebased because upstream removed its
`use_wayland` condition. Its early disabled-Wayland return still prevents
separate extension builds from consulting undefined Wayland dependencies.

```sh
OPENSSL=/absolute/openssl sh profiles/common-media/tests/source.sh \
    /absolute/distfiles /absolute/new-source-check
BMAKE=/absolute/bmake MAKECONF=/absolute/cross.mk \
    sh profiles/common-media/tests/gstreamer-cross.sh \
    /absolute/prepared-pkgsrc /absolute/new-package-check
```

The source check verifies every archive in sources.tsv, its patch hashes and
zero-fuzz application. The package check executes the original flex-version
script with its real native interpreter and checks actual generated grammar,
enums, all GIR/typelib outputs, utilities, plugins, scanner and translation.
Source checks do not establish complete plugin-family builds or playback.

Clang 23.1.3 Static Analyzer checked the inherited `gstrusage.c` port before
and after its clock-identifier patch using actual target compiler definitions,
headers and paths; neither run produced a diagnostic. Cppcheck 2.22.0 was
also attempted on the actual compile database and GCC16-preprocessed units.
It could not parse GLib's diagnostic pragmas within generated autoptr typedefs.
That failure is an analyzer limitation, not a successful Cppcheck result.
The scope is this changed C translation unit, not the entire multimedia stack.

## Accepted installed core on CM5

On 2026-10-12 the complete `gstreamer1-1.28.8` package passed normal
cross-package checks and installation into the common EmberBSD sysroot.
Package SHA256:
`23e9967c0a8f182c437443b0187c5620f52797f2f5f2a693e51d30a9ebcc9afa`.
All five GIR/typelib pairs were generated with real target GType queries.
The two installed documentation helpers remain in the package. Cross builds
skip executing the upstream documentation cache generator after installing
those helpers; a request for unsupported cross hotdoc generation still fails.
The installed Python helper retains its target interpreter.

The same package and normal GSL dependency were installed on CM5 Rev 1.0,
BCM2712 D0, 4 GiB, Waveshare CM5-NANO-B. Its experimental EmberBSD kernel was
`EMBERV3DRENDER #1`, SHA256
`6c5aa74d3c33fb6e84ea5c04d6f3df48928deb021cdc908ee972a42df03c7bf5`.
The following unchanged upstream suites passed against installed shared
libraries, without loader overrides:

| Suite | Passed | Failures/errors |
|---|---:|---:|
| GstBuffer | 25 | 0/0 |
| GstCaps | 37 | 0/0 |
| GstEvent | 2 | 0/0 |
| GstQuery | 2 | 0/0 |
| GstSegment | 11 | 0/0 |
| GstStructure | 29 | 0/0 |

The runner retains upstream's empty `GST_STATE_IGNORE_ELEMENTS` environment
beacon and core plugin whitelist. An initial run omitted that required beacon;
all buffer cases rejected the runner setup. No test implementation was changed.
A 64-buffer `fakesrc ! identity ! fakesink` pipeline reached EOS. An unknown
element failed with exit 1 and the expected diagnostic. Boot time was unchanged.
Target log archive SHA256:
`faf8b6b94f33a0d85d789cf2052e94c6191e8f136b6787a823009d0db3dffef3`.

```sh
READELF=/absolute/target-readelf ruby profiles/common-media/tests/stage-gstreamer-tests.rb \
    /absolute/built-gstreamer-source /absolute/sysroot /absolute/new-bundle
# Transfer the bundle without host extended attributes, then on EmberBSD:
sh /absolute/bundle/gstreamer-runtime.sh /absolute/bundle /absolute/new-results
```

This accepts 106 selected core checks and a finite non-media pipeline.
It does not accept all upstream tests, media decoding, audio/video output,
all plugin packages, long-running playback, or an accelerated Plasma session.

The [base/bad plugin receipt](gstreamer-plugins.md) adds installed media parser
and introspection checks, including the corrected core runtime dependency.
