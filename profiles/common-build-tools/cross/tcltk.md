# Common Tcl and Tk 9.1

The current profiles use Tcl 9.1.0 at `lang/tcl` and paired Tk 9.1.0 at
`x11/tk`, in the standard package prefix. `lang/tcl/Makefile.version` owns
both release selections. Generic `-ltcl` and `-ltk` buildlink names select
the current libraries. This does not make the Tcl 8 ABI compatible with Tcl 9.

The development toolchain, common tools, graphics, media and Plasma exports
replace the pinned pkgsrc providers. The default export retains pkgsrc's pins.
The current profiles do not add an old runtime for an application.
Consumers that require Tcl 8 need an API port.

Tcl retains Itcl 4.3.8, SQLite 3.53.4 bindings, TDBC 1.1.15, its four database
drivers, Thread 3.0.7, modules, encodings, messages, headers and manuals.
The SQLite bindings link the common system SQLite library.
Both Tcl and Tk retain ZipFS and install their external script trees.
The original debug options and upstream test targets remain available.

Tk retains X11/Aqua selection, Xft, XScreenSaver, XRender, CUPS printing,
ATK accessibility and bidirectional text. The X11 default enables the CUPS,
ATK, bidi and Xft options. Bidi uses bundled SheenBidi and common HarfBuzz.
CUPS uses `print/libcups`. It does not require the print server.
Tk tests require a display and a suitable window manager.

## Source and attribution

