#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check pkg-config flags reach Darwin GYP rules in a disposable Node source."""
import argparse
import ast
import json
import os
import re
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import types

parser = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'prefix', 'sdk', 'xcode-version-plist'):
    parser.add_argument('--' + name, type=Path, required=True)
a = parser.parse_args()
source = a.source.resolve(strict=True)
prefix = a.prefix.resolve(strict=True)
pkg = prefix / 'bin/pkg-config'
env = os.environ.copy()
env.update(PATH=str(prefix / 'bin') + ':' + str(prefix / 'sbin'),
           CC=str(prefix / 'bin/clang'), CXX=str(prefix / 'bin/clang++'),
           CARGO=str(prefix / 'bin/cargo'), PKG_CONFIG_PATH=str(prefix / 'lib/pkgconfig'),
           GYP_MACOS_SDK_PATH=str(a.sdk), GYP_XCODE_VERSION_PLIST=str(a.xcode_version_plist),
           GYP_LIBTOOL=str(prefix / 'bin/llvm-libtool-darwin'))
# Exercise the actual configuration function with metadata, an explicit
# override and missing metadata. Other shared providers retain upstream rules.
tree = ast.parse((source / 'configure.py').read_text())
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == 'configure_library')
module = ast.Module(body=[function], type_ignores=[])
for explicit, metadata, want in ((None, '-lada -lada-idna', ['-lada', '-lada-idna']),
                                 ('custom,extra', '-lada -lada-idna', ['-lcustom', '-lextra']),
                                 (None, None, ['-lada'])):
    options = types.SimpleNamespace(shared_ada=True, shared_ada_libname=explicit,
                                    shared_ada_includes=None, shared_ada_libpath=None)
    scope = {'options': options, 'b': lambda value: 'true' if value else 'false',
             'pkg_config': lambda _: (metadata, None, None, None),
             'pkg_config_other_cflags': lambda _: [], 'flavor': 'mac'}
    exec(compile(module, str(source / 'configure.py'), 'exec'), scope)
    result = {'variables': {}, 'libraries': []}
    scope['configure_library']('ada', result, fallback_lib='ada')
    assert result['libraries'] == want

packages = ('libhwy', 'simdjson')
expected = set()
for package in packages:
    result = subprocess.check_output([str(pkg), '--cflags-only-other', package], env=env, text=True)
    expected.update(flag for flag in shlex.split(result) if flag.startswith('-D'))
assert expected, 'selected shared packages must publish compile definitions'
with tempfile.TemporaryDirectory(prefix='node-pkgconfig-') as d:
    wrapper = Path(d) / 'pkg-config'
    wrapper.write_text('#!' + sys.executable + '\n' +
        'import subprocess,sys\n' +
        'r=subprocess.run([' + repr(str(pkg)) + ',*sys.argv[1:]],capture_output=True)\n' +
        'sys.stdout.buffer.write(r.stdout);sys.stdout.buffer.flush()\n' +
        "if r.returncode==0 and '--cflags-only-other' in sys.argv: print(' -D NODE_SPLIT_FLAG=1 -pthread',end='')\n" +
        'sys.stderr.buffer.write(r.stderr);raise SystemExit(r.returncode)\n')
    wrapper.chmod(0o755)
    env['PKG_CONFIG'] = str(wrapper)
    subprocess.run([sys.executable, '-B', 'configure.py', '--shared-highway',
                    '--shared-simdjson', '--shared-ada', '--without-npm'], cwd=source, env=env,
                   check=True, stdout=subprocess.DEVNULL)
config = (source / 'config.gypi').read_text()
data = json.loads(config[config.index('{'):])['target_defaults']
assert 'NODE_SPLIT_FLAG=1' in data['defines']
assert all(flag[2:] in data['defines'] for flag in expected)
link_rules = (source / 'out/node_mksnapshot.target.mk').read_text()
assert re.search(r'^\s*-lada\s*\\$', link_rules, re.M)
assert re.search(r'^\s*-lada-idna\s*\\$', link_rules, re.M)
rules = (source / 'out/tools/v8_gypfiles/v8_base_without_compiler.target.mk').read_text()
for mode in ('Debug', 'Release'):
    definitions = re.search(r'^DEFS_' + mode + r' :=(.*?)(?:\n\n)', rules, re.M | re.S)
    assert definitions, 'missing ' + mode + ' definitions'
    for flag in (*expected, '-DNODE_SPLIT_FLAG=1'):
        assert flag in definitions.group(1), 'missing generated GYP define: ' + flag
    for language in ('C', 'CC'):
        block = re.search(r'^CFLAGS_' + language + '_' + mode + r' :=(.*?)(?:\n\n)', rules, re.M | re.S)
        assert block and '-pthread' in block.group(1), 'missing ' + language + ' flags in ' + mode
print('pkg-config flags and Ada metadata/override/fallback in generated GYP: PASS')
