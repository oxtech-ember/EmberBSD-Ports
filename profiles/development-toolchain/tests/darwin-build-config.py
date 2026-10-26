#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the Darwin GCC16 build configuration with real Mach-O objects.

GCC's bootstrap-debug compares -g0 and -g objects after stripping debug
information. The selected llvm-strip -S keeps Mach-O section addresses, so
__eh_frame moves when GCC emits __debug_frame first. The recipe must pass
--without-build-config. Run on Darwin with a patched GCC 16.2 source tree:

  SDK_PYTHON -B darwin-build-config.py --sdk-source SDK_SOURCE \
      --descriptor JSON --descriptor-sha256 SHA256 \
      --producer-receipt JSON --producer-receipt-sha256 SHA256 \
      --tools-bin SDK_BIN --gcc-source SRC --math-prefix PREFIX --work NEW_WORK

Use an accepted ordinary native toolset. Bootstrap seed evidence is insufficient.
The descriptor owns GCC16, its driver closure, ABI flags and every utility.
SDK_BIN must contain the selected utility paths under their exact command names.
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
CONFIGURE_FILES = tuple((PROFILE / 'patches/gcc-sdk-configure-diagnostics.files').read_text().splitlines())
DIAGNOSTIC_HELPER = 'config/emberbsd-sdk-diagnostics.sh'
DIAGNOSTIC_SOURCE = (Path(__file__).resolve().parents[2] /
    'common-build-tools/files/emberbsd-configure-diagnostics.sh').read_text()

# configure and compare-debug use these bare names. Each must resolve to its
# admitted role in one explicit SDK directory. Compiler and LLVM paths are direct.
PATH_ROLES = ('sh', 'make', 'awk', 'basename', 'cat', 'chmod', 'cmp', 'cp', 'cut',
              'date', 'diff', 'dirname', 'expr', 'grep', 'head', 'hostname', 'install', 'ln', 'ls', 'mkdir',
              'mktemp', 'mv', 'printf', 'rm', 'rmdir', 'sed', 'sort', 'tail', 'touch', 'tr', 'uname', 'uniq', 'wc')
REQUIRED_ROLES = ('cc', 'cxx', 'cpp', 'as', 'ld', 'ar', 'ranlib', 'nm', 'strip',
                  'objdump', 'objcopy', 'python', *PATH_ROLES)


def selected_inputs(args):
    """Admit pinned SDK bytes before output creation or any compiler child."""
    from emberbsd_sdk.errors import SDKError
    from emberbsd_sdk.native_toolset import NATIVE_TOOLSET_API, load_native_toolset
    selectors = (args.descriptor, args.descriptor_sha256,
                 args.producer_receipt, args.producer_receipt_sha256)
    if not all(selectors):
        raise SDKError('Set the descriptor and producer receipt paths and SHA256 pins')
    if type(NATIVE_TOOLSET_API) is not int or NATIVE_TOOLSET_API != 1:
        raise SDKError('SDK native toolset API 1 is required')
    selected = load_native_toolset(args.descriptor,
        descriptor_sha256=args.descriptor_sha256,
        accepted_producer_receipt=dict(path=args.producer_receipt, sha256=args.producer_receipt_sha256),
        required_roles=REQUIRED_ROLES)
    if selected.host['os'] != 'Darwin':
        raise SDKError('This probe requires an accepted native Darwin GCC16 toolset')
    directory = args.tools_bin
    if not directory.is_absolute() or not directory.is_dir() or ':' in str(directory):
        raise SDKError('Use one absolute selected SDK tool directory')
    for role in REQUIRED_ROLES:
        if role not in selected.tools:
            raise SDKError('Missing selected SDK role: ' + role)
        path = Path(selected.tool(role))
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise SDKError('Missing executable SDK role: ' + role)
        if role in PATH_ROLES and path != directory / role:
            raise SDKError('SDK PATH role differs from the selected directory: ' + role)
    admitted = set(selected.tools.values())
    if any(str(path) not in admitted for path in directory.iterdir()):
        raise SDKError('Every SDK PATH entry must be an explicitly selected tool')
    if Path(sys.executable).resolve(strict=True) != Path(selected.tool('python')).resolve(strict=True):
        raise SDKError('The controller must use the selected SDK Python')
    flags = selected.abi_flags
    env = dict(PATH=str(directory), HOME=str(args.work), TMPDIR=str(args.work), LC_ALL='C', TZ='UTC',
               SHELL=selected.tool('sh'), CONFIG_SHELL=selected.tool('sh'), CONFIG_SITE='/dev/null',
               GCC_CONFIGURE_SDK='yes', GCC_CONFIGURE_UNAME=selected.tool('uname'))
    for key, role in (('CC', 'cc'), ('CXX', 'cxx'), ('CPP', 'cpp'), ('AS', 'as'), ('LD', 'ld'),
                      ('AR', 'ar'), ('RANLIB', 'ranlib'), ('NM', 'nm'), ('STRIP', 'strip'),
                      ('OBJDUMP', 'objdump'), ('OBJCOPY', 'objcopy'), ('MAKE', 'make'),
                      ('AWK', 'awk'), ('SED', 'sed'), ('GREP', 'grep'), ('INSTALL', 'install')):
        env[key] = shlex.join([selected.tool(role)])
    env['EGREP'] = shlex.join([selected.tool('grep'), '-E'])
    env['FGREP'] = shlex.join([selected.tool('grep'), '-F'])
    for key in ('cppflags', 'cflags', 'cxxflags', 'ldflags'):
        env[key.upper()] = shlex.join(flags[key])
    return selected, env



