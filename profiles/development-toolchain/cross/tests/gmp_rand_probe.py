# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; causal checks of the pinned GMP 6.3.0 test adaptation.
"""Run original and patched t-rand against one unchanged host library."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil

from emberbsd_sdk.errors import CommandError
from host import (PROFILE, build_path, capture, digest_rows, host_compilers,
                  jobs, logged, new_path, policy_sources, require, sha,
                  source_row)
from pipeline import GMP_RAND_PATCH_SHA256

HERE = Path(__file__).resolve().parent
TYPE_ERROR = 'GMP random size must be unsigned long'


def status(command, log, env, cwd=None):
    """Retain expected test failures without hiding failed producer ownership."""
    try:
        logged(command, log, env, cwd)
    except CommandError as error:
        return error.returncode
    return 0


def main(args):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', help='Pinned gmp-6.3.0.tar.xz archive')
    parser.add_argument('work', help='New directory for sources and receipts')
    parser.add_argument('--sanitize', action='store_true',
                        help='Build C objects and tests with ASan/UBSan')
    parser.add_argument('--require-baseline-failure', action='store_true',
                        help='Require the original runtime test to fail on this host')
    options = parser.parse_args(args)
    archive, work = build_path(options.archive), new_path(options.work)
    row = source_row('gmp', '6.3.0', [PROFILE / 'cross/host-sources.tsv'])
    delta = PROFILE / 'cross/patches/gmp-t-rand-varargs.patch'
    require(sha(archive) == row[3], 'GMP archive SHA256 mismatch')
    require(sha(delta) == GMP_RAND_PATCH_SHA256, 'GMP test patch SHA256 mismatch')
    cc, cxx = host_compilers()
    make = shutil.which(os.environ.get('GMAKE', 'gmake'))
    require(make, 'GNU make missing')
    require('GNU Make' in capture([make, '--version']), 'GNU make is required')
    count = jobs()
    cppflags = shlex.split(os.environ.get('HOST_CPPFLAGS', ''))
    ldflags = shlex.split(os.environ.get('HOST_LDFLAGS', ''))
    flags = ['-O2', '-std=gnu17']
    if options.sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-sanitize-recover=all']
    env = dict(CC=cc, CXX=cxx, CFLAGS=shlex.join(flags),
               CPPFLAGS=shlex.join(cppflags), LDFLAGS=shlex.join(ldflags))
    work.mkdir()
    source, build = work / 'source', work / 'build'
    source.mkdir()
    build.mkdir()
    (work / 'inputs.txt').write_text(
        platform.platform() + '\nsource_url=' + row[2] + '\n' +
        capture([cc, '--version']) + capture([cc, '-dumpmachine']) +
        'cflags=' + shlex.join(flags) + '\ncppflags=' + shlex.join(cppflags) +
        '\nldflags=' + shlex.join(ldflags) + '\n' +
        digest_rows([archive, delta, Path(__file__), HERE / 'gmp-rand-types.h'] +
                    policy_sources()), encoding='utf-8')
    logged(['tar', '-xf', archive, '--strip-components=1', '-C', source],
           work / 'extract.log', env)
    original = work / 'original-t-rand.c'
    shutil.copyfile(source / 'tests/rand/t-rand.c', original)
    logged([source / 'configure', '--disable-shared', '--enable-static'],
           work / 'configure.log', env, build)
    logged([make, '-j' + count], work / 'library-build.log', env, build)
    library = build / '.libs/libgmp.a'
    library_hash = sha(library)
    logged(['patch', '-f', '-N', '-F', '0', '-p1', '-d', source, '-i', delta],
           work / 'patch.log', env)
    fixed = work / 'fixed-t-rand.c'
    shutil.copyfile(source / 'tests/rand/t-rand.c', fixed)
    compile_command = [cc] + flags + cppflags + ['-I' + str(build)]
    commands = []
    results = {'schema': 1, 'library_sha256': library_hash, 'runtime': {},
               'type_controls': {}, 'sanitize': options.sanitize}
    for name, test in [('original', original), ('fixed', fixed)]:
        binary = work / (name + '-t-rand')
        command = compile_command + [test, library] + ldflags + ['-o', binary]
        commands.append({'directory': str(work), 'file': str(test),
                         'arguments': [str(value) for value in command]})
        logged(command, work / (name + '-build.log'), env)
        result = status([binary], work / (name + '-run.log'), env)
        results['runtime'][name] = result
        require(name != 'fixed' or result == 0, 'Patched GMP t-rand failed')
    if options.require_baseline_failure:
        require(results['runtime']['original'] != 0,
                'The original runtime failure did not reproduce on this host')

    # A clean runtime baseline does not prove correct variadic argument types.
    # These compile controls reject each missing cast on every supported ABI.
    text = fixed.read_text(encoding='utf-8')
    sites = list(re.finditer(r'gmp_randinit\s*\(rstate, GMP_RAND_ALG_LC, '
                             r'(\(unsigned long\) )', text))
    require(len(sites) == 3, 'Expected three patched GMP variadic call sites')
    controls = [('original', original, 3), ('fixed', fixed, 0)]
    for index, site in enumerate(sites, 1):
        mutant = work / ('missing-cast-' + str(index) + '.c')
        mutant.write_text(text[:site.start(1)] + text[site.end(1):], encoding='utf-8')
        controls.append(('missing-cast-' + str(index), mutant, 1))
    for name, test, expected in controls:
        log = work / (name + '-type.log')
        result = status(compile_command + ['-include', HERE / 'gmp-rand-types.h',
                        '-fsyntax-only', '-fdiagnostics-color=never', test], log, env)
        diagnostics = log.read_text(encoding='utf-8')
        errors = re.findall(r'error: static assertion failed:.*' + TYPE_ERROR, diagnostics)
        require((result == 0) == (expected == 0) and len(errors) == expected
                and len(re.findall(r'error:', diagnostics)) == expected,
                'Unexpected variadic type control result: ' + name)
        results['type_controls'][name] = {'exit': result, 'type_errors': len(errors)}

    # Exercise the print-mode call as well as both upstream verification tables.
    for mode, bits in [('z', 16), ('f', 16), ('z', 128), ('f', 128)]:
        name = mode + str(bits)
        log = work / ('fixed-print-' + name + '.log')
        logged([work / 'fixed-t-rand', mode, str(bits)], log, env)
        table = re.search(r'const char \*' + name + r'\[ENTS\] = \{([^\n]+)\};', text)
        require(table is not None, 'Missing upstream expected-value table: ' + name)
        expected = re.findall(r'"([^"]*)"', table.group(1))
        actual = re.findall(r'"([^"]*)"', log.read_text(encoding='utf-8'))
        require(len(expected) == 10 and actual == expected,
                'Print-mode output differs from upstream values: ' + name)
        results['runtime']['fixed-print-' + name] = 0
    require(sha(library) == library_hash, 'The comparison changed the GMP library')
    (work / 'compile_commands.json').write_text(json.dumps(commands, indent=2) + '\n', encoding='utf-8')
    (work / 'results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print('PASS: patched GMP random values, print modes and three missing-cast controls')
    print('Original runtime exit: ' + str(results['runtime']['original']) +
          '; diagnostics and unchanged-library identity: ' + str(work))
