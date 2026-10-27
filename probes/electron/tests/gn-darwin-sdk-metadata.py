#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), not submitted upstream.
"""Run pinned Chromium mac_sdk.gni with the shared SDK reader and real GN/Ninja.

Compiler tools are not invoked. This proves metadata selection/regeneration,
not a complete Electron build or Darwin/EmberBSD binary compatibility.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import time

PROBE = Path(__file__).resolve().parents[1]
MEMBER = 'build/config/mac/mac_sdk.gni'
PATCH = PROBE / 'patches/gn-darwin-sdk-metadata.patch'


def gn_string(value):
    return json.dumps(str(value), ensure_ascii=False).replace('$', r'\$')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'sdk-source', 'macos-sdk', 'xcode-version-plist', 'native-bin', 'git', 'gn', 'ninja', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if not all(path.is_absolute() for path in vars(args).values()):
        parser.error('all inputs and output must be absolute')
    if args.work.exists() or args.work.resolve().is_relative_to(args.source.resolve()):
        parser.error('work must be new and outside source')
    if sys.version_info[:2] != (3, 15):
        parser.error('use selected CPython 3.15')
    args.work.mkdir(parents=True)
    empty = args.work / 'empty-path'; empty.mkdir()
    environment = {'PATH': str(empty), 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
    logs = args.work / 'logs'; logs.mkdir()
    results = []

    def run(name, argv, cwd, error=None):
        proc = subprocess.run(list(map(str, argv)), cwd=cwd, env=environment,
                              capture_output=True, text=True, timeout=60)
        output = proc.stdout + proc.stderr
        (logs / (name + '.log')).write_text(output)
        results.append(dict(case=name, argv=list(map(str, argv)), exit_code=proc.returncode))
        (args.work / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
        if error is None:
            assert proc.returncode == 0, name + ':\n' + output
        else:
            assert proc.returncode != 0 and error in output, name + ':\n' + output
        return output

    spec = importlib.util.spec_from_file_location('source_prepare', PROBE / 'electron44/files/prepare-sources.py')
    prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)
    pinned = run('read-pinned-gni', [args.git, '-C', args.source, 'show', prepare.CHROMIUM_REVISION + ':' + MEMBER], args.work)
    assert pinned.encode() == (args.source / MEMBER).read_bytes(), 'prepared mac_sdk.gni is not pinned leaf'
    before = hashlib.sha256((args.source / MEMBER).read_bytes()).hexdigest()
    baseline = args.work / 'baseline'
    target = baseline / MEMBER; target.parent.mkdir(parents=True); target.write_text(pinned)
    legacy = 'build/config/apple/sdk_info.py'
    (baseline / legacy).parent.mkdir(parents=True, exist_ok=True)
    (baseline / legacy).write_text(run('read-pinned-discovery', [args.git, '-C', args.source, 'show', prepare.CHROMIUM_REVISION + ':' + legacy], args.work))
    patched = args.work / 'patched'; shutil.copytree(baseline, patched)
    run('patch-check', [args.git, 'apply', '--check', PATCH], patched)
    run('patch-apply', [args.git, 'apply', PATCH], patched)
    defaults = dict(emberbsd_sdk_source=str(args.sdk_source),
                    emberbsd_xcode_version_plist=str(args.xcode_version_plist),
                    emberbsd_mac_toolchain_bin=str(args.native_bin), mac_sdk_path=str(args.macos_sdk),
                    mac_sdk_min='15')

    def fixture(name, overrides=None, *, original=False, explicit=True, error=None):
        root = args.work / name; shutil.copytree(baseline if original else patched, root)
        gni = (root / MEMBER).read_text()
        for line in gni.splitlines():
            if not line.startswith('import("//'):
                continue
            imported = root / line.split('"')[1][2:]
            imported.parent.mkdir(parents=True, exist_ok=True)
            if imported.name == 'mac_sdk_overrides.gni':
                imported.write_text('declare_args() { mac_sdk_min = "15" }\n')
            else:
                imported.write_text('')
        (root / '.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\nscript_executable = '+gn_string(sys.executable)+'\n')
        (root / 'BUILDCONFIG.gn').write_text('''current_os = "mac"
target_os = "netbsd"
is_chrome_branded = false
is_official_build = false
use_system_xcode = true
set_default_toolchain("//:native")
''')
        fields = ('mac_sdk_path','mac_sdk_version','mac_sdk_build_version','mac_bin_path','xcode_version','xcode_version_int','xcode_build')
        body='import("//'+MEMBER+'")\nselected = {\n'+''.join('  '+field+' = '+field+'\n' for field in fields)+'}\nwrite_file("$root_build_dir/selected.json", selected, "json")\n'
        body+='toolchain("native") {\n  tool("stamp") {\n    command = '+gn_string(str(Path(sys.executable))+' -c "import pathlib; pathlib.Path(\'{{output}}\').touch()"')+'\n    description = "fixture stamp"\n  }\n}\ngroup("default") {}\n'
        (root / 'BUILD.gn').write_text(body)
        out=root/'out';out.mkdir()
        values=defaults.copy() if explicit else {}
        values.update(overrides or {})
        (out/'args.gn').write_text(''.join(key+' = '+gn_string(value)+'\n' for key,value in values.items()))
        run(name, [args.gn,'gen',out], root,error)
        return root

    actual=fixture('actual-sdk')
    measured=json.loads((actual/'out/selected.json').read_text())
    with (args.macos_sdk/'SDKSettings.plist').open('rb') as stream: settings=plistlib.load(stream)
    with (args.macos_sdk/'System/Library/CoreServices/SystemVersion.plist').open('rb') as stream: system=plistlib.load(stream)
    with args.xcode_version_plist.open('rb') as stream: xcode=plistlib.load(stream)
    parts=(xcode['CFBundleShortVersionString'].split('.')+['0','0'])[:3]
    formatted=('%2s%s%s'%tuple(parts)).replace(' ','0')
    expected=dict(mac_sdk_path=str(args.macos_sdk.resolve()),mac_sdk_version=settings['Version'],
                  mac_sdk_build_version=system['ProductBuildVersion'],mac_bin_path=str(args.native_bin.resolve())+'/',
                  xcode_version=formatted,xcode_version_int=int(formatted),xcode_build=xcode['ProductBuildVersion'])
    assert measured==expected,(measured,expected)
    # A process audit also rejects absolute Apple/tool invocations that an
    # empty PATH alone would not catch. The adapter is a pure metadata reader.
    guard = args.work / 'no-process.py'
    guard.write_text("import runpy,sys\ndef audit(event,args):\n if event.startswith(('subprocess.', 'os.spawn', 'os.posix_spawn')) or event == 'os.system': raise RuntimeError('metadata attempted a child process')\nsys.addaudithook(audit)\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name='__main__')\n")
    run('adapter-no-process', [sys.executable, '-B', '-I', '-S', guard,
        patched/'build/config/apple/emberbsd_sdk_info.py',
        '--sdk-source',args.sdk_source,'--macos-sdk',args.macos_sdk,
        '--xcode-version-plist',args.xcode_version_plist,'--minimum-sdk','15',
        '--toolchain-bin',args.native_bin],args.work)
    invalid_sdk=args.work/'incompatible-sdk'
    shutil.copytree(args.sdk_source/'src/emberbsd_sdk',invalid_sdk/'src/emberbsd_sdk')
    reader=invalid_sdk/'src/emberbsd_sdk/darwin_sdk.py'
    reader.write_text(reader.read_text().replace('DARWIN_SDK_API = 1','DARWIN_SDK_API = 2'))
    fixture('incompatible-sdk-reader',{'emberbsd_sdk_source':str(invalid_sdk)},error='Darwin SDK API 1')
    reader.write_text(reader.read_text().replace('DARWIN_SDK_API = 2', '# API intentionally absent'))
    fixture('missing-sdk-reader-api',{'emberbsd_sdk_source':str(invalid_sdk)},error='Darwin SDK API 1')
    for field in ('emberbsd_sdk_source','emberbsd_xcode_version_plist','emberbsd_mac_toolchain_bin','mac_sdk_path'):
        fixture('missing-'+field,{field:''},error='Explicit Darwin metadata needs')
    fixture('minimum-too-new',{'mac_sdk_min':'99'},error='older than the requested minimum')
    fixture('relative-tool-directory',{'emberbsd_mac_toolchain_bin':'tools'},error='absolute native toolchain bin')
    fixture('missing-tool-directory',{'emberbsd_mac_toolchain_bin':str(args.work/'missing-tools')},error='absolute native toolchain bin')
    fixture('upstream-default',explicit=False,error='xcodebuild')
    fixture('upstream-unpatched-control',original=True,explicit=False,error='xcodebuild')

    # Real plist parsing, adversarial numeric comparison and GN dependencies.
    # This metadata-only fixture has no headers/libraries and is not an ABI SDK.
    sdk=args.work/'metadata fixture $/MacOSX.sdk';sdk.mkdir(parents=True)
    (sdk/'System/Library/CoreServices').mkdir(parents=True)
    fixture_settings=dict(settings,Version='27.9',CanonicalName='macosx27.9')
    fixture_system=dict(system,ProductVersion='27.9')
    (sdk/'SDKSettings.plist').write_bytes(plistlib.dumps(fixture_settings))
    (sdk/'System/Library/CoreServices/SystemVersion.plist').write_bytes(plistlib.dumps(fixture_system))
    plist=args.work/'metadata fixture $/Xcode version.plist';plist.write_bytes(plistlib.dumps(dict(xcode,CFBundleShortVersionString='9.3')))
    changes=dict(mac_sdk_path=str(sdk),emberbsd_xcode_version_plist=str(plist))
    fixture('numeric-minimum',{**changes,'mac_sdk_min':'27.10'},error='older than the requested minimum')
    regeneration=fixture('metadata-regeneration',{**changes,'mac_sdk_min':'27.9'})
    selected=json.loads((regeneration/'out/selected.json').read_text())
    assert selected['xcode_version']=='0930' and selected['xcode_version_int']==930
    # A change to one declared plist must cause Ninja's GN regeneration.
    time.sleep(1.1)
    plist.write_bytes(plistlib.dumps(dict(xcode,CFBundleShortVersionString='10.0')))
    run('ninja-metadata-regeneration',[args.ninja,'-C',regeneration/'out'],regeneration)
    selected=json.loads((regeneration/'out/selected.json').read_text())
    assert selected['xcode_version']=='1000' and selected['xcode_version_int']==1000
    bad=dict(fixture_system,ProductVersion='27.8')
    (sdk/'System/Library/CoreServices/SystemVersion.plist').write_bytes(plistlib.dumps(bad))
    fixture('inconsistent-plists',changes,error='metadata versions disagree')
    assert before==hashlib.sha256((args.source/MEMBER).read_bytes()).hexdigest(), 'source mutated'
    print('Pinned GN metadata routing, actual plists, partial-input refusals, numeric minimum and Ninja regeneration passed; no compilation.')


if __name__=='__main__':
    main()
