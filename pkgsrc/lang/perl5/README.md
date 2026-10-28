# Perl module cross builds

The pkgsrc MakeMaker module path can build for a target with a matching Perl
installed in the selected sysroot. Set `EMBERBSD_PERL_TARGET_CONFIG` to its
installed `Config.pm` and `EMBERBSD_CROSS_BUILD_PERL` to the selected native
Perl of the same version. The native interpreter and its XS modules remain
native. A separate build context supplies the target configuration and the
selected compiler wrappers; target install paths remain target paths.

This path currently supports `PERL5_MODULE_TYPE=MakeMaker`; other module build
systems require their own cross integration. A module that executes a target
program during configuration still needs a target execution mechanism. Build
success alone does not establish target runtime behavior.
