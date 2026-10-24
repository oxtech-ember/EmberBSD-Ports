#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Finite source controls, not make evaluation.
"""Check the prepared policy source against its exact pre-patch source tree."""
import json
import sys
from pathlib import Path

OPT = '.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} == "yes"'


def require(value, message):
    if not value:
        raise AssertionError(message)


def branch(text, opening):
    """Return this one literal conditional's two bodies; retain nested syntax."""
    lines = text.splitlines(keepends=True)
    hits = [i for i, line in enumerate(lines) if line.rstrip() == opening]
    require(len(hits) == 1, 'Expected one exact source guard')
    start = hits[0]
    depth = 1
    split = None
    for i in range(start + 1, len(lines)):
        # pkgsrc indents directive keywords after the dot.
        directive = lines[i].lstrip()[1:].lstrip().split(None, 1)[0] if lines[i].lstrip().startswith('.') else ''
        if directive in ('if', 'ifdef', 'ifndef'):
            depth += 1
        elif directive == 'endif':
            depth -= 1
            if depth == 0:
                return ''.join(lines[start + 1:split or i]), ''.join(lines[split + 1:i]) if split is not None else ''
        elif directive == 'else' and depth == 1:
            split = i
    raise AssertionError('Unclosed source guard')


def check(before, after, policy, recipe):
    # The full ordinary native-tool body, including its xcrun behavior, is exact.
    name = 'mk/tools/tools.Darwin.mk'
    selected, ordinary = branch(after[name], OPT)
    original_body = before[name][before[name].index('OSX_XCRUN='):]
    require(ordinary == original_body, 'Ordinary Darwin native-tool bytes changed')
    require('xcrun' not in selected and '/usr/bin/' not in selected,
            'Selected native-tool branch contains host discovery')
    require('TOOLS_PLATFORM.gmake= ${EMBERBSD_DARWIN_GMAKE}' in selected,
            'Selected GNU make command was lost')
    require('TOOLS_PLATFORM.${_ember_tool}= ${EMBERBSD_DARWIN_TOOL.${_ember_tool}}' in selected,
            'Native utility mapping was lost')

    prefs = after['mk/bsd.prefs.mk']
    include = prefs.index('.include "${MAKECONF}"')
    require(include < prefs.index('# Set PATH if not already set') < prefs.index('NATIVE_OPSYS:='),
            'MAKECONF can follow PATH or host discovery')
    require('!exists(${MAKECONF})' in prefs[:include] and 'empty(MAKECONF:M/*)' in prefs[:include],
            'Missing or relative MAKECONF can reach fallback')
    selected, ordinary = branch(prefs, OPT)
    start = before['mk/bsd.prefs.mk'].index('.if exists(/usr/bin/uname)')
    stop = before['mk/bsd.prefs.mk'].index('\n\n.if !defined(NATIVE_OPSYS)', start)
    require(ordinary == before['mk/bsd.prefs.mk'][start:stop] + '\n',
            'Ordinary uname selection bytes changed')
    require('UNAME= ${EMBERBSD_DARWIN_TOOL.uname}' in selected,
            'The selected uname path was lost')
    for fact, value in [('NATIVE_OPSYS', 'OS'), ('NATIVE_OS_VERSION', 'KERNEL_VERSION'),
                        ('NATIVE_OPSYS_VERSION', 'PKGSRC_OPSYS_VERSION'), ('MACHINE_ARCH', 'CPU')]:
        require(f'{fact}= ${{EMBERBSD_DARWIN_HOST_{value}}}' in policy,
                f'Stale {fact} can replace the accepted host fact')
    require('OS CPU KERNEL_VERSION PRODUCT_VERSION PKGSRC_OPSYS_VERSION' in policy,
            'An accepted host fact is no longer required')
    require(all(f'.undef {v}\n' in policy for v in ['_CC', '_GCC_VERSION', '_GCC_VERSION_STRING']),
            'An inherited compiler cache can replace the selected query')

    replacement = after['mk/tools/replace.mk']
    selected, ordinary = branch(replacement, OPT)
    require(not ordinary and 'empty(EMBERBSD_DARWIN_SOURCE_TOOLS:M${_ember_tool})' in selected
            and '.error "Select a native or shared Ports source provider' in selected,
            'An unknown requested utility can silently use a provider')
    require('Select accepted parse-time utility ${_ember_tool}' in policy,
            'The early utility admission gate was lost')

    gcc = after['mk/compiler/gcc.mk']
    require(gcc.count('CWRAPPERS_PREPEND.${_ember_wrap}+= ${EMBERBSD_GCC16_SEED_${_ember_var}:[2..-1]}') == 1,
            'The cwrapper seed command tail is missing or duplicated')
    require(gcc.count('_WRAP_EXTRA_ARGS.${_ember_var}+= ${EMBERBSD_GCC16_SEED_${_ember_var}:[2..-1]}') == 1,
            'The legacy-wrapper seed command tail is missing or duplicated')
    require('PKG_${_ember_var}= ${EMBERBSD_GCC16_SEED_${_ember_var}:[1]}' in gcc,
            'A cwrapper wrappee can contain a shell command')
    require('_GCC_QUERY_CC= ${EMBERBSD_GCC16_SEED_CC}' in gcc,
            'Compiler metadata lost its accepted binding')
    require('+CONFIGURE_ENV+= CC=${EMBERBSD_GCC16_SEED_CC:Q} CXX=${EMBERBSD_GCC16_SEED_CXX:Q} CPP=${EMBERBSD_GCC16_SEED_CPP:Q}' in recipe,
            'GCC self-bootstrap lost its direct accepted compiler tuple')
    require('empty(EMBERBSD_DARWIN_JOBS:M[1-4])' in policy and
            policy.index('MAKE_JOBS= ${EMBERBSD_DARWIN_JOBS}') > policy.index('.include '),
            'The jobs cap is absent or overwritten by the shared profile')
    return True


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: darwin-bootstrap-source.py BEFORE_TREE AFTER_TREE')
    root = Path(__file__).resolve().parents[3]
    names = ['mk/tools/tools.Darwin.mk', 'mk/bsd.prefs.mk', 'mk/tools/replace.mk', 'mk/compiler/gcc.mk']
    before = {n: (Path(sys.argv[1]) / n).read_text() for n in names}
    after = {n: (Path(sys.argv[2]) / n).read_text() for n in names}
    policy = (root / 'profiles/development-toolchain/darwin-bootstrap.mk.conf').read_text()
    recipe = (root / 'profiles/development-toolchain/patches/gcc-darwin-host.patch').read_text()
    check(before, after, policy, recipe)
    mutants = []
    changed = dict(after)
    n = 'mk/tools/tools.Darwin.mk'
    changed[n] = changed[n].replace('# Every native tool', 'OSX_BAD!= /usr/bin/xcrun --find m4\n# Every native tool', 1)
    mutants.append(('selected-xcrun', changed, policy, recipe))
    changed = dict(after)
    n = 'mk/bsd.prefs.mk'
    changed[n] = changed[n].replace('.include "${MAKECONF}"', '# stale host query runs first', 1)
    mutants.append(('missing-early-config', changed, policy, recipe))
    mutants.append(('stale-host-os', after, policy.replace('NATIVE_OPSYS= ${EMBERBSD_DARWIN_HOST_OS}', 'NATIVE_OPSYS?= Darwin'), recipe))
    changed = dict(after)
    n = 'mk/tools/replace.mk'
    changed[n] = changed[n].replace('.error "Select a native or shared Ports source provider', '# missing refusal "Select a native or shared Ports source provider', 1)
    mutants.append(('unknown-utility', changed, policy, recipe))
    changed = dict(after)
    n = 'mk/compiler/gcc.mk'
    line = 'CWRAPPERS_PREPEND.${_ember_wrap}+= ${EMBERBSD_GCC16_SEED_${_ember_var}:[2..-1]}'
    changed[n] = changed[n].replace(line, line + '\n' + line, 1)
    mutants.append(('duplicate-specs-prefix', changed, policy, recipe))
    mutants.append(('uncapped-jobs', after, policy.replace('empty(EMBERBSD_DARWIN_JOBS:M[1-4])', 'empty(EMBERBSD_DARWIN_JOBS)'), recipe))
    rejected = []
    for name, source, conf, gcc_recipe in mutants:
        try:
            check(before, source, conf, gcc_recipe)
        except (AssertionError, ValueError):
            rejected.append(name)
        else:
            raise AssertionError(f'Mutant was accepted: {name}')
    print(json.dumps({'scope': 'finite source controls only; no make/DAG or binary execution',
                      'positive': 'PASS', 'mutants_rejected': rejected}, sort_keys=True))


if __name__ == '__main__':
    main()
