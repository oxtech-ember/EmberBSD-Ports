#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Upstream status: not submitted.
"""Check Darwin host Perl selectors for a NetBSD build context."""
import argparse
import os
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--perl', required=True)
p.add_argument('--build-config', required=True)
p.add_argument('--perl5lib', help='staged host Perl libraries, for pre-install testing')
a = p.parse_args()
code = ('use ExtUtils::MM; use ExtUtils::CBuilder; use Errno; '
        'print join(q{,}, $^O, $ExtUtils::MM::ISA[0], $ExtUtils::CBuilder::ISA[0]);')
env = dict(os.environ)
env.pop('EMBERBSD_PERL_BUILD_CONFIG', None)
if a.perl5lib:
    env['PERL5LIB'] = a.perl5lib
else:
    env.pop('PERL5LIB', None)
native = subprocess.check_output([a.perl, '-e', code], env=env, text=True).strip()
assert native == 'darwin,ExtUtils::MM_Darwin,ExtUtils::CBuilder::Platform::darwin', native
env['EMBERBSD_PERL_BUILD_CONFIG'] = a.build_config
target = subprocess.check_output([a.perl, '-e', code], env=env, text=True).strip()
assert target == 'darwin,ExtUtils::MM_Unix,ExtUtils::CBuilder::Platform::Unix', target
print('Perl native and target build selectors: PASS')
