#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise Perl package paths for relocatable, native and cross Config."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ports = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bmake', required=True)
p.add_argument('--makefiles', required=True)
p.add_argument('--perl', required=True)
a = p.parse_args()
keys = ('installarchlib', 'installscript', 'installvendorbin', 'installvendorscript',
        'installvendorarch', 'installvendorlib', 'installvendorman1dir', 'installvendorman3dir')
with tempfile.TemporaryDirectory(prefix='perl-vars-prefix-') as tmp:
    root = Path(tmp)
    recipe = root / 'lang/perl5'
    recipe.mkdir(parents=True)
    (root / 'mk').mkdir()
    (root / 'mk/bsd.prefs.mk').write_text('')
    shutil.copy2(ports / 'pkgsrc/lang/perl5/vars.mk', recipe / 'vars.mk')
    (recipe / 'Makefile').write_text('.include "vars.mk"\n')
    def query(prefix, installprefix, cross=False, bad=None, target_config=True):
        rows = ['prefix=' + prefix, 'installprefix=' + installprefix]
        rows += [key + '=' + (bad if key == 'installvendorlib' and bad else '/producer/lib/' + key)
                 for key in keys]
        command = [a.bmake, '-m', a.makefiles, '-C', str(recipe), 'PERL5=' + a.perl,
                   'PREFIX=/selected', '_PERL5_VARS_OUT=' + ' '.join(rows)]
        if cross:
            command += ['USE_CROSS_COMPILE=yes']
            if target_config:
                command += ['EMBERBSD_PERL_TARGET_CONFIG=/target/Config.pm']
        command += ['-V', '${PERL5_SUB_INSTALLVENDORLIB}', '-V', '${PERL5_INSTALLVENDORLIB}']
        return subprocess.run(command, capture_output=True, text=True)
    for prefix, installprefix, cross, target_config in (
            ('.../..', '/producer', False, False),
            ('/producer', '/producer', False, False),
            ('/producer', '/unused', True, True),
            ('.../..', '/producer', True, False)):
        result = query(prefix, installprefix, cross, target_config=target_config)
        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == ['lib/installvendorlib', '/selected/lib/installvendorlib']
    for cross in (False, True):
        command = [a.bmake, '-m', a.makefiles, '-C', str(recipe), 'PERL5=' + a.perl,
                   'PREFIX=/selected', '-V', '${PERL5_SUB_INSTALLVENDORLIB}']
        if cross:
            command += ['USE_CROSS_COMPILE=yes']
        real = subprocess.run(command, capture_output=True, text=True)
        assert real.returncode == 0, real.stderr
        assert real.stdout.strip().startswith('lib/perl5/'), real.stdout
    # Explicit target metadata must not borrow the native relocation fallback.
    result = query('.../..', '/producer', cross=True)
    assert result.returncode != 0 and 'absolute Perl installation prefix' in result.stderr, result.stderr
    for bad in ('/outside/installvendorlib', '/producer-other/installvendorlib', 'relative/path'):
        result = query('.../..', '/producer', bad=bad)
        assert result.returncode != 0 and 'outside its installation prefix' in result.stderr, result.stderr
    result = query('.../..', 'relative')
    assert result.returncode != 0 and 'absolute Perl installation prefix' in result.stderr, result.stderr
print('PASS: relocatable, ordinary, cross and malformed Perl Config paths')
