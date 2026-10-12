# Preserve Frameworks Designer plugins in cross packages

Ten Frameworks 6.31 recipes inherited a CMake option that disabled Designer
plugins during cross compilation. Their package manifests still required the
plugins. The recipes now use the ordinary default-on option already used by
upstream KIO 6.31. Explicit `BUILD_DESIGNERPLUGIN=OFF` remains possible in a
custom build; the full package keeps the manifest and its required plugin.

```sh
CMAKE=/absolute/cmake ruby ../tests/designer-options.rb \
    /absolute/distfiles /absolute/new-option-check
```

The source check verifies all eleven providers' original archive hashes.
It applies the ten patches with zero fuzz, rejects repeated application,
and evaluates actual CMake option lines for native, cross and explicit-off
cases. This is a source/configuration check for the full set.

KWidgetsAddons, KConfigWidgets and KCompletion additionally passed full GCC16
cross-package checks on 2026-10-12. Their actual installed AArch64 plugins
link Qtbase and Frameworks. QtTools is retained as a build dependency for
Designer headers. Runtime dependencies do not unnecessarily install QtTools.
KConfigWidgets also removes an obsolete Perl dependency: upstream 6.31 no
longer includes the former `preparetips6` script.

```sh
BMAKE=/absolute/bmake CMAKE=/absolute/cmake \
KF6_WIDGET_COMPONENT=kconfigwidgets ruby ../tests/widgets-plugin.rb \
    /absolute/pkgsrc /absolute/cross.mk /absolute/configured-source \
    /absolute/sysroot /absolute/aarch64-readelf /absolute/new-check
```

The component can be `kwidgetsaddons`, `kconfigwidgets` or `kcompletion`.
This check reproduces the previous cross exclusion, verifies the native
default, queries actual dependency classes, and inspects the installed plugin.
The [KWidgetsAddons CM5 tests](models-and-jobs.md#widget-apis-and-the-designer-plugin)
remain the earlier runtime evidence. KConfigWidgets/KCompletion runtime,
Designer loading, and other providers' full packages are not established by
this source check. No C/C++ source changed in these option patches.

| Package | SHA256 |
| --- | --- |
| kf6-kconfigwidgets-6.31.0nb1.tgz | `52997eb0f21334b41aa785f866b2c758adaf21a34a0b147d21d71c17d2f15a4f` |
| kf6-kcompletion-6.31.0nb1.tgz | `16d2b2f2b665307527f977750f4ecfb0ed2266e0256d11bb55ef0e3a4d40769a` |
