# Perl module cross builds

The pkgsrc Perl module paths can build for a target with a matching Perl
installed in the selected sysroot. Set `EMBERBSD_PERL_TARGET_CONFIG` to its
installed `Config.pm` and `EMBERBSD_CROSS_BUILD_PERL` to the selected native
Perl of the same version. The native interpreter and its XS modules remain
native. A separate build context supplies the target configuration and the
selected compiler wrappers; target install paths remain target paths.

Cross packages that need Perl only as a build tool and do not select
`EMBERBSD_PERL_TARGET_CONFIG` query the native interpreter's configuration.
They accept its relocatable `prefix` through the matching absolute
`installprefix`, just as native builds do. Explicit target configuration still
requires an absolute target prefix and keeps the installation-path checks.

This covers `PERL5_MODULE_TYPE` `MakeMaker`, `Module::Install`,
`Module::Install::Bundled`, `Module::Build` and `Module::Build::Tiny`. The
packaged Module::Build (`devel/p5-Module-Build`) reads the same build context
and selects its platform layer from the target `osname`. Module::Build::Tiny
reads it through the packaged ExtUtils::Config and ExtUtils::Helpers, which
use `ExtUtils::MakeMaker::Config`. `Build.PL` and `Build` run with the native
Perl. `Module::Build::Bundled` uses another copy of the build system and is
refused for cross builds. A module that executes a target program during
configuration still needs a target execution mechanism. Build success alone
does not establish target runtime behavior.

## Native Darwin SDK prefixes

Native Darwin builds select upstream executable-relative include directories
while retaining shared libperl. The build/install Mach-O name remains absolute;
the SDK portable-package producer must make its load commands relative before
publishing a movable package. Other host and cross configurations retain their
existing selection.

A selected runtime shell next to the Perl executable is resolved with Perl's
own path relocation code. During the uninstalled build, the explicit
`PERL_BUILD_SHELL` selects the current build shell for both the full interpreter
and miniperl. The cross recipe also supplies it when the build tree executes native
miniperl through a symlink or copy. An installed miniperl resolves its
shell relative to its versioned `libexec/perl5` directory. The shared `PL_sh_path` symbol is unchanged.
Package configuration scripts run after textual prefix relocation through the
SDK's qualified deferred-hook contract.

Check a packaged installation at a new prefix with
`profiles/common-build-tools/tests/perl-relocation.py --prefix PATH
--producer-prefix ORIGINAL --deny-producer` (Darwin). It loads core and XS
modules, checks Config and include paths, and invokes the selected shell while
reads from the original prefix are denied. A successful build alone does not
establish these relocation properties.
