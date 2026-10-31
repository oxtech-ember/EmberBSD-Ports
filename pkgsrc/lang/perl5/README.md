# Perl module cross builds

The pkgsrc Perl module paths can build for a target with a matching Perl
installed in the selected sysroot. Set `EMBERBSD_PERL_TARGET_CONFIG` to its
installed `Config.pm` and `EMBERBSD_CROSS_BUILD_PERL` to the selected native
Perl of the same version. The native interpreter and its XS modules remain
native. A separate build context supplies the target configuration and the
selected compiler wrappers; target install paths remain target paths.

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
