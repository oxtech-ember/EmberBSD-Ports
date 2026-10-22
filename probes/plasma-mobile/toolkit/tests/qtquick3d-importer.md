# QtQuick3D optional model importer

The QtQuick3D 6.12.0nb2 recipe exposes an `assimp` package option. Its
default remains enabled. The ordinary package retains its existing model
import behavior and Assimp dependency.

An explicit reduced-feature package can omit that dependency:

```make
PKG_OPTIONS.qt6-qtquick3d= -assimp
```

The recipe passes `-DFEATURE_quick3d_assimp:BOOL=OFF` through the module's
CMake argument list. Qt's core libraries remain enabled. The Assimp plugin
and its seven CMake metadata files are omitted from the package manifest.
Clean an existing work directory after changing the option, since pkgsrc
retains its previously calculated dependency list.

This option also removes runtime OBJ/glTF/GLB import through
`QQuick3DRuntimeLoader`. Its importer reports unsupported formats; the
Quick3D rendering engine remains a separate module. Applications that need
external model import must retain the default option and audit Assimp.
The option does not repair Assimp itself or suppress its advisories.

The native EmberBSD/amd64 GCC16 package with `-assimp` passes ordinary
staging checks and installation. `pkg_admin check` verifies all 1237 files.
The configure summary reports both Assimp and System Assimp disabled, and
the installed rendering-library dependencies contain no Assimp library.
Real Quick3D scenes, RuntimeLoader behavior and SpatialAudio execution are
not accepted by these package checks. They require separate consumers.

Run the actual pkgsrc metadata check for default and explicit selections:

```sh
python3 probes/plasma-mobile/toolkit/tests/quick3d-assimp-option.py \
    /absolute/prepared-pkgsrc --makeconf /absolute/mk.conf
```

The check covers dependency selection, the CMake boolean, eight conditional
plugin files and the unchanged unconditional core-library manifest entries.