def check_configure_source(source):
    """Check every canonical generated configure before any compiler child."""
    from emberbsd_sdk.errors import SDKError
    try:
        helper = (source / DIAGNOSTIC_HELPER).read_text()
        if helper != DIAGNOSTIC_SOURCE:
            raise SDKError('Use the common Ports SDK configure diagnostic helper')
        for name in CONFIGURE_FILES:
            text = (source / name).read_text()
            for program in ('/usr/bin/uname', '/bin/uname', '/bin/arch', '/usr/bin/arch',
                            '/usr/convex/getsysinfo', '/usr/bin/hostinfo', '/bin/machine',
                            '/usr/bin/oslevel', '/bin/universe'):
                if '`(' + program in text:
                    raise SDKError(name + ' still executes an unselected diagnostic tool: ' + program)
            relative = '../' * (len(Path(name).parts) - 1) + DIAGNOSTIC_HELPER
            if ('. "${srcdir}/' + relative + '" || exit 1') not in text:
                raise SDKError(name + ' lacks the common selected SDK diagnostic entry')
    except OSError as error:
        raise SDKError('Incomplete common GCC configure source: ' + str(error)) from error


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


def mach_o_probe(args, selected, env, work):
    """The configure probe fails only because __eh_frame moved."""
    tools = {name: selected.tool(name) for name in ('strip', 'objdump', 'objcopy')}
    (work / 'conftest.c').write_text(PROBE)
    cc = [selected.tool('cc'), *selected.abi_flags['cppflags'], *selected.abi_flags['cflags']]
    for flag, name in (([], 'conftest.o.g0'), (['-g'], 'conftest.o.g')):
        run(cc + flag + ['-c', 'conftest.c', '-o', name], work, env)
    header = (work / 'conftest.o.g').read_bytes()[:4]
    assert header == b'\xcf\xfa\xed\xfe', 'not a 64-bit Mach-O object'
    probe_env = dict(env, GCC_COMPARE_DEBUG_STRIP=tools['strip'],
                     GCC_COMPARE_DEBUG_OBJDUMP=tools['objdump'],
                     GCC_COMPARE_DEBUG_OBJCOPY=tools['objcopy'])
    result = run([selected.tool('sh'), str(args.gcc_source / 'contrib/compare-debug'), '-p',
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


def configure(args, selected, env, build, extra):
    build.mkdir()
    math = str(args.math_prefix)
    command = [selected.tool('sh'), str(args.gcc_source / 'configure'), '--enable-languages=c,c++',
               '--with-gmp=' + math, '--with-mpfr=' + math, '--with-mpc=' + math,
               '--without-isl', '--disable-multilib',
               '--build=' + selected.compiler['triplet'],
               '--host=' + selected.compiler['triplet']] + extra
    result = run(command, build, env, check=False)
    print('configure', extra or ['(no build-config argument)'], 'status', result.returncode)
    return result


def main(argv=None):
    sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
    import sdk_source
    arguments = sdk_source.arguments(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('gcc-source', 'tools-bin', 'math-prefix', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('descriptor', 'descriptor-sha256', 'producer-receipt', 'producer-receipt-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(arguments)
    selected, env = selected_inputs(args)
    check_configure_source(args.gcc_source)
    for path in (args.gcc_source, args.tools_bin, args.math_prefix, args.work):
        assert path.is_absolute(), path
    assert os.uname().sysname == 'Darwin', 'needs real Mach-O objects'
    assert (args.gcc_source / 'contrib/compare-debug').read_text().count('GCC_COMPARE_DEBUG_STRIP') > 0
    args.work.mkdir()
    probe_env = mach_o_probe(args, selected, env, args.work)
    control = configure(args, selected, probe_env, args.work / 'build-default', [])
    assert control.returncode != 0 and MESSAGE in control.stdout, 'the default route no longer fails'
    extra = recipe_build_config()
    assert extra == ['--without-build-config'], 'recipe build-config arguments: %r' % extra
    fixed = configure(args, selected, probe_env, args.work / 'build-recipe', extra)
    assert fixed.returncode == 0, fixed.stdout[-3000:]
    assert 'checking for default BUILD_CONFIG... \n' in fixed.stdout, 'BUILD_CONFIG is not empty'
    makefile = (args.work / 'build-recipe/Makefile').read_text()
    assert re.search(r'^BUILD_CONFIG = *$', makefile, re.M), 'Makefile selects a build config'
    assert re.search(r'^do-compare = cmp ', makefile, re.M), 'stage comparison command missing'
    assert re.search(r'^compare:$', makefile, re.M), 'stage 2/3 compare target missing'
    print('PASS: Darwin GCC16 configures without bootstrap-debug and keeps the stage comparison')


if __name__ == '__main__':
    main()
