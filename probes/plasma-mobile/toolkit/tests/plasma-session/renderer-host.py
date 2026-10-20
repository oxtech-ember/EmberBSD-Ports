#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run actual shell profile controls. No KDE, target command or GPU is run."""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex

BASELINE = '8b0508d72da7adf676af5a4ab1b069b2099b2e07'
ICD = '/usr/pkg/share/vulkan/icd.d/powervr_mesa_icd.json'
POWER = 'zink Vulkan 1.2(PowerVR B-Series BXM-4-64 MC1 (IMAGINATION_OPEN_SOURCE_MESA))'
V3D = 'V3D 7.1.10.2'


def section(text, start, end):
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('Actual source boundary changed: ' + start)
    return text.split(start, 1)[1].split(end, 1)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    ports = source.parents[4]
    sys.path.insert(0, str(ports / 'profiles/development-toolchain/runtime/recipe/files'))
    import sdk_source
    sdk_source.load(args.sdk_source)
    from emberbsd_sdk.process import capture
    from emberbsd_sdk.errors import CommandError

    work = args.work.absolute()
    if work.exists() or work.is_symlink():
        raise ValueError('Select a new work directory')
    work.mkdir()
    work = work.resolve()
    checker = source.parent / 'plasma-desktop/check-results.sh'
    inputs = [source / 'run.sh', source / 'controller.sh', source / 'guard.pl', checker, Path(__file__)]
    pins = {str(p.relative_to(ports)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    runner = (source / 'run.sh').read_text()
    controller = (source / 'controller.sh').read_text()
    check_text = checker.read_text()
    results = []

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def call(name, argv, expected=0, env=None, cwd=None):
        try:
            result = capture(argv, cwd=cwd or work, env=env)
            code, out, err = 0, result.stdout, result.stderr
        except CommandError as error:
            code, out, err = error.returncode, error.stdout, error.stderr
        row = dict(name=name, argv=argv, code=code, expected=expected,
                   stdout=out.decode(errors='replace'), stderr=err.decode(errors='replace'))
        results.append(row)
        require(code == expected if expected is not None else code != 0,
                'Wrong result: ' + json.dumps(row))
        return out

    def script(name, body, argv=(), expected=0, env=None):
        path = work / (name + '.sh')
        path.write_text('#!/bin/sh\nset -eu\n' + body)
        return call(name, ['/bin/sh', str(path), *argv], expected, env)

    def support(value):
        return 'Compositing is active\nCompositing Type: OpenGL ES\nOpenGL renderer string: ' + value + '\n'

    def qt(value):
        return '[321] qt.rhi.general: OpenGL VENDOR: Mesa RENDERER: ' + value + ' VERSION: 3.1\n'

    def check(name, mode, text, profile=None, expected=0, selected=checker):
        evidence = work / (name + '.txt')
        evidence.write_text(text)
        argv = ['/bin/sh', str(selected), mode, str(evidence)]
        if profile is not None:
            argv.append(profile)
        call(name, argv, expected)

    try:
        for p in inputs[:4]:
            if p.suffix == '.sh':
                call('syntax-' + p.name, ['/bin/sh', '-n', str(p)])
        for profile, value in [('v3d', V3D), ('powervr-zink', POWER)]:
            for mode, render in [('support', support), ('renderer', qt)]:
                check(profile + '-' + mode, mode, render(value), profile)
                check(profile + '-repeat-' + mode, mode, render(value) + render(value), profile)
                for bad in ['llvmpipe', 'lavapipe', 'softpipe', 'QPainter', 'zink', 'PowerVR', 'notzink PowerVR', 'zink notPowerVR', '']:
                    check(profile + '-' + mode + '-bad-' + str(len(results)), mode, render(bad), profile, 1)
                    check(profile + '-' + mode + '-mixed-' + str(len(results)), mode, render(value) + render(bad), profile, 1)
                check(profile + '-inactive', 'support', support(value).replace('Compositing is active', 'Compositing is inactive'), profile, 1)
                check(profile + '-qpainter', 'support', support(value) + 'Compositing Type: QPainter\n', profile, 1)
        check('default-support', 'support', support(V3D))
        check('default-qt', 'renderer', qt(V3D))
        check('default-no-power', 'support', support(POWER), expected=1)
        check('unknown-profile', 'support', support(V3D), 'unknown', 2)
        check('empty-profile', 'support', support(V3D), '', 2)
        check('opengl-without-es', 'support', support(V3D).replace('OpenGL ES', 'OpenGL'))
        check('qt-no-pid', 'renderer', qt(V3D).replace('[321] ', ''))
        for name, text in [
            ('vendor-spoof', qt('zink').replace('VENDOR: Mesa', 'VENDOR: PowerVR')),
            ('version-spoof', qt('zink').replace('VERSION: 3.1', 'VERSION: PowerVR')),
            ('separate-lines', qt('zink') + qt('PowerVR')),
            ('environment', 'GALLIUM_DRIVER=zink PowerVR\n'),
            ('unrelated', 'debug mentions ' + qt(POWER)),
            ('malformed', qt(POWER) + '[321] qt.rhi.general: OpenGL VENDOR: PowerVR RENDERER: zink\n'),
            ('qml', qt(POWER) + 'Error loading applet\n'),
        ]:
            check(name, 'renderer', text, 'powervr-zink', 1)
        check('support-unrelated', 'support', support('zink') + 'GPU name: PowerVR\n', 'powervr-zink', 1)
        image = work / 'header.png'
        image.write_bytes(bytes.fromhex('89504e470d0a1a0a0000000d494844520000014000000100'))
        call('png-unchanged', ['/bin/sh', str(checker), 'png', str(image)])

        # Execute the actual parser and path gates before any target preflight.
        prefix = runner.split('[ "$(id -u)" -ne 0 ]', 1)[0]
        out = work / 'never-created'
        parser_ok = prefix + 'printf "%s\\n" "$profile"\n'
        require(script('parser-default', parser_ok, [str(out)]) == b'v3d\n', 'Default profile changed')
        for profile in ['v3d', 'powervr-zink']:
            require(script('parser-' + profile, parser_ok, ['--renderer', profile, str(out)]) == (profile + '\n').encode(), 'Explicit profile lost')
        for index, argv in enumerate([[], ['relative'], ['--renderer'], ['--renderer', ''], ['--renderer', 'unknown', str(out)], ['--renderer', '', str(out)], ['--renderer', 'v3d', '--renderer', 'powervr-zink', str(out)], [str(work)], ['--other', 'v3d', str(out)]]):
            script('parser-reject-' + str(index), parser_ok, argv, 2)
            require(not out.exists(), 'Rejected argument created output')
        # Full production CLI must reject unknown profiles before target commands.
        call('full-unknown-cli', ['/bin/sh', str(source / 'run.sh'), '--renderer', 'unknown', str(out)], 2)
        require(not out.exists(), 'Full invalid CLI created output')

        prerequisites = section(runner, '# Check access without creating nodes or changing their permissions.\n', 'source_dir=$(CDPATH=')
        regular = work / 'regular'; regular.write_text('fixture')
        link = work / 'link'; link.symlink_to('/dev/null')
        icd = work / 'icd.json'; icd.write_text('{}\n')
        for index, (nodes, path, profile, status) in enumerate([
            (['/dev/null'], icd, 'powervr-zink', 0),
            ([str(regular), '/dev/null'], icd, 'v3d', 0),
            ([str(regular)], icd, 'v3d', 2), ([str(link)], icd, 'v3d', 2),
            ([str(work / 'missing')], icd, 'v3d', 2),
            (['/dev/null'], work / 'missing', 'powervr-zink', 2),
            (['/dev/null'], work, 'powervr-zink', 2),
            (['/dev/null'], work / 'missing', 'v3d', 0),
        ]):
            body = 'profile=' + shlex.quote(profile) + '\n' + prerequisites.replace('/dev/dri/renderD*', shlex.join(nodes)).replace(ICD, shlex.quote(str(path)))
            script('prerequisite-' + str(index), body, expected=status)

        # Reproduce the former unquoted ICD assignment, even with a plain --work.
        spaced = work / 'renderer fixture'; spaced.mkdir()
        spaced_icd = spaced / 'installed ICD.json'; spaced_icd.write_text('{}\n')
        prefix = 'profile=powervr-zink\n'
        unsafe = prerequisites.replace('/dev/dri/renderD*', '/dev/null').replace(ICD, str(spaced_icd))
        safe = prerequisites.replace('/dev/dri/renderD*', '/dev/null').replace(ICD, shlex.quote(str(spaced_icd)))
        script('unquoted-icd-baseline', prefix + unsafe, expected=None,
               env=dict(os.environ, LC_ALL='C'))
        require(results[-1]['code'] in (1, 127) and
                any(text in results[-1]['stderr'] for text in ['not found', 'No such file or directory']),
                'The unquoted baseline did not fail at the split shell command')
        script('quoted-icd-fixed', prefix + safe)
        # Observe the for-loop words without changing its access predicate.
        nodes = [str(spaced / 'absent node'), '/dev/null']
        observed = prerequisites.replace('; do\n', '; do\n    printf "%s\\n" "$node"\n', 1)
        observed = observed.replace(ICD, shlex.quote(str(spaced_icd)))
        split = script('unquoted-nodes-baseline', prefix + observed.replace('/dev/dri/renderD*', ' '.join(nodes)))
        intact = script('quoted-nodes-fixed', prefix + observed.replace('/dev/dri/renderD*', shlex.join(nodes)))
        expected = ('\n'.join(nodes) + '\n').encode()
        require(split != expected and intact == expected, 'Node quoting control missed shell word splitting')

        # Use the real env -i dispatch. Replace only its target Perl/guard command.
        dispatch = '# These argv entries enter only the clean session environment.\n' + section(runner, '# These argv entries enter only the clean session environment.\n', '/sbin/sysctl kern.boottime > boot.after')
        recorder = work / 'record.py'
        recorder.write_text('import json,os,sys\nprint(json.dumps(dict(env=dict(os.environ),argv=sys.argv[1:])))\nsys.exit(int(os.environ["TEST_EXIT"]))\n')
        expected_power = dict(KWIN_COMPOSE='O2ES', GALLIUM_DRIVER='zink', MESA_LOADER_DRIVER_OVERRIDE='zink', VK_DRIVER_FILES=ICD, PVR_I_WANT_A_BROKEN_VULKAN_DRIVER='1')
        for profile in ['v3d', 'powervr-zink']:
            for status in [0, 7]:
                directory = work / (profile + '-' + str(status)); directory.mkdir()
                body = 'work=' + shlex.quote(str(directory)) + '\ncd "$work"\nprofile=' + profile + '\naccount=fixture\nlogin_shell=/bin/sh\nicd=' + ICD + '\n'
                body += dispatch.replace('/usr/pkg/bin/perl ./guard.pl', 'TEST_EXIT=' + str(status) + ' ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(recorder)) + ' ./guard.pl')
                env = dict(os.environ, LD_LIBRARY_PATH='/untrusted', LD_PRELOAD='/untrusted', VK_ICD_FILENAMES='/untrusted', VK_DRIVER_FILES='/untrusted', GALLIUM_DRIVER='softpipe')
                script('dispatch-' + profile + '-' + str(status), body, env=env)
                row = json.loads((directory / 'bus.log').read_text())
                require((directory / 'status').read_text().strip() == str(status), 'Guard status lost')
                require(row['argv'] == ['./guard.pl', str(directory), '240', '--', '/usr/pkg/bin/dbus-run-session', '--', '/bin/sh', './controller.sh'], 'Supervisor dispatch changed')
                for key, value in expected_power.items():
                    require(row['env'].get(key) == (value if profile == 'powervr-zink' else None), 'Incorrect environment: ' + key)
                for key in ['LD_LIBRARY_PATH', 'LD_PRELOAD', 'LIBGL_DRIVERS_PATH', 'VK_ICD_FILENAMES', 'QT_PLUGIN_PATH', 'QML_IMPORT_PATH']:
                    require(key not in row['env'], 'Inherited private override: ' + key)
                require(row['env']['EMBER_PLASMA_RENDERER_PROFILE'] == profile, 'Profile lost at dispatch')

        # The controller must pass the selected profile at all three call sites.
        calls = [line for line in controller.splitlines() if line.startswith('/bin/sh ./check-results.sh ')]
        require(len(calls) == 3 and all(line.endswith(' "$profile"') for line in calls), 'Controller profile propagation changed')
        require('awk -v prefix="[$shell_pid] "' in controller, 'Actual shell PID filter lost')
        for profile, value in [('v3d', V3D), ('powervr-zink', POWER)]:
            for name in ['support-before.txt', 'support-after.txt']:
                (work / name).write_text(support(value))
            (work / 'shell-renderer.log').write_text(qt(value))
            (work / 'check-results.sh').write_text(check_text)
            script('controller-checks-' + profile, 'profile=' + profile + '\n' + '\n'.join(calls) + '\n')

        # Compare preserved lifecycle source with the exact upstream baseline.
        relative = source.relative_to(ports)
        old = lambda name: capture(['git', '-C', str(ports), 'show', BASELINE + ':' + str(relative / name)]).stdout.decode()
        original_controller = old('controller.sh')
        projected = controller.replace('profile=${EMBER_PLASMA_RENDERER_PROFILE-v3d}\ncase "$profile" in v3d|powervr-zink) ;; *) exit 2 ;; esac\n', '')
        projected = projected.replace(' "$profile"\n', '\n')
        require(projected == original_controller, 'Controller changed outside profile plumbing')
        require((source / 'guard.pl').read_text() == old('guard.pl'), 'Supervisor changed')
        old_checker = work / 'baseline-checker.sh'
        old_checker.write_bytes(capture(['git', '-C', str(ports), 'show', BASELINE + ':' + str(checker.relative_to(ports))]).stdout)
        check('baseline-powervr-red', 'support', support(POWER), expected=1, selected=old_checker)
        check('baseline-v3d-green', 'renderer', qt(V3D), selected=old_checker)
        for label, before, after in [
            ('allow-software', 'if (lower ~ /llvmpipe|lavapipe|softpipe|qpainter/)', 'if (0)'),
            ('ignore-mixed', 'exit (count == 0 || bad)', 'exit (count == 0)'),
            ('drop-power', 'lower !~ /(^|[^[:alnum:]_])powervr([^[:alnum:]_]|$)/', '0'),
        ]:
            require(check_text.count(before) == 1, 'Mutation point changed')
            mutant = work / (label + '.sh'); mutant.write_text(check_text.replace(before, after))
            bad = POWER + ' llvmpipe' if label == 'allow-software' else ('zink' if label == 'drop-power' else POWER)
            payload = qt(bad) + (qt('lavapipe') if label == 'ignore-mixed' else '')
            # These deliberately broken predicates must falsely accept.
            check('mutant-' + label, 'renderer', payload, 'powervr-zink', 0, mutant)
            check('fixed-' + label, 'renderer', payload, 'powervr-zink', 1)
        require(all(hashlib.sha256((ports / name).read_bytes()).hexdigest() == value for name, value in pins.items()), 'Source changed during regression')
        receipt = dict(status='PASS', cases=len(results), source_sha256=pins, baseline=BASELINE, checks=results,
                       scope='Host shell and process-environment controls. Target preflight paths are explicit doubles. No KDE, GPU or target execution.')
    except BaseException as error:
        receipt = dict(status='FAIL', error=str(error), checks=results, source_sha256=pins)
        raise
    finally:
        (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS:', len(results), 'actual-source renderer/profile controls; no target execution')


if __name__ == '__main__':
    main()
