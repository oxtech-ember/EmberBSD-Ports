# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native consumer of installed cross-built Perl.
use strict;
use warnings;
use ExtUtils::MakeMaker;
WriteMakefile(NAME => 'EmberProbe', VERSION => '0.01',
    XS => {'EmberProbe.xs' => 'EmberProbe.c'},
    PM => {'EmberProbe.pm' => '$(INST_LIB)/EmberProbe.pm'});
