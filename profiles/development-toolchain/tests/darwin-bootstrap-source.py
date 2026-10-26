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


def check_unprivileged_policy(policy):
    """Select the common current-user install policy before pkgsrc discovery."""
    lines = [line.strip() for line in policy.splitlines() if not line.lstrip().startswith('#')]
    require(lines.count('UNPRIVILEGED= yes') == 1,
            'The SDK prefix lost the explicit unprivileged pkgsrc policy')
    require(policy.index('UNPRIVILEGED= yes') <
            policy.index('.include "${.PARSEDIR}/EMBERBSD-DEVELOPMENT-MK.CONF"'),
            'The unprivileged policy follows shared pkgsrc configuration')
    require(not any(line.startswith(('SU_CMD', 'PKG_INSTALL_AS_ROOT')) for line in lines),
            'The profile replaces the common pkgsrc privilege mechanism')
    return True


def check_builtin_cases(rows):
    """Check captured (exit, bytes) pairs from the finite native make fixture."""
    names = {'old-empty', 'reference-empty', 'new-empty', 'reference-word', 'new-word',
             'reference-option', 'new-option', 'reference-backslash', 'new-backslash',
             'nested-empty', 'new-true', 'new-false',
             'new-test', 'new-test-false', 'new-bracket'}
    require(set(rows) == {(mode, name) for mode in ('compat', 'jobs1') for name in names},
            'The finite builtin capture is incomplete')
    for mode in ('compat', 'jobs1'):
        cases = {name: item for (kind, name), item in rows.items() if kind == mode}
        for name, program in [('old-empty', b'echo')]:
            code, data = cases[name]
            require((code != 0 and b'exec(' + program + b') failed' in data)
                    if mode == 'compat' else code == 0, 'The old route lost its causal failure')
        for name, (code, data) in cases.items():
            if name.startswith('old-'):
                continue
            if name in ('new-false', 'new-test-false'):
                require(code != 0 and b'Error code 1' in data and b'exec(' not in data,
                        'A selected builtin did not preserve its failure')
            else:
                require(code == 0, 'A selected builtin failed')
        for name in ('empty', 'word', 'option', 'backslash'):
            require(cases['new-' + name][1] == cases['reference-' + name][1],
                    'The route changed the selected shell builtin semantics')
        require(cases['new-empty'][1] == cases['nested-empty'][1] ==
                (b'\n' if mode == 'compat' else b''), 'Empty output or recursion changed')
        require(cases['new-word'][1] == b'plain value\n', 'A nonempty value changed')
    return True


def check_variable_cases(outputs):
    """Check the seven fixed named -V expressions without shell interpretation."""
    expected = (b'QUERY_UNDEFINED=\nQUERY_EMPTY=\nQUERY_WORD=plain\nQUERY_SPACE=space value\n'
                b'QUERY_BACKSLASH=first\\nsecond\nQUERY_QUOTE=double"quote\'single\nQUERY_OPTION=-n\n')
    require(set(outputs) == {'compat', 'jobs1'} and all(data == expected for data in outputs.values()),
            'A direct named expression lost an empty or literal value')
    return True


