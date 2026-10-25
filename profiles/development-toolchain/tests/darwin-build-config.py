#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the Darwin GCC16 build configuration with real Mach-O objects.

GCC's bootstrap-debug compares -g0 and -g objects after stripping debug
information. The selected llvm-strip -S keeps Mach-O section addresses, so
__eh_frame moves when GCC emits __debug_frame first. The recipe must pass
--without-build-config. Run on Darwin with a patched GCC 16.2 source tree:

  python3 -B darwin-build-config.py --gcc-source SRC --cc GCC --cxx G++ \
      --llvm-bin DIR --math-prefix PREFIX --shell MKSH --work NEW_WORK
"""

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
PROFILE = Path(__file__).resolve().parents[1]
RECIPE = PROFILE / 'patches/gcc-darwin-host.patch'
PROBE = 'int f (void) { return 0; }\n'
MESSAGE = 'selected Darwin bootstrap-debug comparison failed'


def run(command, cwd, env, check=True):
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and result.returncode:
        sys.stderr.write(result.stdout[-4000:])
        raise SystemExit('FAIL: ' + ' '.join(map(str, command)))
    return result


def recipe_build_config():
    """Return the Darwin build-config arguments the recipe adds."""
    words = []
    for line in RECIPE.read_text().splitlines():
        if line.startswith('+CONFIGURE_ARGS+='):
            words += [w for w in line.split()[1:] if 'build-config' in w]
    return words


def sections(objdump, path, env):
    out = run([objdump, '--section-headers', str(path)], path.parent, env).stdout
    table = {}
    for line in out.splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[0].isdigit():
            table[fields[1]] = int(fields[3], 16)
    return table


def mach_o_probe(args, env, work):
    """The configure probe fails only because __eh_frame moved."""
    tools = {name: str(args.llvm_bin / ('llvm-' + name)) for name in ('strip', 'objdump', 'objcopy')}
    (work / 'conftest.c').write_text(PROBE)
    cc = shlex.split(args.cc)
    for flag, name in (([], 'conftest.o.g0'), (['-g'], 'conftest.o.g')):
        run(cc + flag + ['-c', 'conftest.c', '-o', name], work, env)
    header = (work / 'conftest.o.g').read_bytes()[:4]
    assert header == b'\xcf\xfa\xed\xfe', 'not a 64-bit Mach-O object'
    probe_env = dict(env, GCC_COMPARE_DEBUG_STRIP=tools['strip'],
                     GCC_COMPARE_DEBUG_OBJDUMP=tools['objdump'],
                     GCC_COMPARE_DEBUG_OBJCOPY=tools['objcopy'])
    result = run([str(args.shell), str(args.gcc_source / 'contrib/compare-debug'), '-p',
                  'conftest.o.g0', 'conftest.o.g'], work, probe_env, check=False)
    print('selected compare-debug status', result.returncode)
    assert result.returncode != 0, 'the selected probe now passes; revisit --without-build-config'
    g0, g = (sections(tools['objdump'], work / (n + '.stripped'), env) for n in ('conftest.o.g0', 'conftest.o.g'))
    assert set(g0) == set(g) and '__eh_frame' in g, (g0, g)
    assert g0['__eh_frame'] != g['__eh_frame'], 'the difference is not the __eh_frame address'
    dumps = []
    for name in ('conftest.o.g0', 'conftest.o.g'):
        out = work / (name + '.eh_frame')
        run([tools['objcopy'], '--dump-section', '__TEXT,__eh_frame=' + str(out),
             name + '.stripped', str(work / (name + '.copy'))], work, env)
        dumps.append(out.read_bytes())
    assert dumps[0] == dumps[1], '__eh_frame contents differ'
    print('__eh_frame address %#x -> %#x, same %d bytes' % (g0['__eh_frame'], g['__eh_frame'], len(dumps[0])))
    return probe_env


def configure(args, env, build, extra):
    build.mkdir()
    math = str(args.math_prefix)
    command = [str(args.shell), str(args.gcc_source / 'configure'), '--enable-languages=c,c++',
               '--with-gmp=' + math, '--with-mpfr=' + math, '--with-mpc=' + math,
               '--without-isl', '--disable-multilib'] + extra
    result = run(command, build, env, check=False)
    print('configure', extra or ['(no build-config argument)'], 'status', result.returncode)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('gcc-source', 'llvm-bin', 'math-prefix', 'shell', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--cc', required=True, help='native Darwin GCC16 command')
    parser.add_argument('--cxx', required=True, help='native Darwin G++16 command')
    args = parser.parse_args()
    for path in (args.gcc_source, args.llvm_bin, args.math_prefix, args.shell, args.work):
        assert path.is_absolute(), path
    assert os.uname().sysname == 'Darwin', 'needs real Mach-O objects'
    assert (args.gcc_source / 'contrib/compare-debug').read_text().count('GCC_COMPARE_DEBUG_STRIP') > 0
    args.work.mkdir()
    env = {'HOME': os.environ.get('HOME', '/'), 'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}
    probe_env = mach_o_probe(args, env, args.work)
    probe_env.update(CC=args.cc, CXX=args.cxx, SHELL=str(args.shell), CONFIG_SHELL=str(args.shell))
    control = configure(args, probe_env, args.work / 'build-default', [])
    assert control.returncode != 0 and MESSAGE in control.stdout, 'the default route no longer fails'
    extra = recipe_build_config()
    assert extra == ['--without-build-config'], 'recipe build-config arguments: %r' % extra
    fixed = configure(args, probe_env, args.work / 'build-recipe', extra)
    assert fixed.returncode == 0, fixed.stdout[-3000:]
    assert 'checking for default BUILD_CONFIG... \n' in fixed.stdout, 'BUILD_CONFIG is not empty'
    makefile = (args.work / 'build-recipe/Makefile').read_text()
    assert re.search(r'^BUILD_CONFIG = *$', makefile, re.M), 'Makefile selects a build config'
    assert re.search(r'^do-compare = cmp ', makefile, re.M), 'stage comparison command missing'
    assert re.search(r'^compare:$', makefile, re.M), 'stage 2/3 compare target missing'
    print('PASS: Darwin GCC16 configures without bootstrap-debug and keeps the stage comparison')


if __name__ == '__main__':
    main()
