#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the real Node recipe and V8 hash consistency across translation units."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'distfile', 'git', 'patch', 'host-prefix', 'sdk-root',
                 'utility-path', 'link-launcher', 'lock-root', 'link-context', 'work'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--arch', choices=('arm64', 'x86_64'), required=True)
    parser.add_argument('--deployment-target', required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin' or platform.machine() != args.arch:
        parser.error('this regression executes the selected Darwin host architecture')
    if any(not value.is_absolute() for value in vars(args).values() if isinstance(value, Path)) or args.work.exists():
        parser.error('use absolute inputs and a new work directory')
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}', args.deployment_target):
        parser.error('invalid deployment target')
    prefix = args.host_prefix.resolve()
    for name in ('clang++', 'ld64.lld'):
        tool = prefix/'bin'/name
        if not tool.resolve().is_relative_to(prefix) or not os.access(tool, os.X_OK):
            parser.error('missing native prefix tool: '+str(tool))
    if not Path(sys.executable).resolve().is_relative_to(prefix):
        parser.error('run with the selected native prefix Python')
    args.work.mkdir()
    owner = Path(__file__).resolve().parents[3]
    env = dict(os.environ, PATH=str(args.utility_path), LC_ALL='C',
               GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', PATCH_VERSION_CONTROL='none')
    for name in ('PYTHONPATH', 'PYTHONHOME', 'CPATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH'):
        env.pop(name, None)
    counter = 0

    def run(name, command, cwd=None, input=None, success=True):
        nonlocal counter
        counter += 1
        result = subprocess.run([str(word) for word in command], cwd=cwd, env=env,
                                input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout+result.stderr
        (args.work/(str(counter)+'-'+name+'.log')).write_bytes(output)
        if success and result.returncode:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
        assert success or result.returncode, name+' unexpectedly succeeded'
        return result.stdout

    # Exercise the real common exporter, preserving its selected patch dialect.
    ports = args.work/'ports';upstream = ports/'upstream/pkgsrc'
    shutil.copytree(args.pkgsrc/'lang/nodejs24', upstream/'lang/nodejs24')
    outer_path = Path('profiles/common-build-tools/patches/pkgsrc-nodejs24-v8-hash.patch')
    outer = owner/outer_path
    destination = ports/outer_path;destination.parent.mkdir(parents=True);shutil.copyfile(outer, destination)
    payload_name = 'patch-deps_v8_std__hash'
    expected = re.search(r'^\+SHA1 \('+payload_name+r'\) = ([0-9a-f]{40})$', outer.read_text(), re.M).group(1)
    (ports/'pkgsrc').mkdir()
    already = (upstream/'lang/nodejs24/patches'/payload_name).is_file()
    (ports/'pkgsrc/export.conf').write_text('' if already else 'patch\t'+outer_path.as_posix()+'\n')
    for location in (upstream, ports):run('git-init', [args.git, '-C', location, 'init', '-q'])
    run('git-add', [args.git, '-C', upstream, 'add', 'lang/nodejs24'])
    run('git-commit', [args.git, '-C', upstream, '-c', 'user.name=Fixture',
        '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'])
    revision = run('git-revision', [args.git, '-C', upstream, 'rev-parse', 'HEAD']).decode().strip()
    run('git-export-index', [args.git, '-C', ports, 'add', 'pkgsrc/export.conf'])
    run('git-submodule-index', [args.git, '-C', ports, 'update-index', '--add', '--cacheinfo',
        '160000,'+revision+',upstream/pkgsrc'])
    spec = importlib.util.spec_from_file_location('ports_exporter', owner/'scripts/prepare-pkgsrc.py')
    exporter = importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
    selected = type('Tools', (), {'command':lambda self, role:(str(args.git if role=='git' else args.patch),)})()
    exported = args.work/'exported'
    def control(command, *, cwd=None, input=None):
        return run('export', command, cwd=cwd, input=input)
    assert exporter.export_pkgsrc(ports, exported, selection=selected, runner=control,
                                  scratch=args.work/'export-scratch') == revision
    recipe = exported/'lang/nodejs24'
    payload = b''.join(line for line in (recipe/'patches'/payload_name).read_bytes().splitlines(keepends=True)
                       if b'$NetBSD' not in line)
    assert hashlib.sha1(payload).hexdigest() == expected
    assert int(re.search(r'^PKGREVISION=\s*(\d+)$', (recipe/'Makefile').read_text(), re.M).group(1)) >= 6
    # Reuse the existing source checksum, full patch-series and configure/GYP
    # regression. Its extraction contains every production patch target.
    run('source', [sys.executable, '-B', '-I', '-S',
        owner/'profiles/common-build-tools/tests/node-python315.py', '--pkgsrc', exported,
        '--distfile', args.distfile, '--patch', args.patch, '--work', args.work/'source-check'])
    source = args.work/'source-check/node-v24.22.1'
    original = args.work/'original-headers/src/base';original.mkdir(parents=True)
    # Add only unmodified header dependencies; never overwrite patched targets.
    with tarfile.open(args.distfile, 'r|xz') as archive:
        for member in archive:
            top, _, relative = member.name.partition('/')
            assert top == source.name
            if relative == 'deps/v8/src/base/hashing.h':
                (original/'hashing.h').write_bytes(archive.extractfile(member).read())
            if relative.endswith('.h') and relative.startswith(('deps/v8/src/base/', 'deps/v8/include/')):
                destination = source/relative
                if not destination.exists():archive.extract(member, source.parent, filter='data')
    canonical = (source/'deps/v8/src/wasm/canonical-types.h').read_text()
    assert 'std::unordered_set<CanonicalGroup, base::hash<CanonicalGroup>>' in canonical
    assert 'base::hash<CanonicalSingletonGroup>>' in canonical
    # The older profiler is not an adapted patch target; inspect its pinned
    # source directly to prove why upstream's newer pair-map hunk is omitted.
    with tarfile.open(args.distfile, 'r|xz') as archive:
        for member in archive:
            if member.name == source.name+'/deps/v8/src/profiler/profile-generator.h':
                text = archive.extractfile(member).read().decode()
                assert 'std::unordered_map<int, int> line_ticks_;' in text
                assert 'line_and_column_ticks_' not in text
                break
        else:raise AssertionError('missing pinned profiler header')
    fixture = args.work/'fixture';fixture.mkdir()
    (fixture/'insert.cc').write_text('''#include <unordered_set>
extern "C" void insert(std::unordered_set<int>* values, int value) { values->insert(value); }
extern "C" size_t external_hash(int value) { return std::hash<int>{}(value); }
''')
    (fixture/'lookup.cc').write_text('''#include "src/base/hashing.h"
#include <unordered_map>
#include <unordered_set>
extern "C" bool lookup(const std::unordered_set<int>* values, int value) { return values->find(value) != values->end(); }
extern "C" size_t v8_tu_hash(int value) { return std::hash<int>{}(value); }
struct Key { int value; size_t hash_value() const { return v8::base::hash<int>{}(value); } bool operator==(const Key&) const = default; };
extern "C" bool explicit_v8_hash() {
  std::unordered_set<Key, v8::base::hash<Key>> keys; keys.insert(Key{7});
  std::unordered_map<std::pair<int,int>, int, v8::base::hash<std::pair<int,int>>> pairs;
  pairs[{1,2}] = 3; return keys.contains(Key{7}) && pairs.at({1,2}) == 3;
}
''')
    (fixture/'main.cc').write_text('''#include <cstdio>
#include <unordered_set>
extern "C" void insert(std::unordered_set<int>*, int);
extern "C" bool lookup(const std::unordered_set<int>*, int);
extern "C" size_t external_hash(int);
extern "C" size_t v8_tu_hash(int);
extern "C" bool explicit_v8_hash();
int main() { std::unordered_set<int> values; insert(&values,1); bool found=lookup(&values,1);
printf("size=%zu found=%d external_hash=%zu v8_tu_hash=%zu explicit=%d\\n",values.size(),found,external_hash(1),v8_tu_hash(1),explicit_v8_hash());
return !found || external_hash(1)!=v8_tu_hash(1) || !explicit_v8_hash(); }
''')
    compiler = [prefix/'bin/clang++', '-isysroot', args.sdk_root, '-arch', args.arch,
        '-mmacosx-version-min='+args.deployment_target, '-std=c++20', '-stdlib=libc++', '-O2',
        '-fno-exceptions', '-fno-rtti']
    link = [sys.executable, '-B', args.link_launcher, '--lock-root', args.lock_root,
            '--context', args.link_context, '--', *compiler, '--ld-path='+str(prefix/'bin/ld64.lld')]
    results = {}
    for route in ('original','fixed'):
        folder = args.work/route;folder.mkdir()
        includes = [] if route == 'fixed' else ['-I'+str(original.parents[1])]
        includes += ['-I'+str(source/'deps/v8'), '-I'+str(source/'deps/v8/include')]
        objects = []
        for name in ('insert','lookup','main'):
            obj=folder/(name+'.o');objects.append(obj)
            run(route+'-'+name, [*compiler, *includes, '-c', fixture/(name+'.cc'), '-o', obj])
        run(route+'-link', [*link,*objects,'-o',folder/'check'])
        output = run(route+'-runtime', [folder/'check'], success=route=='fixed').decode().strip()
        results[route] = output
    assert 'found=0' in results['original'] and 'explicit=1' in results['original']
    assert 'found=1' in results['fixed'] and 'explicit=1' in results['fixed']
    summary = {'checks':['common exporter and recipe checksum','complete source patch series',
        'applicable upstream custom hash consumers','two-TU original failure/fixed success',
        'explicit V8 custom and pair hash behavior'], 'runtime':results,
        'scope':'native Clang/libc++ causal regression; full ordinary Node rebuild and runtime suites remain separate'}
    (args.work/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
