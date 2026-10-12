# KCMUtils cross tooling and CM5 package

The complete KCMUtils 6.31.0nb1 package cross-builds against the common Qt
6.12 and KDE Frameworks 6.31. It retains Core, Widgets, Quick/QML components,
translations and the target metadata generator. KTextWidgets and KXmlGui
6.31.0nb1 also package and install with the complete dependency closure.

KCMUtils's build-tree alias previously selected the target metadata generator
during cross compilation. The tools subdirectory now imports the explicit
native tooling. The imported target is global so sibling autotest directories
can resolve it. Cross consumers require that native import and do not fall
back to an installed target executable. Native builds keep their ordinary alias.

Build the upstream native generator with the same pinned source archive:

```sh
CMAKE=/absolute/native-cmake NINJA=/absolute/native-ninja \
  HOST_CC=/absolute/native-cc HOST_CXX=/absolute/native-c++ JOBS=2 \
  sh build-kcmutils-tool.sh DISTFILES HOST_QT ECM_CMAKE_DIR NEW_WORK
```

Copy `NEW_WORK/tooling/KF6KCMUtils` into the common `EMBERBSD_KF6_HOST_TOOLING`
directory. The helper uses upstream `TOOLS_ONLY`, tests a localized JSON
fixture and refuses a missing input. It records archive, script and executable
hashes. This is a private build tool; target package features remain enabled.
Then build the ordinary `devel/kf6-kcmutils` package from the toolkit export.

On 2026-10-12 all ordinary package checks pass. The complete three-package
payload matches the common sysroot; installed checks cover 506 regular files
on CM5 Rev 1.0 / BCM2712 D0. The unmodified target `module_data_test` passes
3 QtTest cases, including generated cursor-theme and size defaults, in 11 ms.
Run its actual ELF binary from `_KDE_build/bin` with private HOME/XDG directories,
`QT_QPA_PLATFORM=offscreen` and a finite timeout. Do not run target tests on Mac.
The kernel and boot time stay unchanged. Interactive control-module loading,
window rendering and the full accelerated Plasma session remain unaccepted.

The KCMUtils package SHA256 is
`2b6f5e7329dafeb9b59e3867704e3269fec215b7e8249e597df2fcd8a395c29e`.
The original source SHA256 and full patches remain in the toolkit manifests.
These are AI-assisted EmberBSD build adaptations, not an upstream acceptance claim.
