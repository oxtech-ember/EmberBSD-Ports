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

BASELINE = 'e441c445281b1b7e80d2951f4883dc5f7beeea0b'
ICD = '/usr/pkg/share/vulkan/icd.d/powervr_mesa_icd.json'
POWER = 'zink Vulkan 1.2(PowerVR B-Series BXM-4-64 MC1 (IMAGINATION_OPEN_SOURCE_MESA))'
V3D = 'V3D 7.1.10.2'
RADEONSI = 'AMD Radeon(TM) Graphics (radeonsi, raven, ACO, DRM 3.54.0, LLVM 23.1.4)'


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
    inputs = [source / 'run.sh', source / 'controller.sh', source / 'guard.pl', checker, source.parent / 'plasma-desktop/layout.js', Path(__file__)]
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
        for profile, value in [('v3d', V3D), ('powervr-zink', POWER), ('radeonsi', RADEONSI)]:
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
        check('default-no-radeonsi', 'support', support(RADEONSI), expected=1)
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
            ('radeonsi-vendor-spoof', qt('llvmpipe').replace('VENDOR: Mesa', 'VENDOR: AMD')),
            ('radeonsi-unrelated-renderer', qt('llvmpipe') + 'AMD Radeon Graphics (radeonsi, raven)\n'),
            ('radeonsi-without-amd-renderer', qt('radeonsi, raven')),
            ('radeonsi-without-driver', qt('AMD Radeon Graphics (raven)')),
        ]:
            check(name, 'renderer', text, 'radeonsi' if name.startswith('radeonsi-') else 'powervr-zink', 1)
        check('radeonsi-vendor-spoof-support', 'support', support('llvmpipe AMD Radeon radeonsi'), 'radeonsi', 1)
        check('radeonsi-mixed', 'renderer', qt(RADEONSI) + qt('AMD Radeon (llvmpipe)'), 'radeonsi', 1)
        check('support-unrelated', 'support', support('zink') + 'GPU name: PowerVR\n', 'powervr-zink', 1)
        image = work / 'header.png'
        image.write_bytes(bytes.fromhex('89504e470d0a1a0a0000000d494844520000014000000100'))
        call('png-unchanged', ['/bin/sh', str(checker), 'png', str(image)])

        # Execute the actual parser and path gates before any target preflight.
        prefix = runner.split('[ "$(id -u)" -ne 0 ]', 1)[0]
        out = work / 'never-created'
        parser_ok = prefix + 'printf "%s\\n" "$profile"\n'
        require(script('parser-default', parser_ok, [str(out)]) == b'v3d\n', 'Default profile changed')
        for profile in ['v3d', 'powervr-zink', 'radeonsi']:
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
            body = 'backend=virtual\nprofile=' + shlex.quote(profile) + '\n' + prerequisites.replace('/dev/dri/renderD*', shlex.join(nodes)).replace(ICD, shlex.quote(str(path)))
            script('prerequisite-' + str(index), body, expected=status)

        # Reproduce the former unquoted ICD assignment, even with a plain --work.
        spaced = work / 'renderer fixture'; spaced.mkdir()
        spaced_icd = spaced / 'installed ICD.json'; spaced_icd.write_text('{}\n')
        prefix = 'backend=virtual\nprofile=powervr-zink\n'
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
        for profile in ['v3d', 'powervr-zink', 'radeonsi']:
            for status in [0, 7]:
                directory = work / (profile + '-' + str(status)); directory.mkdir()
                backend = 'drm' if status == 7 else 'virtual'
                drm_output = 'eDP-1' if status == 7 else 'HDMI-A-1'
                body = 'work=' + shlex.quote(str(directory)) + '\ncd "$work"\nbackend=' + backend + '\nprofile=' + profile + '\ndrm_output=' + drm_output + '\naccount=fixture\nlogin_shell=/bin/sh\nicd=' + ICD + '\n'
                body += dispatch.replace('/usr/pkg/bin/perl ./guard.pl', 'TEST_EXIT=' + str(status) + ' ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(recorder)) + ' ./guard.pl')
                env = dict(os.environ, LD_LIBRARY_PATH='/untrusted', LD_PRELOAD='/untrusted', VK_ICD_FILENAMES='/untrusted', VK_DRIVER_FILES='/untrusted', GALLIUM_DRIVER='softpipe', KWIN_DRM_DEVICES='/untrusted')
                script('dispatch-' + profile + '-' + str(status), body, env=env)
                row = json.loads((directory / 'bus.log').read_text())
                require((directory / 'status').read_text().strip() == str(status), 'Guard status lost')
                require(row['argv'] == ['./guard.pl', str(directory), '240', '--', '/usr/pkg/bin/dbus-run-session', '--', '/bin/sh', './controller.sh'], 'Supervisor dispatch changed')
                for key, value in expected_power.items():
                    require(row['env'].get(key) == (value if profile == 'powervr-zink' else None), 'Incorrect environment: ' + key)
                for key in ['LD_LIBRARY_PATH', 'LD_PRELOAD', 'LIBGL_DRIVERS_PATH', 'VK_ICD_FILENAMES', 'QT_PLUGIN_PATH', 'QML_IMPORT_PATH', 'KWIN_DRM_DEVICES']:
                    require(key not in row['env'], 'Inherited private override: ' + key)
                require(row['env']['EMBER_PLASMA_RENDERER_PROFILE'] == profile, 'Profile lost at dispatch')
                require(row['env']['EMBER_PLASMA_BACKEND'] == backend, 'Backend lost at dispatch')
                require(row['env']['EMBER_PLASMA_EXPECTED_DRM_OUTPUT'] == drm_output,
                        'Expected DRM output lost at dispatch')

        # The controller must pass the selected profile at all three call sites.
        calls = [line for line in controller.splitlines() if line.startswith('/bin/sh ./check-results.sh ')]
        require(len(calls) == 3 and all(line.endswith(' "$profile"') for line in calls), 'Controller profile propagation changed')
        require('awk -v prefix="[$shell_pid] "' in controller, 'Actual shell PID filter lost')
        for profile, value in [('v3d', V3D), ('powervr-zink', POWER), ('radeonsi', RADEONSI)]:
            for name in ['support-before.txt', 'support-after.txt']:
                (work / name).write_text(support(value))
            (work / 'shell-renderer.log').write_text(qt(value))
            (work / 'check-results.sh').write_text(check_text)
            script('controller-checks-' + profile, 'profile=' + profile + '\n' + '\n'.join(calls) + '\n')

        # The backend enum is independent of renderer selection and option order.
        parser_backend = runner.split('[ "$(id -u)" -ne 0 ]', 1)[0]
        parser_backend += 'printf "%s %s %s\\n" "$backend" "$profile" "$drm_output"\n'
        for backend in ['virtual', 'drm']:
            for profile in ['v3d', 'powervr-zink', 'radeonsi']:
                orders = [['--backend', backend, '--renderer', profile],
                          ['--renderer', profile, '--backend', backend]]
                if backend == 'drm':
                    orders.extend([
                        ['--backend', backend, '--renderer', profile, '--output', 'eDP-1'],
                        ['--renderer', profile, '--output', 'eDP-1', '--backend', backend],
                    ])
                for order in orders:
                    expected_output = 'eDP-1' if '--output' in order else 'HDMI-A-1'
                    require(script('backend-parser-' + str(len(results)), parser_backend,
                                   [*order, str(out)]) == (backend + ' ' + profile + ' ' + expected_output + '\n').encode(),
                            'Backend/profile parser changed')
        for argv in [['--backend'], ['--backend', '', str(out)],
                     ['--backend', 'unknown', str(out)], ['--backend', 'drm'],
                     ['--backend', 'drm', '--backend', 'virtual', str(out)],
                     ['--backend', 'drm', str(out), '--renderer', 'v3d'],
                     ['--output'], ['--output', '', str(out)],
                     ['--output', 'eDP-1', str(out)],
                     ['--backend', 'virtual', '--output', 'eDP-1', str(out)],
                     ['--backend', 'drm', '--output', 'eDP/1', str(out)],
                     ['--backend', 'drm', '--output', 'eDP-1', '--output', 'HDMI-A-1', str(out)],
                     ['--backend', 'drm', '--output', 'A' * 33, str(out)],
                     ['--width', '1920', str(out)], ['--drm', str(out)]]:
            script('backend-parser-reject-' + str(len(results)), parser_backend, argv, 2)
            require(not out.exists(), 'Rejected backend created output')
        call('full-unknown-backend', ['/bin/sh', str(source / 'run.sh'), '--backend', 'unknown', str(out)], 2)
        call('full-output-on-virtual', ['/bin/sh', str(source / 'run.sh'), '--output', 'eDP-1', str(out)], 2)

        # Only target paths are replaced; real character/access/symlink tests run.
        for backend, nodes, expected in [
                ('drm', ['/dev/null'], 0), ('virtual', [str(regular)], 0),
                ('drm', [str(regular)], 2), ('drm', [str(link)], 2),
                ('drm', [str(work / 'absent-primary')], 2)]:
            body = 'backend=' + backend + '\nprofile=v3d\n' + prerequisites.replace(
                '/dev/dri/renderD*', '/dev/null').replace('/dev/dri/card*', shlex.join(nodes))
            script('backend-primary-' + str(len(results)), body, expected=expected)
        # Model only access(2) answers to cover unreadable/unwritable devices.
        primary_gate = 'primary_node=\n' + section(runner, 'primary_node=\n', 'icd=')
        for permission in ['-r', '-w']:
            before = '[ ' + permission + ' "$node" ]'
            require(primary_gate.count(before) == 1, 'Primary access boundary changed')
            script('primary-no-' + permission, 'backend=drm\n' + primary_gate.replace(
                '/dev/dri/card*', '/dev/null').replace(before, 'false'), expected=2)
        no_primary = prerequisites.replace('/dev/dri/renderD*', '/dev/null').replace(
            '/dev/dri/card*', shlex.quote(str(regular)))
        script('mutant-drop-primary-access', 'backend=drm\nprofile=v3d\n' + no_primary.replace(
            '[ -n "$primary_node" ] ||', 'true ||'), expected=0)
        # The same ordinary-user gate still precedes target access and launch.
        user_gate = '[ "$(id -u)" -ne 0 ] || { echo \'Run as an ordinary desktop user.\' >&2; exit 2; }'
        require(runner.count(user_gate) == 1, 'Ordinary-user gate changed')
        script('backend-root-refusal', 'id() { echo 0; }\n' + user_gate + '\n', expected=2)

        policy_start = 'backend=${EMBER_PLASMA_BACKEND-virtual}\n'
        policy = policy_start + section(controller, policy_start, 'cd "$EMBER_PLASMA_OUTPUT"\n')
        predicate = 'backend_check()\n' + section(controller, 'backend_check()\n', 'owner()\n')
        launch_start = 'case "$backend" in\nvirtual) set -- --virtual'
        launch = launch_start + section(controller, launch_start, 'wrapper=$!\n')
        require('KWIN_DRM_DEVICES=' not in runner and 'Noop' not in runner + controller,
                'Launcher must not override DRM device or seat policy')
        layout_word = next(line.strip().split(' > layout.txt')[0] for line in controller.splitlines()
                           if '"var emberExpectedWidth=' in line)
        layout = (source.parent / 'plasma-desktop/layout.js').read_text()
        layout_test = work / 'layout-test.js'
        layout_test.write_text(r'''
const fs = require('fs'), vm = require('vm');
const [file, width, height, outcome] = process.argv.slice(2);
let printed = '';
const ctx = {screenCount: 1, screenGeometry: () => ({width: +width, height: +height}),
 desktops: () => [{screen: 0, type: 'org.kde.plasma.folder'}],
 panels: () => [{screen: 0, type: 'org.kde.panel', widgets: () =>
 ['kickoff','pager','icontasks','systemtray','digitalclock','showdesktop'].map(n => ({type:'org.kde.plasma.'+n}))}],
 print: line => {printed = line;}};
let rejected = false;
try {vm.runInNewContext(fs.readFileSync(file, 'utf8'), ctx, {timeout:1000});} catch (_) {rejected = true;}
if (rejected !== (outcome === 'reject')) {console.error('FAIL: actual layout geometry outcome'); process.exit(1);}
if (!rejected && printed !== 'PASS: default desktop, panel and six applet models on '+width+'x'+height) {
 console.error('FAIL: actual layout evidence'); process.exit(1);
}
console.log('PASS: actual layout geometry');
''')
        wrapper = work / 'wrapper'
        wrapper.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > wrapper-arguments\n')
        wrapper.chmod(0o700)
        for backend, width, height, name, backend_name, drm_output in [
                ('virtual', 1280, 1024, 'Virtual-0', 'KWin::VirtualBackend', 'HDMI-A-1'),
                ('drm', 1920, 1080, 'HDMI-A-1', 'DRM', 'HDMI-A-1'),
                ('drm', 1920, 1080, 'eDP-1', 'DRM', 'eDP-1')]:
            env = dict(os.environ, EMBER_PLASMA_BACKEND=backend,
                       EMBER_PLASMA_EXPECTED_DRM_OUTPUT=drm_output)
            directory = work / ('launch-' + backend + '-' + name); directory.mkdir()
            actual_launch = launch.replace('/usr/pkg/bin/kwin_wayland_wrapper', shlex.quote(str(wrapper)))
            script('launch-' + backend, policy + 'cd ' + shlex.quote(str(directory)) + '\n' + actual_launch + 'wait "$!"\n', env=env)
            expected = (['--virtual', '--width', '1280', '--height', '1024'] if backend == 'virtual' else ['--drm'])
            expected += ['--xwayland', '--no-lockscreen', '/bin/sh ./environment.sh']
            require((directory / 'wrapper-arguments').read_text().splitlines() == expected,
                    'Actual backend launch arguments changed')
            output_record = section(controller, 'cd "$EMBER_PLASMA_OUTPUT"\n', 'phase=display-environment\n')
            policy_dir = work / ('output-policy-' + backend + '-' + name); policy_dir.mkdir()
            script('output-policy-' + backend + '-' + name,
                   policy + 'cd "$EMBER_PLASMA_OUTPUT"\n' + output_record,
                   env=dict(env, EMBER_PLASMA_OUTPUT=str(policy_dir)))
            require((policy_dir / 'output-policy.txt').read_text() ==
                    backend + ' ' + str(width) + ' ' + str(height) + ' ' +
                    ('Virtual-0' if backend == 'virtual' else drm_output) + '\n',
                    'Recorded output policy does not match the checked output')
            payload = work / ('layout-' + backend + '.js')
            (work / 'layout.js').write_text(layout)
            payload.write_bytes(script('layout-payload-' + backend, policy + 'printf "%s\\n" ' + layout_word + '\n', env=env))
            call('layout-' + backend, ['node', str(layout_test), str(payload), str(width), str(height), 'accept'])
            call('layout-wrong-' + backend, ['node', str(layout_test), str(payload), '800', '600', 'reject'])
            evidence = ('LogicalOutput backend\n==============\nName: ' + backend_name + '\n\nScreens\n=======\n'
                        'Number of Screens: 1\n\nScreen 0:\n---------\nName: ' + name + '\nEnabled: 1\n'
                        'Geometry: 0,0,' + str(width) + 'x' + str(height) + '\nScale: 1\nRefresh Rate: 60000\n\nCompositing\n')
            for phase in ['before', 'after']:
                f = work / ('backend-' + backend + '-' + phase + '.txt'); f.write_text(evidence)
                script('backend-' + backend + '-' + name + '-' + phase,
                       policy + predicate + 'backend_check "$1"\n', [str(f)], env=env)
            for label, bad in [
                    ('wrong-backend', evidence.replace('Name: ' + backend_name + '\n', 'Name: wrong-backend\n', 1)),
                    ('wrong-output', evidence.replace('Name: ' + name + '\n', 'Name: Virtual-99\n')),
                    ('wrong-mode', evidence.replace('Geometry: 0,0,', 'Geometry: 1,0,')),
                    ('wrong-size', evidence.replace('Geometry: 0,0,' + str(width), 'Geometry: 0,0,800')),
                    ('disabled', evidence.replace('Enabled: 1', 'Enabled: 0')),
                    ('scaled', evidence.replace('Scale: 1', 'Scale: 2')),
                    ('wrong-refresh', evidence.replace('Refresh Rate: 60000', 'Refresh Rate: 50000')),
                    ('duplicate', evidence.replace('Name: ' + name, 'Name: ' + name + '\nName: ' + name)),
                    ('two-screens', evidence.replace('Number of Screens: 1', 'Number of Screens: 2')),
                    ('unrelated', evidence.replace('LogicalOutput backend', 'unrelated'))]:
                f = work / ('backend-' + backend + '-' + name + '-' + label + '.txt'); f.write_text(bad)
                script('backend-' + backend + '-' + name + '-' + label,
                       policy + predicate + 'backend_check "$1"\n', [str(f)], 1, env)
            if backend == 'drm':
                wrong_launch = actual_launch.replace('drm) set -- --drm ;;', 'drm) set -- --virtual --width 1280 --height 1024 ;;')
                script('mutant-virtual-drm-launch', policy + 'cd ' + shlex.quote(str(directory)) + '\n' + wrong_launch + 'wait "$!"\n', env=env)
                require((directory / 'wrapper-arguments').read_text().splitlines() != expected,
                        'Wrong virtual-to-DRM launch mutant was not observed')
                bad = work / 'virtual-as-drm.txt'
                bad.write_text(evidence.replace('Name: DRM\n', 'Name: KWin::VirtualBackend\n'))
                mutant = predicate.replace('bad += ($0 != "Name: " expected_backend)', 'bad += 0')
                script('mutant-drop-backend-name', policy + mutant + 'backend_check "$1"\n', [str(bad)], 0, env)
                script('fixed-backend-name', policy + predicate + 'backend_check "$1"\n', [str(bad)], 1, env)
                # Exercise both actual support callers with renderer-valid
                # evidence from the wrong output backend. No KDE runs here.
                (work / 'check-results.sh').write_text(check_text)
                bad.write_text(bad.read_text() + support(V3D))
                for phase, end in [('before', 'count=0\n'), ('after', 'shell_pid=')]:
                    start = 'phase=support-' + phase + '\n'
                    caller = start + section(controller, start, end)
                    stub = 'query() { cat ' + shlex.quote(str(bad)) + '; }\nprofile=v3d\n'
                    script('caller-' + phase + '-wrong-backend', policy + predicate + stub + caller,
                           expected=1, env=env)
                    mutant_caller = caller.replace('backend_check support-' + phase + '.txt\n', '')
                    script('mutant-drop-' + phase + '-backend-gate', policy + predicate + stub + mutant_caller,
                           expected=0, env=env)
                mutant_payload = work / 'layout-mutant.js'
                mutant_payload.write_text(payload.read_text().replace('geometry.width === width && geometry.height === height', 'true'))
                row = len(results)
                call('mutant-drop-layout-size', ['node', str(layout_test), str(mutant_payload), '800', '600', 'reject'], 1)
                require('FAIL: actual layout geometry outcome' in results[row]['stderr'], 'Unrelated layout mutant failure')
        script('controller-unknown-backend', policy, env=dict(os.environ, EMBER_PLASMA_BACKEND='unknown'), expected=2)
        for phase in ['before', 'after']:
            require(controller.count('backend_check support-' + phase + '.txt\n') == 1,
                    'Missing actual backend evidence gate ' + phase)
        require(runner.count('EMBER_PLASMA_BACKEND="$backend"') == 1 and
                '"$backend" > backend.txt' in runner and '"$primary_node" > primary-node.txt' in runner,
                'Selected backend/evidence dispatch lost')

        # Compare preserved lifecycle source with the frozen parent revision.
        relative = source.relative_to(ports)
        old = lambda name: capture(['git', '-C', str(ports), 'show', BASELINE + ':' + str(relative / name)]).stdout.decode()
        original_controller = old('controller.sh')
        projected = controller
        projected = projected.replace('case "$profile" in v3d|powervr-zink|radeonsi) ;; *) exit 2 ;; esac\n',
                                       'case "$profile" in v3d|powervr-zink) ;; *) exit 2 ;; esac\n')
        projected = projected.replace('expected_drm_output=${EMBER_PLASMA_EXPECTED_DRM_OUTPUT-HDMI-A-1}\n', '')
        projected = projected.replace(
            'drm)\n    case "$expected_drm_output" in \'\'|*[!A-Za-z0-9_.-]*) exit 2 ;; esac\n'
            '    [ "${#expected_drm_output}" -le 32 ] || exit 2\n'
            '    width=1920; height=1080; output_name=$expected_drm_output; backend_name=DRM ;;',
            'drm) width=1920; height=1080; output_name=HDMI-A-1; backend_name=DRM ;;')
        projected = projected.replace(
            'printf \'%s %s %s %s\\n\' "$backend" "$width" "$height" "$output_name" > output-policy.txt',
            'printf \'%s %s %s\\n\' "$backend" "$width" "$height" > output-policy.txt')
        require(projected == original_controller, 'Controller changed outside profile plumbing')
        require((source / 'guard.pl').read_text() == old('guard.pl'), 'Supervisor changed')
        old_checker = work / 'baseline-checker.sh'
        old_checker.write_bytes(capture(['git', '-C', str(ports), 'show', BASELINE + ':' + str(checker.relative_to(ports))]).stdout)
        check('baseline-powervr-green', 'support', support(POWER), 'powervr-zink', selected=old_checker)
        check('baseline-v3d-green', 'renderer', qt(V3D), selected=old_checker)
        check('baseline-radeonsi-unknown', 'support', support(RADEONSI), 'radeonsi', 2, old_checker)
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
        for label, before, bad in [
            ('drop-radeonsi-name', 'lower !~ /(^|[^[:alnum:]_])radeonsi([^[:alnum:]_]|$)/', 'AMD Radeon Graphics (raven)'),
            ('drop-amd-name', 'lower !~ /(^|[^[:alnum:]_])(amd|radeon)([^[:alnum:]_]|$)/', 'radeonsi, raven'),
        ]:
            require(check_text.count(before) == 1, 'Radeon predicate mutation point changed')
            mutant = work / (label + '.sh'); mutant.write_text(check_text.replace(before, '0'))
            check('mutant-' + label, 'renderer', qt(bad), 'radeonsi', 0, mutant)
            check('fixed-' + label, 'renderer', qt(bad), 'radeonsi', 1)
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
