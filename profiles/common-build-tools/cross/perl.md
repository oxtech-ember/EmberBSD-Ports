# Cross-building Perl 5.44 for the common stack

[Perl 5.44.0](https://dev.perl.org/perl5/) remains the current stable release
as checked on 2026-10-12. Its [release announcement](https://www.nntp.perl.org/group/perl.perl5.porters/2026/07/msg271063.html)
publishes the matching source SHA256.

The complete `lang/perl5` recipe supplies Perl 5.44.0nb3, its shared library,
threaded interpreter, XS modules, development headers and manuals. Clang's
installed scan-build programs depend on this target package. The build uses
macOS for compilation and an EmberBSD/AArch64 device for Configure probes.
It does not compile Perl on the device.

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
EMBERBSD_PERL_TARGET_HOST=private-ssh-alias
EMBERBSD_PERL_TARGET_USER=build-user
EMBERBSD_PERL_TARGET_DIR=/absolute/private-probe-directory
```

Use a connected target, an existing SSH account and a new writable probe
location. Configure runs small executables and transfers them through the
upstream SSH/SCP runner. Keep SSH credentials and connection configuration
outside Git. Use legacy SCP protocol where the target lacks an SFTP service.
A stable connection matters: a failed transport must not be interpreted as an
absent operating-system feature. Record SSH/SCP transport failures separately
and reject that Configure run; a successful package build alone is insufficient.
The accepted build recorded no transport failures and subsequently exercised
installed modules on the same board.

Run ordinary `bmake package` in the exported `lang/perl5` directory with the
private MAKECONF. Keep host and target package databases separate. Do not run
the target's ELF interpreter on macOS or replace failed target probes with host
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
for staging. Installed Config modules describe native GCC16, `/bin/sh` and
normal target tools, with cross transport and build-host paths removed. All
feature answers and configured ABI macros are preserved. Only tool-name macros
and build identity comments change in the installed copy of `CORE/config.h`.
The original build Config files remain untouched; the header keeps its
cross-build provenance. The converter rejects unknown remaining host paths.

## Checks

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
