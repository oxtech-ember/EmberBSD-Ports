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
Set optimization and debug flags in `MAKECONF`. Passing `CFLAGS` on the make
command line overrides the language and OpenMP flags added by `configure`.
Check actual compile commands and `_OPENMP`, not only `USE_OMP` in config.h.

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

The [OpenMP workload](../../../probes/kicad/ngspice/tests/openmp-contract.sh)
uses the exact upstream `examples/mos/nmos_pmos_BSIM482.sp` circuit.
The preserved fixture and upstream COPYING file are next to the script.
Its SHA256 is `817b8ed1a1879fce346a1750268fbca0005e759a68fa1d41204fcbf3c3f38ecb`.
The script replaces interactive controls with one DC sweep, file output and
explicit one/two-thread selection. Device and model definitions stay unchanged.
Run it on EmberBSD with the installed CLI and base `ktrace`, `kdump` and `sha256`:

```sh
sh probes/kicad/ngspice/tests/openmp-contract.sh \
    /usr/pkg/bin/ngspice /absolute/new-openmp-check
```

The check compares 31 DC points within a stated absolute/relative tolerance.
It also requires more successful `_lwp_create` calls in the two-thread run.
This tests parallel activation and numerical agreement, not an independent
analytic solution for BSIM4. The divider remains the known-answer circuit.
The ordinary GCC 16.2.0 AArch64 packages passed installation, removal and
reinstallation in the E34 EmberBSD guest. All 37 installed payload entries
match their package stages. The C API passed 18 checks, including the divider,
XSPICE gain, rejected input, circuit switching, reset and controlled exit.
The CLI passed repeated-input and malformed-vector checks. An actual KiCad
10.0.7 exported circuit produced 5 V, 2.5 V and -2.5 mA; its checker rejected 3 V.
The BSIM workload passed all 31 points. Successful worker creation increased
from zero to one between the one-thread and two-thread runs.
The loaded API/CLI providers match the compiler SDK, including GCC16 libgomp.

The accepted shared archive has SHA256
`3bc665c463ee4ccf2aa55a724df8c8992ec48525e91c0c2435e076eb1c802a73`.
The CLI archive has SHA256
`1eb7c16f545a08ccb7e0fed797f3e816744d44a3a89402f9354dcc6d09f26444`.
An earlier private invocation overrode configure's OpenMP flags; that package
was superseded before runtime acceptance. Actual accepted compile commands
define `_OPENMP=202111`, and both interfaces import `GOMP_parallel`.

The current configure check incorrectly detects the build host's `/proc/meminfo`.
The target emits that missing-file diagnostic during memory queries; numerical
checks still pass. This portability issue remains open. Target memory analysis,
complete CIDER/OSDI/KLU workflows and KiCad application integration remain pending.
The source and native analysis limits remain documented in the probe.
