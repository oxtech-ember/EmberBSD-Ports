#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Generate, build and run a tiny Darwin target with selected Node GYP metadata."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'distfile', 'patch', 'work', 'host-prefix', 'sdk-root',
                 'xcode-version-plist', 'utility-path', 'makeconf', 'git'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--arch', choices=('arm64', 'x86_64'), required=True)
    parser.add_argument('--deployment-target', required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin' or platform.machine() != args.arch:
        parser.error('this regression builds and executes the current Darwin host architecture')
    if not args.work.is_absolute() or args.work.exists():
        parser.error('use a new absolute work directory')
    for path in (args.host_prefix, args.sdk_root, args.xcode_version_plist, args.utility_path, args.makeconf):
        if not path.is_absolute() or not path.exists():
            parser.error('missing absolute input: ' + str(path))
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}', args.deployment_target):
        parser.error('invalid deployment target')
    prefix = args.host_prefix.resolve()
    for name in ('clang', 'clang++', 'ld64.lld', 'llvm-libtool-darwin', 'gmake', 'bmake', 'mksh'):
        tool = prefix/'bin'/name
        if not tool.resolve().is_relative_to(prefix) or not os.access(tool, os.X_OK):
            parser.error('missing selected prefix tool: ' + str(tool))
    if not Path(sys.executable).resolve().is_relative_to(prefix):
        parser.error('run with the selected prefix Python')
    args.work.mkdir()
    owner = Path(__file__).resolve().parents[1]
    view = args.work/'view'
    recipe = view/'lang/nodejs24'
    view.mkdir()
    (view/'lang').mkdir()
    for path in args.pkgsrc.iterdir():
        if path.name != 'lang':
            (view/path.name).symlink_to(path.resolve(), target_is_directory=path.is_dir())
    for path in (args.pkgsrc/'lang').iterdir():
        if path.name != 'nodejs24':
            (view/'lang'/path.name).symlink_to(path.resolve(), target_is_directory=path.is_dir())
    env = dict(os.environ, PATH=str(args.utility_path), PYTHONDONTWRITEBYTECODE='1')
    for name in ('PYTHONPATH', 'PYTHONHOME', 'GYP_GENERATORS', 'GYP_DEFINES'):
        env.pop(name, None)

    def run(name, command, cwd, environment=env):
        result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True)
        (args.work/(name+'.log')).write_text(result.stdout + result.stderr)
        return result

    # Run the actual common exporter on a pinned local Git fixture containing
    # the supplied recipe. It must apply infrastructure patches with its own
    # -p1/capability contract, not a separate approximation in this regression.
    if not args.git.is_absolute() or not os.access(args.git, os.X_OK):
        parser.error('select an absolute executable source-control Git')
    ports = args.work/'export-fixture/ports'
    upstream = ports/'upstream/pkgsrc'
    initial = upstream/'lang/nodejs24'
    shutil.copytree(args.pkgsrc/'lang/nodejs24', initial)
    patch_name = 'patch-tools_gyp_pylib_gyp_xcode__emulation.py'
    outer = owner/'patches/pkgsrc-nodejs24-darwin-metadata.patch'
    selected_patches = []
    if not (initial/'patches/patch-tools_gyp_pylib_gyp_input.py').is_file():
        selected_patches.append(owner/'patches/pkgsrc-nodejs24-python315.patch')
    if 'GYP_MACOS_SDK_PATH' not in (initial/'patches'/patch_name).read_text():
        selected_patches.append(outer)
    (ports/'pkgsrc').mkdir()
    lines = []
    for path in selected_patches:
        relative = path.relative_to(owner.parents[1])
        destination = ports/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        lines.append('patch\t'+relative.as_posix()+'\n')
    (ports/'pkgsrc/export.conf').write_text(''.join(lines))
    control_env = dict(env, LC_ALL='C', GIT_OPTIONAL_LOCKS='0',
                       GIT_NO_LAZY_FETCH='1', PATCH_VERSION_CONTROL='none')

    def control(command, *, cwd=None, input=None):
        result = subprocess.run(command, cwd=cwd, input=input, env=control_env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with (args.work/'common-export.log').open('a') as log:
            log.write(shlex.join(str(word) for word in command)+'\n')
            log.write((result.stdout+result.stderr).decode(errors='replace'))
        result.check_returncode()
        return result.stdout

    for location in (upstream, ports):
        control([str(args.git), '-C', str(location), 'init', '-q'])
    control([str(args.git), '-C', str(upstream), 'add', 'lang/nodejs24'])
    control([str(args.git), '-C', str(upstream), '-c', 'user.name=Fixture',
             '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'])
    revision = control([str(args.git), '-C', str(upstream), 'rev-parse', 'HEAD']).decode().strip()
    control([str(args.git), '-C', str(ports), 'add', 'pkgsrc/export.conf'])
    control([str(args.git), '-C', str(ports), 'update-index', '--add', '--cacheinfo',
             '160000,'+revision+',upstream/pkgsrc'])
    spec = importlib.util.spec_from_file_location('ports_exporter', owner.parents[1]/'scripts/prepare-pkgsrc.py')
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    selected = type('SelectedTools', (), {'command': lambda self, role:
                    (str(args.git if role == 'git' else args.patch),)})()
    exported = args.work/'exported-recipe'
    assert exporter.export_pkgsrc(ports, exported, selection=selected, runner=control,
                                  scratch=args.work/'export-scratch') == revision
    shutil.copytree(exported/'lang/nodejs24', recipe)
    expected = re.search(r'^\+SHA1 \(' + re.escape(patch_name) + r'\) = ([0-9a-f]{40})$',
                         outer.read_text(), re.MULTILINE).group(1)
    payload = b''.join(line for line in (recipe/'patches'/patch_name).read_bytes().splitlines(keepends=True)
                       if b'$NetBSD' not in line)
    assert hashlib.sha1(payload).hexdigest() == expected
    # Reuse the real checksum/patch/configure/GYP source regression. It extracts
    # the scripts and all patch targets, not Node's unrelated large test tree.
    result = run('source', [sys.executable, '-B', '-I', '-S',
                 str(owner/'tests/node-python315.py'), '--pkgsrc', str(view),
                 '--distfile', str(args.distfile), '--patch', str(args.patch),
                 '--work', str(args.work/'source-check')], args.work)
    assert not result.returncode, result.stdout+result.stderr
    source = args.work/'source-check/node-v24.22.1'
    env.update(GYP_MACOS_SDK_PATH=str(args.sdk_root),
               GYP_XCODE_VERSION_PLIST=str(args.xcode_version_plist),
               GYP_LIBTOOL=str(prefix/'bin/llvm-libtool-darwin'))
    flags = ['-isysroot', str(args.sdk_root), '-mmacosx-version-min='+args.deployment_target,
             '--start-no-unused-arguments', '--ld-path='+str(prefix/'bin/ld64.lld'),
             '--end-no-unused-arguments']
    for name, compiler in (('CC', 'clang'), ('CXX', 'clang++'), ('LINK', 'clang++')):
        env[name] = shlex.join([str(prefix/'bin'/compiler), *flags])
    launcher = args.work/'run-gyp.py'
    launcher.write_text('''import runpy,sys
script=sys.argv[1];sys.argv=sys.argv[1:]
def forbid(event,args):
    if event == "subprocess.Popen":
        raise RuntimeError("undeclared metadata subprocess: "+str(args[0]))
sys.addaudithook(forbid)
runpy.run_path(script,run_name="__main__")
''')

    def generate(name, environment, sdk='macosx'):
        directory = args.work/name
        directory.mkdir()
        (directory/'answer.c').write_text('int answer(void) { return 42; }\n')
        (directory/'main.cc').write_text('#include <vector>\nextern "C" int answer(void);\n'
            'int main() { std::vector<int> n{40,2}; return n[0]+n[1] == answer() ? 0 : 1; }\n')
        settings = {'ARCHS': [args.arch], 'SDKROOT': sdk,
                    'MACOSX_DEPLOYMENT_TARGET': args.deployment_target,
                    'CLANG_CXX_LANGUAGE_STANDARD': 'c++20'}
        fixture = {'target_defaults': {'default_configuration': 'Release',
                   'configurations': {'Release': {'xcode_settings': settings}}},
                   'targets': [{'target_name': 'answer', 'type': 'static_library', 'sources': ['answer.c']},
                               {'target_name': 'probe', 'type': 'executable', 'sources': ['main.cc'],
                                'dependencies': ['answer']}]}
        build = directory/'fixture.gyp'
        build.write_text(repr(fixture)+'\n')
        result = run(name, [sys.executable, '-B', str(launcher),
                     str(source/'tools/gyp/gyp_main.py'), '-f', 'make-mac',
                     '--depth='+str(directory), str(build)], directory, environment)
        return result, directory

    # Inspect the real recipe's configure and regeneration environment, including
    # shell quoting of an explicit metadata filename containing spaces.
    quoted_plist = args.work/'metadata with spaces/version.plist'
    quoted_plist.parent.mkdir()
    shutil.copy2(args.xcode_version_plist, quoted_plist)
    bmake = [str(prefix/'bin/bmake'), '-m', str(prefix/'share/mk'),
             'SHELL='+str(prefix/'bin/mksh'), 'MAKECONF='+str(args.makeconf),
             'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'NODE_GYP_XCODE_VERSION_PLIST='+str(quoted_plist),
             'WRKOBJDIR='+str(args.work/'pkgsrc-obj'), 'DISTDIR='+str(args.distfile.parent),
             '-C', str(recipe)]
    result = run('recipe-metadata', bmake+['-V', '${CONFIGURE_ENV}', '-V', '${MAKE_ENV}'], args.work)
    assert not result.returncode, result.stdout+result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 2, result.stdout
    for line in lines:
        assignments = shlex.split(line)
        assert 'GYP_MACOS_SDK_PATH='+str(args.sdk_root) in assignments
        assert 'GYP_XCODE_VERSION_PLIST='+str(quoted_plist) in assignments
    unselected_makeconf = args.work/'unselected.mk.conf'
    unselected_makeconf.write_text('LOCALBASE='+str(prefix)+'\nPKGSRC_COMPILER=clang\n'
                                  'PYTHON_VERSION_DEFAULT=315\nOSX_SDK_PATH='+str(args.sdk_root)+'\n'
                                  'MACOSX_DEPLOYMENT_TARGET='+args.deployment_target+'\n')
    unselected_env = dict(env)
    for name in ('EMBERBSD_DARWIN_BOOTSTRAP', 'NODE_GYP_XCODE_VERSION_PLIST',
                 'EMBERBSD_DARWIN_XCODE_VERSION_PLIST'):
        unselected_env.pop(name, None)
    unselected = [word for word in bmake if not word.startswith(
                  ('EMBERBSD_DARWIN_BOOTSTRAP=', 'NODE_GYP_XCODE_VERSION_PLIST=', 'MAKECONF='))]
    unselected += ['MAKECONF='+str(unselected_makeconf), '-V', '${_NODE_GYP_METADATA_ENV:U}']
    result = run('recipe-unselected-metadata', unselected, args.work, unselected_env)
    assert not result.returncode and not result.stdout.strip(), result.stdout+result.stderr
    source_only = [word if not word.startswith('NODE_GYP_XCODE_VERSION_PLIST=') else
                   'NODE_GYP_XCODE_VERSION_PLIST='+str(args.work/'absent-for-checksum.plist')
                   for word in bmake]
    result = run('recipe-checksum-without-metadata', source_only+['checksum'], args.work)
    assert not result.returncode, result.stdout+result.stderr
    legacy = dict(env)
    legacy.pop('GYP_MACOS_SDK_PATH')
    legacy.pop('GYP_XCODE_VERSION_PLIST')
    for name, sdk, command in (('legacy-sdk-search', 'macosx', 'xcrun'),
                               ('legacy-version-search', str(args.sdk_root), 'xcodebuild')):
        result, _ = generate(name, legacy, sdk)
        assert result.returncode and 'undeclared metadata subprocess: '+command in result.stderr
    negatives = 0
    for key in ('GYP_MACOS_SDK_PATH', 'GYP_XCODE_VERSION_PLIST'):
        missing = dict(env)
        missing.pop(key)
        result, _ = generate('missing-'+key.lower(), missing)
        assert result.returncode and 'must both be absolute paths' in result.stderr
        assert 'undeclared metadata subprocess' not in result.stderr
        negatives += 1
    for name, value, diagnostic in (
            ('relative-plist', 'version.plist', 'must both be absolute paths'),
            ('absent-plist', str(args.work/'absent.plist'), 'Cannot read selected macOS metadata'),
            ('invalid-plist', str(args.work/'invalid.plist'), 'Cannot read selected macOS metadata')):
        (args.work/'invalid.plist').write_bytes(b'not a plist')
        broken = dict(env, GYP_XCODE_VERSION_PLIST=value)
        result, _ = generate(name, broken)
        assert result.returncode and diagnostic in result.stderr
        assert 'undeclared metadata subprocess' not in result.stderr
        negatives += 1
    for name, sdk in (('other-sdk-name', 'iphonesimulator'), ('other-sdk-path', '/not-the-selected-sdk')):
        result, _ = generate(name, env, sdk)
        assert result.returncode and 'SDKROOT does not match GYP_MACOS_SDK_PATH' in result.stderr
        assert 'undeclared metadata subprocess' not in result.stderr
        negatives += 1
    result, directory = generate('selected', env)
    assert not result.returncode, result.stdout+result.stderr
    result = run('build', [str(prefix/'bin/gmake'), '-j1', 'V=1'], directory)
    assert not result.returncode, result.stdout+result.stderr
    for tool in ('clang', 'clang++', 'llvm-libtool-darwin'):
        assert str(prefix/'bin'/tool) in result.stdout
    assert str(args.sdk_root) in result.stdout
    result = run('native-run', [str(directory/'out/Release/probe')], directory)
    assert not result.returncode, result.stdout+result.stderr
    summary = {'source': 'Node24.22.1', 'metadata_negative_cases': negatives,
               'legacy_metadata_search_refused': ['xcrun', 'xcodebuild'],
               'actual_common_exporter': True,
               'actual_pkgsrc_configure_and_make_metadata_quoting': True,
               'actual_pkgsrc_checksum_without_metadata': True,
               'actual_unselected_pkgsrc_route_unchanged': True,
               'actual_gyp_make_generation_without_subprocesses': True,
               'actual_selected_clang_c_cpp_archive_link_run': True,
               'scope': 'tiny native Darwin target; not a Node package build or target runtime check'}
    (args.work/'result.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
