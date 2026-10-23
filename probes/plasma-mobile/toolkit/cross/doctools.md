# Native documentation generators for cross-built KDE

KDE consumers must execute `meinproc6`, `checkXML6` and `docbookl10nhelper`
on the build host. A native pkgsrc KDocTools dependency previously rebuilt
QtTools and LLVM on macOS. The cross recipes now use selected native generators
and target KDocTools data. Native package builds retain their normal dependency.

## Build and select the generators

Use the verified Frameworks 6.31.0 archives in [sources.tsv](../sources.tsv),
matching native Qt 6.12 tools, Extra CMake Modules 6.31 and a native prefix
with libxml2, libxslt, DocBook XML 4.5, DocBook XSL, zlib, bzip2, XZ and Zstd.
Set `HOST_PERL` to a native Perl interpreter that provides `URI::Escape` from
`www/p5-URI`. The builder passes it to CMake as `PERL_EXECUTABLE`. Set
`PERL5LIB` if these modules use a separate native installation prefix.
On macOS, GCC16 can use a native Qt built against libc++ when `CXXFLAGS` puts
compatible libc++ headers before the SDK C headers and `LDFLAGS` selects the
matching libc++ runtime. Keep these host flags out of the target sysroot.
The builder requires Python 3.15 with its standard library and SDK API 1.
Select the SDK with `--sdk-source` or `EMBERBSD_SDK_SOURCE`.
The five positional arguments and the explicit native tool inputs are
required. `PERL5LIB`, pkg-config paths, compiler flags and the macOS SDK
selection are explicit recorded inputs. Other ambient build variables are not
forwarded. Use clean Ports and SDK source checkouts.

The builder verifies both source hashes before it creates the work directory.
Qt may print a locale warning under the builder's `LC_ALL=C` environment.
The builder requires exactly one `6.12.0` version line in the recorded output.
It uses the SDK process controller and an exclusive lock on the canonical
work path. Shared locks cover the Qt, native and ECM input directories.
All cooperating writers must use the same canonical paths and the work
parent as their lock root. These locks do not freeze uncoordinated installers.
The builder writes only the new work directory and lock files in its parent.
It does not download dependencies or install target packages.

`inputs.json` records sources, tool and archive hashes, Python, selected paths
and the effective environment. `commands/` and `logs/` record each native
command. `outputs.json` binds those records to installed file/link inventories
and the generated version header. `outputs.sha256` retains the three generator
hashes. The receipt does not seal transitive native dependency trees or qualify
a binary cache. Preserve the dependency owners' receipts separately.

A failed build retains its incomplete work. An unproven process shutdown also
writes `.producer-ownership-unproven.json`. Do not reuse that work or delete it
before its processes have been inspected. Successful completion requires
`outputs.json`, the version marker and no `incomplete.json`. The builder
publishes the version marker last, after input rechecks and output inventories.
A failed final check cannot admit the prefix through the existing consumer
version gate. The command never overwrites work.

```sh
CMAKE=/absolute/cmake NINJA=/absolute/ninja \
HOST_CC=/absolute/cc HOST_CXX=/absolute/c++ HOST_PERL=/absolute/perl JOBS=3 \
    python3.15 build-doctools-host.py --sdk-source /absolute/EmberBSD-SDK \
    /absolute/distfiles /absolute/native-qt \
    /absolute/native-prefix /absolute/native-ecm/cmake /absolute/new-work
```

The private host KArchive retains compression and cache support. Only the
host generator build omits translated manuals and upstream test executables.
The complete target KDocTools package retains translations and target tools.
Upstream `meinproc6 --version` reports the tool's hard-coded `5.0` banner.
The builder verifies the generated Frameworks version header as `6.31.0`.
It must not infer Frameworks compatibility from that banner.

Combine the KConfig and KDocTools import directories under one private directory:

```sh
mkdir /absolute/native-kf-tooling
ln -s /absolute/kconfig-host/tooling/KF6Config /absolute/native-kf-tooling/KF6Config
ln -s /absolute/new-work/tooling/KF6DocTools /absolute/native-kf-tooling/KF6DocTools
```

Set these inputs in the private cross MAKECONF:

```make
EMBERBSD_KF6_HOST_TOOLING=/absolute/native-kf-tooling
EMBERBSD_KF6_DOCTOOLS_HOST=/absolute/new-work/prefix
```

The recipe rejects missing CMake imports, absent executables and an incorrect
version marker before configuration. The imports select native executable
locations. Target libraries, headers, customization data and translations
remain in the common sysroot. `RELOCATABLE_DOCBOOK_FILES` retains target paths
in installed data instead of recording the build host's data directories.

