# KiCad resource packages

Origin: NetBSD pkgsrc and KiCad contributors. EmberBSD integration is AI-assisted.

The four canonical recipes retain the official KiCad 10.0.7 library release.
`cad/kicad10` requires matching resource packages, with optional pkgsrc revisions.
The data packages do not depend on the application.

| Recipe | Installed resources |
| --- | --- |
| `cad/kicad-symbols` | Packed symbol libraries, simulation models, and `sym-lib-table` |
| `cad/kicad-footprints` | Footprints and `fp-lib-table` |
| `cad/kicad-templates` | Project and worksheet templates |
| `cad/kicad-packages3d` | Official STEP models |

The CMake projects declare `NONE`. They compile no target programs.
The symbols recipe retains default symbol packing. It uses the build-host
Python from `lang/python/tool.mk` through `Python3_EXECUTABLE`.
The upstream packer uses the Python standard library. It is not installed
as a target dependency. Keep `PYTHON_FOR_BUILD_ONLY=tool`.
Do not replace the packed table with the source table. The source table names
`.kicad_symdir` directories. The packed table names installed `.kicad_sym` files.
Both default tables use the `KICAD10_*` resource paths.

Each package installs its original `LICENSE.md` in `share/doc/PKGBASE`.
The data uses CC-BY-SA 4.0 with the upstream design-output exception.
Retain this exception and the attribution when redistributing the libraries.
Do not copy an unrelated package's license declaration.

The static PLISTs follow the tagged CMake install rules. The 3D release installs
STEP models. It does not install the optional `list_models` build target.
Normal staged package checks must compare the complete generated PLIST, archive,
file modes, and payload bytes. Validate all packed symbols and both library tables
with the installed KiCad version. Source checks do not prove a complete GUI/CAD
workflow, 3D rendering, or package lifecycle.

## Source provenance

All four releases use the `10.0.7` tag in the official
[KiCad library group](https://gitlab.com/kicad/libraries). The original archive
hashes and sizes are in each recipe's `distinfo`. The shared source index is
[common-graphics sources](../../../profiles/common-graphics/sources.tsv).
The original recipes come from the pinned pkgsrc base.
The current [NetBSD symbols recipe](https://github.com/NetBSD/pkgsrc/blob/trunk/cad/kicad-symbols/Makefile)
also uses a build-only Python tool.
The [FreeBSD library recipes](https://cgit.freebsd.org/ports/tree/cad/kicad-library-symbols)
provide an independent release/archive comparison.
The [OpenBSD application](https://github.com/openbsd/ports/blob/master/cad/kicad/Makefile)
also requires all four resource families.

## Source packer regression

Run the unchanged tagged packer with a new fixture directory:

```sh
python3.15 -B -E -S probes/kicad/application/tests/library-resources.py \
  --pack-script /absolute/kicad-symbols/tools/kicad_lib_pack.py \
  --expected-sha256 d8143432d68dac80f1ec55eaae52d774939ad4c43d96a8a7e28f1ad98ed5c75b \
  --work /absolute/new-fixture
```

The three cases check packed symbol order and exact table transport, malformed
library tables, and missing input. This test invokes the upstream CLI in the
same Python process. It supplies `sys.exit` for the upstream site-provided
`exit` helper when Python uses `-S`. It starts no child or target program.