def branch(text, opening, count=1, which=0):
    """Return one literal conditional's two bodies; retain nested syntax."""
    lines = text.splitlines(keepends=True)
    hits = [i for i, line in enumerate(lines) if line.rstrip() == opening]
    require(len(hits) == count, f'Expected {count} exact source guards')
    start = hits[which]
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
    check_unprivileged_policy(policy)
    # The full ordinary native-tool body, including its xcrun behavior, is exact.
    name = 'mk/tools/tools.Darwin.mk'
    selected, ordinary = branch(after[name], OPT)
    original_body = before[name][before[name].index('OSX_XCRUN='):]
    require(ordinary == original_body, 'Ordinary Darwin native-tool bytes changed')
    require('xcrun' not in selected and '/usr/bin/' not in selected,
            'Selected native-tool branch contains host discovery')
    require('TOOLS_PLATFORM.gmake= ${EMBERBSD_DARWIN_GMAKE}' in selected,
            'Selected GNU make command was lost')
    require('TOOLS_PLATFORM.ggrep?= ${TOOLS_PLATFORM.grep}\n' in selected,
            'GNU grep requests lost the selected grep; a Ports grep forms a cycle')
    require('TOOLS_PLATFORM.${_ember_tool}= ${EMBERBSD_DARWIN_TOOL.${_ember_tool}}' in selected,
            'Native utility mapping was lost')
    for tool, args in [('gunzip', '-f'), ('gzip', '-nf ${GZIP}'), ('mkdir', '-p')]:
        require(f'_EMBERBSD_DARWIN_TOOL_ARGS.{tool}= {args}\n' in selected,
                f'Selected {tool} lost its standard pkgsrc arguments')
    require('${EMBERBSD_DARWIN_TOOL.${_ember_tool}}${_EMBERBSD_DARWIN_TOOL_ARGS.${_ember_tool}:D ${_EMBERBSD_DARWIN_TOOL_ARGS.${_ember_tool}}}' in selected,
            'Native utility arguments are not applied, or a tool gains a trailing space')
    require('TOOLS_PLATFORM.printf=' not in selected,
            'printf is treated as a shell builtin')
    require('.for _ember_builtin in [ echo false test true\n' in selected and
            'TOOLS_PLATFORM.${_ember_builtin}= ${EMBERBSD_DARWIN_BUILTIN_SHELL} ${EMBERBSD_DARWIN_BUILTIN_HELPER} ${_ember_builtin}' in selected and
            'EMBERBSD_DARWIN_BUILTIN_SHELL= ${EMBERBSD_DARWIN_SH}' in policy,
            'A simple builtin recipe can bypass its selected shell')

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
    selected, ordinary = branch(replacement, OPT, 2, 0)
    require(not ordinary and 'empty(EMBERBSD_DARWIN_SOURCE_TOOLS:M${_ember_tool})' in selected
            and '.error "Select a native or shared Ports source provider' in selected,
            'An unknown requested utility can silently use a provider')
    selected, ordinary = branch(replacement, OPT, 2, 1)
    require(not ordinary and '.  for _ember_builtin in echo false test true\n' in selected
            and 'TOOLS_${_TOOLS_VARNAME.${_ember_builtin}}=\t${TOOLS_CMDLINE.${_ember_builtin}}\n' in selected
            # after the loop that sets TOOLS_<VAR> to the first word
            and replacement.rindex(OPT) > replacement.index('TOOLS_CMDLINE_${_TOOLS_VARNAME.${_t_}}='),
            'pkgsrc scripts get only the shell of a builtin command map')
    unprivileged = after['mk/unprivileged.mk']
    selected, ordinary = branch(unprivileged, '.if !empty(_UNPRIVILEGED:Munprivileged)')
    selected, ordinary = branch(selected, OPT)
    require(not ordinary and '.  for _ember_ownership in chgrp chown\n' in selected and
            'TOOLS_PATH.${_ember_ownership}= ${TOOLS_PLATFORM.${_ember_ownership}:[1]}\n' in selected and
            'TOOLS_ARGS.${_ember_ownership}= ${TOOLS_PLATFORM.${_ember_ownership}:[2..-1]}\n' in selected and
            'TOOLS_CMDLINE.${_ember_ownership}= ${TOOLS_PLATFORM.${_ember_ownership}}\n' in selected and
            'TOOLS_${_TOOLS_VARNAME.${_ember_ownership}}= ${TOOLS_CMDLINE.${_ember_ownership}}\n' in selected and
            '${_TOOLS_VARNAME.${_ember_ownership}}= ${TOOLS_CMDLINE.${_ember_ownership}}\n' in selected and
            unprivileged.index(OPT) > unprivileged.index('TOOLS_PLATFORM.chown='),
            'Rootless ownership commands lost their complete selected-shell tuple')
    require('Select accepted parse-time utility ${_ember_tool}' in policy,
            'The early utility admission gate was lost')

    clang = after['mk/compiler/clang.mk']
    selected, ordinary = branch(clang, OPT, 2, 0)
    original = before['mk/compiler/clang.mk']
    start = original.index('.if exists(${CLANGBASE}/bin/clang)')
    end = original.index('.if !defined(CC_VERSION)', start)
    require(ordinary == original[start:end], 'Ordinary Clang selection bytes changed')
    require('exists(${${_ember_path}})' in selected and
            '.error "The selected Clang driver is missing:' in selected,
            'Missing Clang can reach host discovery')
    selected, ordinary = branch(clang, OPT, 2, 1)
    require(not ordinary and all(clang.count(line) == 1 for line in (
        'CWRAPPERS_PREPEND.${_ember_wrap}+= ${EMBERBSD_DARWIN_SEED_${_ember_var}:[2..-1]}',
        '_WRAP_EXTRA_ARGS.${_ember_var}+= ${EMBERBSD_DARWIN_SEED_${_ember_var}:[2..-1]}',
        'PKG_${_ember_var}= ${EMBERBSD_DARWIN_SEED_${_ember_var}:[1]}')),
            'The selected Clang wrapper lost its exact driver and command tail')

    gcc = after['mk/compiler/gcc.mk']
    require(gcc.count('CWRAPPERS_PREPEND.${_ember_wrap}+= ${EMBERBSD_GCC16_SEED_${_ember_var}:[2..-1]}') == 1,
            'The cwrapper seed command tail is missing or duplicated')
    require(gcc.count('_WRAP_EXTRA_ARGS.${_ember_var}+= ${EMBERBSD_GCC16_SEED_${_ember_var}:[2..-1]}') == 1,
            'The legacy-wrapper seed command tail is missing or duplicated')
    require('PKG_${_ember_var}= ${EMBERBSD_GCC16_SEED_${_ember_var}:[1]}' in gcc,
            'A cwrapper wrappee can contain a shell command')
    require('_GCC_QUERY_CC= ${EMBERBSD_GCC16_SEED_CC}' in gcc,
            'Compiler metadata lost its accepted binding')
    require('.if !empty(_CC:M${TOOLBASE}/*) && ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} != "yes"\n' in gcc
            and '.if !empty(_CC:M${TOOLBASE}/*)\n' in before['mk/compiler/gcc.mk'],
            'A selected GCC16 under TOOLBASE becomes a lang/gcc package dependency')
    require('+CONFIGURE_ENV+= CC=${EMBERBSD_GCC16_SEED_CC:Q} CXX=${EMBERBSD_GCC16_SEED_CXX:Q} CPP=${EMBERBSD_GCC16_SEED_CPP:Q}' in recipe,
            'GCC self-bootstrap lost its direct accepted compiler tuple')
    require('.for _ember_jobs in EMBERBSD_DARWIN_JOBS EMBERBSD_DARWIN_CPU_BUDGET' in policy and
            'empty(${_ember_jobs}:M[1-9]*)' in policy and
            '!empty(${_ember_jobs}:C/[0-9]//g)' in policy and
            '.if ${EMBERBSD_DARWIN_JOBS} > ${EMBERBSD_DARWIN_CPU_BUDGET}' in policy and
            policy.index('MAKE_JOBS= ${EMBERBSD_DARWIN_JOBS}') > policy.index('.include '),
            'The accepted jobs budget is absent or overwritten by the shared profile')
    require('.if ${EMBERBSD_DARWIN_JOBS} > 1' in policy and
            '.error "Parallel GCC bootstrap requires the accepted SDK link launcher"' in policy and
            '+MAKE_ENV+= GCC_HOST_LINKER_LAUNCHER=${EMBERBSD_GCC16_LINKER_LAUNCHER:Q}' in recipe,
            'Parallel native GCC can bypass the accepted link launcher')
    return True


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: darwin-bootstrap-source.py BEFORE_TREE AFTER_TREE')
    root = Path(__file__).resolve().parents[3]
    names = ['mk/tools/tools.Darwin.mk', 'mk/bsd.prefs.mk', 'mk/tools/replace.mk',
             'mk/unprivileged.mk', 'mk/compiler/gcc.mk', 'mk/compiler/clang.mk']
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
    changed[n] = changed[n].replace('_EMBERBSD_DARWIN_TOOL_ARGS.mkdir= -p\n', '', 1)
    mutants.append(('mkdir-without-p', changed, policy, recipe))
    changed = dict(after)
    changed[n] = changed[n].replace('TOOLS_PLATFORM.sh=', 'TOOLS_PLATFORM.printf= printf\nTOOLS_PLATFORM.sh=', 1)
    mutants.append(('printf-builtin', changed, policy, recipe))
    changed = dict(after)
    changed[n] = changed[n].replace('TOOLS_PLATFORM.${_ember_builtin}= ${EMBERBSD_DARWIN_BUILTIN_SHELL} ${EMBERBSD_DARWIN_BUILTIN_HELPER} ${_ember_builtin}',
                                  'TOOLS_PLATFORM.${_ember_builtin}= ${_ember_builtin}', 1)
    mutants.append(('unbound-builtins', changed, policy, recipe))
    changed = dict(after)
    changed[n] = changed[n].replace('TOOLS_PLATFORM.ggrep?= ${TOOLS_PLATFORM.grep}\n', '', 1)
    mutants.append(('ports-ggrep', changed, policy, recipe))
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
    n = 'mk/unprivileged.mk'
    changed[n] = changed[n].replace('TOOLS_${_TOOLS_VARNAME.${_ember_ownership}}= ${TOOLS_CMDLINE.${_ember_ownership}}',
                                   'TOOLS_${_TOOLS_VARNAME.${_ember_ownership}}= ${TOOLS_PATH.${_ember_ownership}}', 1)
    mutants.append(('rootless-ownership-tail', changed, policy, recipe))
    n = 'mk/compiler/clang.mk'
    for label, old, new in (
            ('clang-host-fallback', '.error "The selected Clang driver is missing:', '# missing refusal'),
            ('clang-ordinary-selection', 'CCPATH=\t\t\t${CLANGBASE}/bin/clang', 'CCPATH= /usr/bin/clang'),
            ('clang-missing-command-tail',
             'CWRAPPERS_PREPEND.${_ember_wrap}+= ${EMBERBSD_DARWIN_SEED_${_ember_var}:[2..-1]}', '')):
        require(old in after[n], 'Missing Clang mutation site: ' + label)
        changed = dict(after)
        changed[n] = changed[n].replace(old, new, 1)
        mutants.append((label, changed, policy, recipe))
    changed = dict(after)
    n = 'mk/compiler/gcc.mk'
    line = 'CWRAPPERS_PREPEND.${_ember_wrap}+= ${EMBERBSD_GCC16_SEED_${_ember_var}:[2..-1]}'
    changed[n] = changed[n].replace(line, line + '\n' + line, 1)
    mutants.append(('duplicate-specs-prefix', changed, policy, recipe))
    changed = dict(after)
    changed[n] = changed[n].replace(' && ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} != "yes"', '', 1)
    mutants.append(('toolbase-gcc-dependency', changed, policy, recipe))
    mutants.append(('unbudgeted-jobs', after, policy.replace('.if ${EMBERBSD_DARWIN_JOBS} > ${EMBERBSD_DARWIN_CPU_BUDGET}', '.if 0'), recipe))
    mutants.append(('parallel-link-bypass', after, policy.replace('.error "Parallel GCC bootstrap requires the accepted SDK link launcher"', '# no link resource refusal'), recipe))
    mutants.append(('privileged-install', after, policy.replace('UNPRIVILEGED= yes\n', ''), recipe))
    mutants.append(('empty-su-bypass', after, policy + '\nSU_CMD=\n', recipe))
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