The canonical [DocBook XSL recipe](../../../../pkgsrc/textproc/docbook-xsl/) retains the installed
`pdf2index` Perl interpreter and its target package dependency. It does not
execute target Perl during packaging. Native builds retain `perl:run`.
DocBook XSL 1.79.2 remains the latest stable release in the
[upstream project](https://github.com/docbook/xslt10-stylesheets#docbook-xslt-10-stylesheets).
Its age does not justify silently selecting a snapshot.

The installed `KF6DocToolsConfig.cmake` searches explicitly selected native
imports with `NO_CMAKE_FIND_ROOT_PATH`. Without it, target-only CMake root
searches re-root the host path, so KService fails to find `meinproc6`.
`tests/doctools-host-import.rb INSTALLED_CONFIG NEW_WORK` executes the installed
lookup with a real CMake target-only root. The corrected lookup passes; the
original lookup and missing-import controls fail. The complete KService 6.31
package now builds its translated manuals through the selected native tooling.

Relocatable stylesheets import DocBook XSL through `../../../xsl/docbook`.
They also load localization data from the `xsl` subdirectory.
libxslt resolves these paths relative to the symbolic link.
It does not use the link target.
In cross mode, the KDocTools `buildlink3.mk` links the complete customization
tree and the DocBook XSL tree into the consumer's buildlink directory.
The consumer gets DocBook XSL as a build dependency only.

## Reproduce the checks

Run the builder contract tests with an explicit SDK source:

```sh
python3.15 ../tests/doctools-builder.py --sdk-source /absolute/EmberBSD-SDK
```

These tests use small archive and command fixtures. They check preserved
CMake arguments, source/version rejection, busy locks, failure handling and
receipts. They do not build KArchive, KDocTools or prerequisite packages.
Set `DOCTOOLS_NATIVE_PROCESS_TEST=1` to also run the actual SDK process
controller with harmless fixture executables. This does not run a compiler.
Set `DOCTOOLS_TEST_RECEIPTS` to an existing evidence directory to retain the
fixture inputs and outputs. A failed native fixture retains its temporary
directory for inspection. No process inspection failure is converted to a pass.
The native generator and installed consumer checks below remain required.


```sh
BMAKE=/absolute/bmake MAKECONF=/absolute/cross.mk \
    sh ../tests/doctools-tools.sh /absolute/prepared-pkgsrc \
    /absolute/new-work/prefix /absolute/kdoctools-6.31.0 /absolute/new-test
BMAKE=/absolute/bmake MAKECONF=/absolute/cross.mk \
    sh ../tests/docbook-source.sh /absolute/prepared-pkgsrc \
    /absolute/docbook-xsl-1.79.2nb8.tgz /absolute/new-docbook-test
```

The first check runs the real generators on upstream's original DocBook
fixture. Valid input produces HTML; a well-formed document with an invalid
DocBook element fails validation. Missing tools, old markers and missing
native imports fail. Representative consumers use target build dependencies
instead of recursively building native KDocTools.

The second check applies the recipe patch to the pinned pkgsrc with zero fuzz,
compares the export, rejects repeated application, and inspects the actual
package's Perl dependency and installed interpreter line.

```sh
BMAKE=/absolute/bmake MAKECONF=/absolute/cross.mk \
    sh ../tests/kdoctools-buildlink.sh /absolute/prepared-pkgsrc \
    /absolute/new-buildlink-test
```

Install the KService dependencies into the cross sysroot before this check.
The check reads the dependency metadata and the KDocTools contents filter.
It prepares a real KService buildlink directory. Then the native `meinproc6`
from `EMBERBSD_KF6_DOCTOOLS_HOST` generates English and German manual pages.

On 2026-10-12, the complete GCC16 cross packages passed dependency, manifest,
interpreter, permissions, PIE, RELRO, RPATH and build-path checks. Native
DocBook generation and the input/recipe checks passed on macOS ARM64.
Target KDocTools execution, its complete upstream suite, memory analysis and
the desktop session remain separate acceptance gates. No C/C++ source changed
in these recipes; these checks do not claim whole-source static analysis.

On 2026-10-21 on macOS ARM64, the buildlink check passed for the amd64
target. Manual controls failed: the previous KDocTools `buildlink3.mk`,
a full DocBook dependency and a filter without the customization tree.
The previous file failed with the DocBook XSL import error.
The DocBook recipe check still passed.

| Package | SHA256 |
| --- | --- |
| kf6-kdoctools-6.31.0nb2.tgz | `9245467ec344cfea1abc15bf8486fbd020f2518af1e25e022961e0353d102073` |
| docbook-xsl-1.79.2nb8.tgz | `eee9eb377b1fa2b2a8d2202de67a19bdd5732fd0a7d5bb020244d6867f546c2c` |
