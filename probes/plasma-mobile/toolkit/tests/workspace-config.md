# Workspace configuration lifecycle

Workspace 6.8.0nb2 declares `xdg/menus` in `MAKE_DIRS`.
Its `CONF_FILES` menu must have a parent directory on a fresh installation.
The pkgsrc helpers create the directory before copying the menu.
They retain a locally edited menu during removal and reinstallation.

Run the regression with the real generated `+INSTALL` and packaged examples.
Use a trusted Workspace package and a new extraction directory:

```sh
mkdir /absolute/new-workspace-config
bsdtar -xzf /absolute/plasma6-plasma-workspace-6.8.0nb2.tgz \
    -C /absolute/new-workspace-config +INSTALL 'share/examples/kde-xdg/*'
ruby probes/plasma-mobile/toolkit/tests/workspace-config.rb \
    /absolute/new-workspace-config/+INSTALL /absolute/new-workspace-config
```

The test invokes the unmodified generated `+DIRS` and `+FILES` helpers.
It uses their `PKG_PREFIX` and reference-count database overrides.
All writes use a temporary directory. Absolute configuration paths are rejected.
The test checks default contents, permissions, removal, reinstallation and edited-menu preservation.
It verifies the files directly because a helper can return zero after a copy error.
The old nb1 script fails when it copies the menu into the absent directory.

For a pre-build check, run the recipe's `generate-install-scripts` target.
Pass its generated `.pkgdb/+INSTALL` and matching package examples to the same test.
This host check does not run target ELF programs, desktop cache hooks or `pkg_add`.
The complete target installation and Plasma session require separate acceptance.
No C/C++ source changes in this repair. Compiler analyzers and Valgrind are not claimed.

For unchanged accepted payloads, use the [metadata refresh workflow](../cross/metadata-refresh.md)
to regenerate package scripts without another C++ compilation.