The recipes retain pkgsrc RCS attribution. They adapt the pinned `lang/tcl90`
and `x11/tk90` recipes to the common package names and prefix.
The [official release](https://www.tcl-lang.org/software/tcltk/download.html)
supplies unchanged source archives with their original `license.terms`.
The recipes retain pkgsrc's license identifier. Original file notices remain.

| Archive | SHA256 |
| --- | --- |
| `tcl9.1.0-src.tar.gz` | `536c45543f64d6eb11832d97ba3494aacff046fbc5040273bd55258d0e448ff1` |
| `tk9.1.0-src.tar.gz` | `772ce7a97c07c2db4c957c93af7ab4dff4bd3037772836b6afbcd0974023b3d6` |

[Tools sources](../sources.tsv), [graphics sources](../../common-graphics/sources.tsv)
and recipe `distinfo` files retain upstream URLs and hashes.
Local patches are AI-assisted and have not been submitted upstream.

## Build and target roles

The Tcl platform patch changes nineteen maintained and generated files,
including all eight bundled extension configurations. The Tk patch changes
its generated script and two maintained Autoconf inputs.
Cross configuration selects the declared target OS and release.
Native configuration retains `uname`. Compiler feature probes remain active.
The build host's Debian marker cannot classify an explicit NetBSD target.

Cross recipes declare current native Tcl as a tool dependency. Thread uses
that interpreter for its ZipFS payload. Tk's interpreter discovery also
selects the native provider. `CC_FOR_BUILD` selects `NATIVE_CC`.
Target objects still use the common GCC16 cross compiler.
Native Zip remains a declared dependency. Target ELF helpers must not run
on the build host.

An additional Tcl patch separates two encoding API names in `Encoding.3`.
The release manual installer otherwise joins them into one invalid alias.
The correction retains both actual API manual names.

The system-SQLite repair keeps `SQLITE_EXTERN` overrides in the bundled-only
configure branch. System headers retain their external data declarations.
The original unconditional flag defines three SQLite globals in the binding,
including an invalid one-byte `sqlite3_version` array.
The [object regression](../tests/tcl-sqlite-extern.py) compares actual compiled
binding objects and checks their SQLite symbol ownership.
The Tcl stub archive is installed with data-file permissions.

Prepare sources through the supported exporter:

```sh
sh scripts/prepare-pkgsrc.sh /absolute/new/pkgsrc common-graphics
```

Use a native GCC16 MAKECONF with private work and package output directories.
Its final prefix must match `EMBERBSD_CROSS_HOST_PREFIX`:

```sh
bmake -C /absolute/new/pkgsrc/lang/tcl MAKECONF=/absolute/native.mk.conf package
bmake -C /absolute/new/pkgsrc/lang/tcl MAKECONF=/absolute/native.mk.conf test
```

Install the accepted native package with normal pkgtools before target builds.
Use the [common GCC16 cross profile](README.md) for `lang/tcl` and `x11/tk`.
Target installation and execution remain separate acceptance gates.

## Focused checks and limits

The source regression uses Python 3.15 and its standard library:

```sh
python3.15 profiles/common-build-tools/tests/tcltk-platform.py \
    /absolute/cache/tcl9.1.0-src.tar.gz \
    /absolute/cache/tk9.1.0-src.tar.gz /absolute/new/check-output
```

It verifies archive bytes, zero-fuzz platform patches, all 22 platform files
and ten shell syntax checks. It executes 114 actual generated branch cases
on a Debian build host. These cover unchanged Linux/Darwin native selection,
cross targets, Windows TEA and the Debian marker. It also executes the real
manual installer before and after the encoding alias repair.

Actual pkgsrc metadata selects Tcl/Tk 9.1.0 for native and cross roles.
Native prerequisites have normal package registrations. The Tk source PLIST
follows the real 9.1 script, header, demo and manual installation rules.
That inventory configuration does not establish enabled feature behavior.

The ordinary Linux/GCC16 `tcl-9.1.0nb1` package passes the package checks.
All payload bytes, links and modes match its complete stage. Its executable
and extension libraries are native x86_64 ELF files. The native
[host contract](../tests/tcl9-host.tcl) passes ZipFS archive creation,
Unicode data, Itcl state, a system SQLite query, TDBC SQLite and Thread.
The actual binding-object regression removes all three invalid SQLite
data definitions and retains its real SQLite API import.

The full upstream runner exits zero but reports failures. The core reports
503,271 passed, 8,066 skipped and 16 failed tests out of 511,353.
External HTTP connections fail in a proxy-only environment. A reserved-port
test fails where unprivileged low ports are enabled. Two files exit under
the C locale. Those two files pass in a clean UTF-8 test directory:
17,038 passed, 30 skipped, zero failed tests out of 17,068.
The SQLite extension's leap-second test fails because common SQLite 3.53.4
returns NULL for `julianday('2012-06-30 23:59:60')`. The binding and the real
SQLite CLI agree. The expected Julian date remains an unresolved test limit.
Other bundled extension targets report no failed tests; raw results retain
skips and zero-test subgroups. This is not full upstream test acceptance.

Strict Valgrind 3.24 Memcheck of the native host contract remains nonclean.
It reports no definite or indirect loss, but 2,573,312 possibly lost bytes
and 221,996 reachable bytes. There are 124 reported contexts and no
suppressions. Native allocator memory acceptance remains pending.

The existing `TCL_FINALIZE_ON_EXIT=1` diagnostic requests full finalization
in the ordinary installed package. It still reports 2,442,240 possibly lost
bytes and 296,896 reachable bytes in 132 heap-only contexts.
No invalid-access or uninitialized-value record occurs in either run.

A separate build with the existing `debug` option enables `TCL_MEM_DEBUG`.
Upstream then disables `USE_THREAD_ALLOC` and adds its memory diagnostics.
The actual debug interpreter and all loaded extensions are checked before
the same host contract runs. With full finalization, strict Memcheck reports
1,706 possibly lost bytes in 14 records, no definite or indirect loss,
no reachable bytes and no access errors. It still exits with failure.
This diagnostic build does not replace ordinary package memory acceptance.

Cross packages, installed EmberBSD extension tests, Tk display behavior and
OCCT Draw remain separate checks. Native host preparation does not establish
a working GUI package.
