# ngspice 47 packages

The common-graphics export updates `cad/ng-spice` and
`cad/ng-spice-shared` to the pinned ngspice 47 release.
Both packages retain XSPICE, CIDER, OSDI, KLU, OpenMP and FFTW.
The CLI retains GNU Readline and batch mode without the optional X11 UI.
KiCad supplies the schematic interface.

The shared package owns the installed C header, library, pkg-config file,
seven XSPICE code modules, Verilog integration modules and common scripts.
The CLI package depends on the matching version of that provider. It owns
the executable and manual. Both interfaces build their complete upstream
configuration; the CLI stage drops duplicate common files before packaging.
Normal packing-list checks remain enabled.

The recipes use normal pkgsrc compiler and Libtool wrappers. The common
cross profile supplies the GCC16 CRT and OpenMP metadata paths, target
runtime paths and the complete native compiler command for XSPICE `cmpp`.
Do not run a target `cmpp` on the build host. Do not invoke the cross-host
Libtool directly outside its pkgsrc wrapper environment.

The twelve source patches have one owner in the
[ngspice probe](../../../probes/kicad/ngspice/README.md).
The recipe links those exact files in their reviewed order. The exporter
verifies each link and checksum, then materializes regular patch files in
the exported recipe. The export needs no reference to the original checkout.
Source URLs and SHA256 are in [sources.tsv](../sources.tsv).
The recipe's `distinfo` also records the archive and patch checksums.
The upstream license inventory is installed with the shared package.

The source regression uses a complete exported tree and actual pkgsrc
metadata, checksum and patch targets. It compares the prepared source with
the reviewed probe, without building or installing packages:

```sh
BMAKE=/absolute/host/bin/bmake ruby profiles/common-graphics/tests/ngspice-source.rb \
    /absolute/export /absolute/cross.mk.conf \
    /absolute/ngspice-47.tar.gz /absolute/new-source-check
```

Build the shared package first and the CLI second with the normal pkgsrc
`package` target and the common cross configuration. Register accepted
packages through `pkg_add` before configuring KiCad. Use the installed
[C API and SPICE contracts](../../../probes/kicad/ngspice/tests)
for runtime acceptance. ELF linking and package creation alone do not
establish target execution.

The source preparation and native bootstrap results remain documented in
the probe. The ordinary GCC16 target packages and their EmberBSD runtime
acceptance are pending.
