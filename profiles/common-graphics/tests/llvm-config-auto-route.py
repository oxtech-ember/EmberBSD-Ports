#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise automatic target llvm-config routing.
"""Check automatic Mesa helper selection against the target architecture."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def run(argv, env, log, expected=0):
    result = subprocess.run(argv, env=env, capture_output=True, text=True)
    output = result.stdout + result.stderr
    log.write_text(output)
    if result.returncode != expected:
        raise SystemExit(f'{log.name}: expected rc={expected}, got {result.returncode}\n{output}')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--makeconf', type=Path, required=True)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--expect-guard-failure', action='store_true')
    args = parser.parse_args()
    paths = [args.pkgsrc, args.makeconf, args.work]
    if args.profile is not None:
        paths.append(args.profile)
    if any(not path.is_absolute() for path in paths) or args.work.exists():
        parser.error('all paths must be absolute and work must be new')
    args.pkgsrc = args.pkgsrc.resolve(strict=True)
    args.makeconf = args.makeconf.resolve(strict=True)
    args.work.mkdir(parents=True)
    profile = (args.profile or (Path(__file__).resolve().parents[1] / 'mk.conf')).resolve(strict=True)
    text = args.makeconf.read_text()
    include = f'.include "{args.pkgsrc}/EMBERBSD-COMMON-GRAPHICS-MK.CONF"'
    if text.count(include) != 1:
        parser.error('MAKECONF must contain exactly one common graphics profile include')
    config = args.work / 'mk.conf'
    config.write_text(text.replace(include, f'.include "{profile}"', 1))

    bmake = Path(os.environ.get('BMAKE', ''))
    if not bmake.is_absolute() or not bmake.is_file():
        parser.error('BMAKE must name the selected absolute host bmake')
    prefix = bmake.parent.parent
    if not Path(sys.executable).resolve().is_relative_to(prefix.resolve()):
        parser.error('run with the selected native prefix Python')
    env = dict(os.environ, MAKECONF=str(config), PKGSRCDIR=str(args.pkgsrc))
    mesa = [str(bmake), '-C', str(args.pkgsrc / 'graphics/MesaLib'),
            'WRKDIR=' + str(args.work / 'mesa-wrkdir')]

    # Match cross-bulk startup: let pkgsrc verify the native binding, then
    # pass only the value that route returned into the Mesa query.
    verified = run([str(bmake), '-C', str(args.pkgsrc / 'pkgtools/pkg_install'),
                    'show-var', 'VARNAME=EMBERBSD_NATIVE_TOOLSET_VERIFIED'],
                   env, args.work / 'native-verification.log').strip()
    if not verified:
        raise SystemExit('pkgsrc did not return a verified native toolset')
    names = ('MACHINE_GNU_PLATFORM EMBERBSD_CROSS_LLVM_VERSION _EMBERBSD_CROSS_LLVM_STATE '
             'EMBERBSD_CROSS_LLVM_CONFIG_WORK EMBERBSD_CROSS_LLVM_CONFIG '
             '_EMBERBSD_GRAPHICS_LLVM_PRIOR_DEFINED _EMBERBSD_GRAPHICS_LLVM_PRIOR_CONFIG '
             'EMBERBSD_GRAPHICS_LLVM_CONFIG LLVM_CONFIG_PATH')
    query = run([*mesa, 'EMBERBSD_NATIVE_TOOLSET_VERIFIED=' + verified,
                 '_MAKEVARS_MK=defined', 'show-vars', 'VARNAMES=' + names],
                env, args.work / 'automatic-route-vars.log').splitlines()
    if len(query) != len(names.split()):
        raise SystemExit(f'unexpected variable output: {query!r}')
    values = dict(zip(names.split(), query))
    work = Path(values['_EMBERBSD_CROSS_LLVM_STATE']) / (
        'llvm-config-' + values['EMBERBSD_CROSS_LLVM_VERSION'])
    selected = str(work / 'helper/bin/llvm-config')
    if values['EMBERBSD_CROSS_LLVM_CONFIG_WORK'] != str(work) or any(
            values[key] != selected for key in ('EMBERBSD_CROSS_LLVM_CONFIG',
                                                'EMBERBSD_GRAPHICS_LLVM_CONFIG',
                                                'LLVM_CONFIG_PATH')):
        raise SystemExit('automatic helper does not follow the final target identity: ' + repr(values))
    if not Path(selected).is_file() or not os.access(selected, os.X_OK):
        raise SystemExit('selected target helper is not already installed: ' + selected)

    if args.expect_guard_failure:
        if values['_EMBERBSD_GRAPHICS_LLVM_PRIOR_DEFINED'] != 'yes' or \
                values['_EMBERBSD_GRAPHICS_LLVM_PRIOR_CONFIG'] == selected:
            raise SystemExit('baseline did not capture the mismatched early helper value: ' + repr(values))
        run([*mesa, 'EMBERBSD_NATIVE_TOOLSET_VERIFIED=' + verified,
             '_MAKEVARS_MK=defined', 'emberbsd-graphics-llvm-input-check'],
            env, args.work / 'automatic-route-guard.log', expected=1)
        if 'earlier conflicting LLVM_CONFIG_PATH' not in \
                (args.work / 'automatic-route-guard.log').read_text():
            raise SystemExit('baseline failed for a reason other than the early helper route')
        print('PASS: prior profile reproduces the automatic-route conflict')
        return
    if values['_EMBERBSD_GRAPHICS_LLVM_PRIOR_DEFINED'] != 'no':
        raise SystemExit('automatic helper assignment was misclassified as a caller override: ' + repr(values))
    run([*mesa, 'EMBERBSD_NATIVE_TOOLSET_VERIFIED=' + verified,
         '_MAKEVARS_MK=defined', 'emberbsd-graphics-llvm-input-check'],
        env, args.work / 'automatic-route-guard.log')
    # A command-line override remains an error after the automatic route.
    run([*mesa, 'EMBERBSD_NATIVE_TOOLSET_VERIFIED=' + verified,
         '_MAKEVARS_MK=defined', 'LLVM_CONFIG_PATH=/usr/bin/false',
         'emberbsd-graphics-llvm-input-check'],
        env, args.work / 'command-line-override.log', expected=1)
    if 'overridden LLVM_CONFIG_PATH' not in (args.work / 'command-line-override.log').read_text():
        raise SystemExit('command-line LLVM_CONFIG_PATH override was not rejected by the consumer guard')
    # A caller value in MAKECONF is distinct from the profile's own automatic
    # assignment and must continue to be rejected, including an empty value.
    profile_include = f'.include "{profile}"'
    for name, caller in (('earlier-bad', 'LLVM_CONFIG_PATH=/usr/bin/false'),
                         ('earlier-empty', 'LLVM_CONFIG_PATH=')):
        variant = args.work / (name + '.mk.conf')
        variant.write_text(config.read_text().replace(profile_include,
            caller + '\n' + profile_include, 1))
        run([str(bmake), '-C', str(args.pkgsrc / 'graphics/MesaLib'),
             'MAKECONF=' + str(variant), 'PKGSRCDIR=' + str(args.pkgsrc),
             'WRKDIR=' + str(args.work / (name + '-wrkdir')),
             'EMBERBSD_NATIVE_TOOLSET_VERIFIED=' + verified,
             '_MAKEVARS_MK=defined', 'emberbsd-graphics-llvm-input-check'],
            env, args.work / (name + '.log'), expected=1)
        if 'earlier conflicting LLVM_CONFIG_PATH' not in (args.work / (name + '.log')).read_text():
            raise SystemExit(name + ' caller selection was not rejected by the earlier-value guard')
    native = run([str(bmake), '-C', str(args.pkgsrc / 'devel/py-mako'),
                  'MAKECONF=' + str(config), 'PKGSRCDIR=' + str(args.pkgsrc),
                  'WRKDIR=' + str(args.work / 'native-wrkdir'),
                  'USE_CROSS_COMPILE=no', 'EMBERBSD_NATIVE_TOOLSET_VERIFIED=' + verified,
                  '_MAKEVARS_MK=defined', 'show-vars',
                  'VARNAMES=OPSYS PKG_FAIL_REASON EMBERBSD_COMMON_GRAPHICS LLVM_CONFIG_PATH'],
                 env, args.work / 'native-query.log').splitlines()
    if len(native) != 4 or native[0] != os.uname().sysname or native[1] or native[2] or \
            native[3] == selected:
        raise SystemExit('native dependency selection changed: ' + repr(native))
    print('PASS: automatic target-derived helper, consuming guard and explicit override refusal')


if __name__ == '__main__':
    main()
