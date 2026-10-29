# Native documentation generators for cross-built KDE

KDE consumers must execute `meinproc6`, `checkXML6` and `docbookl10nhelper`
on the build host. In a cross build, these come from the native package
[devel/kf6-kdoctools-generators](../../../../pkgsrc/devel/kf6-kdoctools-generators/).
Target libraries, headers, customization data and translations come from the
target package [devel/kf6-kdoctools](../../../../pkgsrc/devel/kf6-kdoctools/).
Native package builds retain their normal dependency.

## Native generators

The generator package builds the same KDocTools release from the same
distfile and patches as the target package. It installs the internal tools,
the DocBook customization data that they read and their CMake import. It
omits KI18n, translated manuals and upstream tests. It refuses a cross build.

The KDocTools `cross-tools.mk` file is included by the target recipe and by its
`buildlink3.mk`. Under `USE_CROSS_COMPILE` it adds the generator package to
`TOOL_DEPENDS`, so pkgsrc builds it natively into `TOOLBASE`. It passes
`KDOCTOOLS_TARGETSFILE` and the three executables from `TOOLBASE` to CMake.
No build-host setting is required, so parsing, fetching and ordering a cross
bulk never fail for KDocTools. Before configuration, the recipe checks the
CMake import, the `6.31.0` package version and the three executables.

Upstream `meinproc6 --version` reports the tool's hard-coded `5.0` banner.
The check reads the installed `KF6DocToolsConfigVersion.cmake` instead.
`RELOCATABLE_DOCBOOK_FILES` retains target paths in installed data instead of
recording the build host's data directories.

The canonical [DocBook XSL recipe](../../../../pkgsrc/textproc/docbook-xsl/) retains the installed
`pdf2index` Perl interpreter and its target package dependency. It does not
execute target Perl during packaging. Native builds retain `perl:run`.
DocBook XSL 1.79.2 remains the latest stable release in the
[upstream project](https://github.com/docbook/xslt10-stylesheets#docbook-xslt-10-stylesheets).
Its age does not justify silently selecting a snapshot.

The installed `KF6DocToolsConfig.cmake` searches explicitly selected native
imports with `NO_CMAKE_FIND_ROOT_PATH`. A cross consumer selects the import
with `KDOCTOOLS_TARGETSFILE` or `KF6_HOST_TOOLING`. Without that option, target-only CMake root
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

```sh
BMAKE=/absolute/bmake sh ../tests/kdoctools-generators.sh \
    /absolute/prepared-pkgsrc /absolute/cross.mk /absolute/new-test
```

This check parses the target package and the KPackage, KService,
KConfigWidgets and Prison consumers in the cross configuration. Each must have
no failure reason, must depend on the native generators and must pass their
`TOOLBASE` locations to CMake. The former `EMBERBSD_KF6_DOCTOOLS_HOST` setting
must not change anything. The generator package must use the target distfile,
add no failure of its own to a native CMake build and refuse a cross build.
The previous recipe fails this check because it required a configured
generator prefix, so a cross bulk could not fetch any KDocTools consumer.

After the generators are installed in `TOOLBASE`:

```sh
BMAKE=/absolute/bmake MAKECONF=/absolute/cross.mk \
    sh ../tests/doctools-tools.sh /absolute/prepared-pkgsrc \
    /absolute/toolbase /absolute/kdoctools-6.31.0 /absolute/new-test
BMAKE=/absolute/bmake MAKECONF=/absolute/cross.mk \
    sh ../tests/docbook-source.sh /absolute/prepared-pkgsrc \
    /absolute/docbook-xsl-1.79.2nb8.tgz /absolute/new-docbook-test
```

The first check runs the real generators on upstream's original DocBook
fixture. Valid input produces HTML; a well-formed document with an invalid
DocBook element fails validation. Missing tools, an old version and missing
native imports fail. Representative consumers use target build dependencies
and the native generator package instead of recursively building the target
KDocTools package.

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
from `TOOLBASE` generates English and German manual pages.

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
