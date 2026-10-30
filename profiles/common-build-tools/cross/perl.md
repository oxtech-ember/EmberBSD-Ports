# Cross-building Perl 5.44 for the common stack

[Perl 5.44.0](https://dev.perl.org/perl5/) remains the current stable release
as checked on 2026-10-12. Its [release announcement](https://www.nntp.perl.org/group/perl.perl5.porters/2026/07/msg271063.html)
publishes the matching source SHA256.

The complete `lang/perl5` recipe supplies Perl 5.44.0nb9, its shared library,
threaded interpreter, XS modules, development headers and manuals. Clang's
installed scan-build programs depend on this target package. The build uses
macOS for compilation and a stored, target-measured Configure result for each
platform. An ordinary package build needs no target device.

## Reproducible inputs

The recipe retains pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b` authorship,
licences and portability patches, including its two upstream regexp fixes.
The original CPAN archive and both patch URLs/SHA256 are in
[the common manifest](../sources.tsv). The recipe owns all additional changes;
there is no second patch series to apply after export.

Prepare the [common cross configuration](README.md) and a fork-provenance
[sysroot](sysroot.md) with GCC 16.2. Build the same Perl 5.44.0 recipe natively
on macOS first, retaining its `miniperl` and `generate_uudmap` executables.
A full host Perl 5.44 is also needed for build scripts. Add to private MAKECONF:

```make
EMBERBSD_PERL_HOST_MINIPERL=/absolute/host-perl-source/miniperl
EMBERBSD_PERL_HOST_GENERATE=/absolute/host-perl-source/generate_uudmap
EMBERBSD_CROSS_BUILD_PERL=/absolute/host/bin/perl
EMBERBSD_PERL_HOST_PYTHON=/absolute/native/python3
```

These are build-host tools only. No target address, account or SSH tool is
needed.

## Stored Configure answers

Perl's Configure must run its feature probes on the target. They were run once
per platform on a real target, and the resulting `config.sh` is stored in
`pkgsrc/lang/perl5/files/config/${MACHINE_PLATFORM}.sh`. Every build-specific path
in it is an `@NAME@` placeholder (`WRKSRC`, `WRKDIR`, `SYSROOT`, `TOOLDIR`,
`TOOLBASE`, `HOST_MINIPERL`, `HOST_GENERATE`, `CROSS_BUILD_PERL`). Build-host
identity, configuration time and the probe target's address are removed.
The probe runner variables name `Cross/no-target`, which only reports an error.

For a cross build, `do-configure` fills the placeholders with the current
paths ([config-template.py](../../../pkgsrc/lang/perl5/files/config-template.py)
`fill`), runs `Configure -S` to extract the `.SH` files from those answers and
then `make depend`. No probe runs and no SSH or SCP is started.

The second line of each stored file names the recipe it was measured with:

```text
# pkgsrc recipe: perl-5.44.0 PKG_OPTIONS=perl-64bitauto,threads
```

The recipe refuses to build when the platform has no stored file or when the
recorded `DISTNAME` or sorted `PKG_OPTIONS` differ from the current build. Both
reasons appear in `PKG_FAIL_REASON` and point to this document.

| Platform | Measured on |
| --- | --- |
| `NetBSD-11.0-aarch64` | EmberBSD AArch64 board, Perl 5.44.0, 2026-10-29 |
| `NetBSD-11.0-x86_64` | EmberBSD amd64 laptop (Ninkear), Perl 5.44.0, 2026-10-30 |

### Capturing a new platform or Perl version

Capture again for each new `MACHINE_PLATFORM`, Perl version or option set.
This is the only step that uses a target. Add to a separate private MAKECONF:

```make
EMBERBSD_PERL_CAPTURE_CONFIG=yes
EMBERBSD_PERL_SSH=/absolute/host/ssh
EMBERBSD_PERL_SCP=/absolute/host/scp
# Optional dedicated configuration, e.g. for a disposable VM:
EMBERBSD_PERL_SSH_CONFIG=/absolute/private/ssh-config
EMBERBSD_PERL_TARGET_PORT=22 # or the selected VM forwarded port
EMBERBSD_PERL_TARGET_HOST=private-ssh-alias
EMBERBSD_PERL_TARGET_USER=build-user
EMBERBSD_PERL_TARGET_DIR=/absolute/private-probe-directory
```

Run `bmake configure` in `lang/perl5`. Configure then runs every probe on the
target, and post-configure writes the normalized template to
`${WRKDIR}/${MACHINE_PLATFORM}.sh` (`config-template.py capture`). Capture
refuses output that still contains a build-host path. Review it, copy it to
`files/config/`, add the platform to the table above and run the
[stored-config regression](../tests/perl-stored-config.py).

Use a connected target, an existing SSH account and a new private probe
location. Configure compiles each probe with the target compiler on the host.
Its runner copies executables, dynamic libraries and text fixtures to that
location. It runs small shell fixtures there, but no compiler on the target.
Keep SSH credentials and connection configuration outside Git.

The recipe's Python standard-library transport uses SSH BatchMode, a ten-second
connection timeout and a sixty-second deadline for each copy or run operation.
It uses legacy SCP protocol and rejects lexical path escapes. Create a fresh
private target directory and verify its parents are not symbolic links. The
transport does not provide remote filesystem isolation.
Use relative local SCP paths. They must not contain `:` or start with `-`,
including after path normalization. Ordinary `./try` and `fromtry.out` paths
remain valid. The transport rejects unsafe operands before it starts SCP.
A failed copy prevents execution of the probe. A transport failure leaves
`Cross/transport-failed`; later transport calls and the pkgsrc post-configure
check reject that run. Inspect the Configure log and correct the failure before
starting a fresh configure. An ordinary probe's nonzero exit status remains a
feature result. SSH status 255 and timeouts conservatively invalidate the run.
A client timeout does not certify that a remote process has exited. Inspect any
remaining probes before reusing the target directory.

The nonblocking-I/O shell fixture uses target-relative executable paths and
copies its output files back before Configure reads them. It does not embed
the build-host runner path in a script executed on the target.

## Building

Run ordinary `bmake package` in the exported `lang/perl5` directory with the
private MAKECONF. Keep host and target package databases separate. Do not run
the target's ELF interpreter on macOS or replace target answers with host
answers. The target triplet and `osname=netbsd` retain the fork's ABI naming.

## Portability fixes

Configure now executes its C99 and lchown probes through the target runner.
The lchown probe transfers its fixture source as well as its executable.
Architecture hints use the selected target and inspect both supported loader
locations inside the sysroot. They no longer disable shared libperl/dlopen
because macOS lacks the target ELF loader.

The experimental amd64 profile derives its target triplet and configured
Perl architecture from `MACHINE_ARCH=x86_64`. The installed metadata helper
accepts only the actual configured AArch64 or x86_64 threaded NetBSD ABI and
preserves its architecture and feature answers. Separate amd64 package and
runtime acceptance are required; the AArch64 results below do not cover it.

The generated primary makefile is `GNUmakefile`. On case-insensitive macOS,
upstream's removal of lowercase `makefile` otherwise also removes `Makefile`.
The build uses native GNU make and native Perl generators.

Errno generation preprocesses nested headers with public `errno.h` included.
This provides the prerequisite definitions for EmberBSD's private cdefs header;
compiler failure while reading those definitions now fails generation instead
of silently omitting errno constants.

The [metadata converter](../../../pkgsrc/lang/perl5/files/target-config.pl) runs only
for staging. Installed Config modules describe the native target Clang
(`/usr/pkg/bin/clang`), `/bin/sh`, the target make and normal target tools,
with cross transport and build-host paths removed. All
feature answers and configured ABI macros are preserved. Only tool-name macros
and build identity comments change in the installed copy of `CORE/config.h`.
The original build Config files remain untouched; the header keeps its
cross-build provenance. The converter rejects unknown remaining host paths.

## Selected Darwin search paths

Darwin Configure receives `locincpth` and `loclibpth` from the selected prefix
before its include/library probes. The canonical `lang/perl5/files/Policy.sh`
owns cleanup of `/usr/local/lib` from both `ldflags` and XS `lddlflags`; the
export infrastructure patch only supplies the Configure arguments and package
revision. It must not add a second copy of that callback block.

The [search-path regression](../../development-toolchain/tests/perl-darwin-search-paths.py)
accepts `CONFIGURE POLICY MAKEFILE SHELL UTILITY_BIN WORK`. Use the actual
exported recipe and patched upstream Configure. It executes the include-search
fragment and the complete substituted Policy.sh to generate `UU/pkgsrc.cbu`,
then runs that callback with flags supplied afterwards. A deliberate unescaped
backtick mutation must freeze the generation-time flags and fail. This checks the
shell generation boundary; installed Perl Config and XS build checks remain
separate.

## Selected Darwin install-name tool

For native Darwin, set `EMBERBSD_DARWIN_INSTALL_NAME_TOOL` to the selected
SDK executable. The recipe passes a defined value through quoted `MAKE_ENV`.
It does not substitute executable text into Perl source or installed Config.
`installperl` reads the environment only inside the existing Darwin shared
library guard. It accepts an absolute executable regular file, including a
symbolic link to one. An empty, relative, missing or non-executable selection
fails before dispatch. It does not fall back to `PATH` after an explicit choice.
An unset value keeps the ordinary upstream `install_name_tool` command.

The list-form call preserves each `-id` and `-change` operand, including paths
with spaces. A nonzero tool exit still fails installation. The NetBSD recipe
does not add this Darwin environment assignment or a new target dependency.
The existing `fix_dep_names` platform guard remains unchanged.

The [selection regression](../tests/perl-install-name-tool.py) takes the exported
Perl Makefile and patched upstream `installperl`:

```sh
python3 profiles/common-build-tools/tests/perl-install-name-tool.py \
    --makefile /absolute/export/lang/perl5/Makefile \
    --installperl /absolute/patched-perl/installperl
```

This command checks source contracts and rejects eleven deliberate mutations.
To execute the actual function, add `--perl /absolute/selected/perl` and
`--new-work /absolute/new-fragment-check` through the SDK owned-process runner.
The fixture supplies Config, verbosity, current directory and OS values.
Only the OS operand in the extracted function is parameterized. Recording
executables check both argument lists, explicit invalid choices, ordinary
unset selection, tool failure, symbolic links and inapplicable platform states.
The selected Perl path must fit a one-word shebang. The install-name tool and
operand paths include spaces and shell metacharacters. The fixture needs no
Perl modules. Source checks do not establish Perl execution or Make quoting;
fragment execution does not establish actual Mach-O rewriting or package
installation. Those checks remain separate.

The [MAKE_ENV regression](../tests/perl-install-name-env.py) runs the real
recipe clause with the complete accepted bmake tuple (`--make-arg` repeated
for each argument), `--makefile`, `--shell` and `--new-work`. The selected
shell checks its received environment. Seven cases check unset, empty,
space-containing and symbolic-link values on Darwin, and no assignment on
NetBSD. It executes neither Perl nor the install-name tool.

## Checks

The stored-config regression checks every stored file for neutral values and
its recipe identity, the capture/fill round trip, and refusal of unmapped
host paths and unknown placeholders. With `--bmake`, it also evaluates the
recipe: a cross build has no target requirement, a missing platform file or
identity mismatch fails with an explicit reason, and capture still requires
the target settings:

```sh
python3 profiles/common-build-tools/tests/perl-stored-config.py \
    --bmake /absolute/cross-bmake-wrapper -v
```

The transport regression uses fake process results and makes no SSH connection:

```sh
python3 profiles/common-build-tools/tests/perl-probe-transport.py \
    --configure /absolute/patched-perl/Configure -v
```

It checks failed-copy admission, SSH failure, timeout, sticky failure state,
path scope, fixture transfer and preservation of a genuine probe failure.
It also executes the actual generated wrappers and both native/cross branches
of the patched nonblocking-I/O shell fixture.


The [metadata regression](../tests/perl-target-config.sh) uses the real configured
source and upstream `configpm`. It checks the installed Config API, ABI macros,
unchanged source files and rejection of existing output or unknown host paths:

```sh
sh profiles/common-build-tools/tests/perl-target-config.sh \
    /absolute/configured-perl-source /absolute/sysroot \
    /absolute/host/bin/perl /absolute/new-metadata-test
```

For installed acceptance, extract these unchanged files from the verified
original Perl archive into a separate test tree, retaining their directories:

- `ext/Errno/t/Errno.t`
- `dist/threads/t/basic.t`
- `dist/IO/t/io_xs.t`
- `cpan/JSON-PP/t/001_utf8.t`
- `dist/Time-HiRes/t/usleep.t` and `dist/Time-HiRes/t/Watchdog.pm`

Copy the [runtime runner](run-perl-tests.sh), test tree and
[XS consumer](../tests/perl-xs) to the device. After installing the complete
package with ordinary pkg_add, execute:

```sh
sh /absolute/run-perl-tests.sh /absolute/upstream-tests /absolute/new-runtime-check
sh /absolute/perl-xs/run.sh /absolute/new-xs-check
```

The runner checks installed Config, Encode and SHA XS loading, then 74 upstream
assertions. It records executable/test hashes, dynamic libraries and unchanged boot time.
The XS consumer builds through installed ExtUtils::MakeMaker and CORE headers;
four assertions check integer width, dynamic loading and exception propagation.
This is a small acceptance consumer, not a native package build.

## Current boundary

On 2026-10-12 a clean macOS cross build of `perl-5.44.0nb3` passed normal
manifest, interpreter, permissions, PIE, RELRO, RPATH and work-reference checks.
It was imported into the common sysroot. Package SHA256:
`2b7f5c00ac5cbfc04429b442c2f9b7f9f640469cc9b4e2aefb2321fc2a01a9f6`.
The complete metadata regression also passed against that clean source.
The [Errno regression](../tests/perl-errno-generator.sh) executes the upstream
subroutine with the real cross GCC and the nested target cdefs header. It also
rejects a compiler returning partial definitions and exit 3. Both cases detect
the original source and pass with the port's patch.

The final nb3 package passed all 74 upstream assertions and four installed
XS-consumer assertions on CM5. Encode UTF-8 and Digest::SHA checks also passed.
The board kept the same boot time. Its installed interpreter SHA256 is
`e98145fa7c9e78ba4782f52c46302e3a07bbeaa7ecf8963694d8201efaddeb71`. The complete upstream Perl suite,
Valgrind and the complete QtTools/Plasma consumers remain unaccepted.

## Perl in other cross recipes

A `perl:run` cross recipe gets the target Perl as a run dependency on
`lang/perl5`. It is accepted when `lang/perl5` can build for the platform: a
stored `files/config/${MACHINE_PLATFORM}.sh` exists (or
`EMBERBSD_PERL_STORED_CONFIG` names one), capture mode is on, or a target Perl
is already staged in the sysroot. The decision does not wait for the staged
Perl, because a bulk fetch and the first parse of a build run before the
dependency is installed. Without any of these the recipe is refused with
`USE_TOOLS+=perl:run not supported in cross-compilation`.
[`tests/cross-perl-run-unstaged.py`](../tests/cross-perl-run-unstaged.py)
checks both cases on six real recipes against a sysroot without a staged Perl:

```sh
/absolute/ports-python3 -B profiles/common-build-tools/tests/cross-perl-run-unstaged.py \
    --pkgsrc /absolute/pkgsrc --makeconf /absolute/cross-mk.conf \
    --sysroot /absolute/sysroot --work /absolute/new-test-dir --bmake /absolute/bmake-command
```

For such a recipe the
tools wrapper, `TOOLS_PERL5` and configure `PERL` still run the build host's
Perl. Only `PERL5`, and so `REPLACE_PERL`, names the target `/usr/pkg/bin/perl`
for installed scripts. The [evaluation test](../tests/cross-perl-tools.sh)
checks both sides on `devel/automake`:

```sh
BMAKE=/absolute/bmake-command sh profiles/common-build-tools/tests/cross-perl-tools.sh \
    /absolute/pkgsrc /absolute/cross-mk.conf /absolute/new-test-dir
```
