#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Generate, build and regenerate a dual-toolset GYP graph on Darwin."""
import argparse
import os
import re
import shlex
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
for arg in ('sdk-source', 'host-prefix', 'gyp-source', 'target-sysroot', 'target', 'python', 'work', 'lock-root'):
    p.add_argument('--' + arg, required=True)
a = p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_.+-]+', a.target):
    p.error('invalid target triplet')
host = Path(a.host_prefix).resolve(strict=True)
gyp = Path(a.gyp_source).resolve(strict=True)
root = Path(a.target_sysroot).resolve(strict=True)
work = Path(a.work).resolve()
if work.exists():
    p.error('select a new fixture work directory')
if any(work.is_relative_to(path) or path.is_relative_to(work) for path in (host, gyp, root)):
    p.error('fixture work must not overlap selected providers')
sys.path.insert(0, str(Path(a.sdk_source) / 'src'))
from emberbsd_sdk.process import ContextLocks, sanitized_environment

def tool(name):
    p = (host / 'bin' / name).resolve(strict=True)
    if not p.is_relative_to(host) or not os.access(p, os.X_OK):
        raise ValueError('tool outside host prefix: ' + str(p))
    return str(p)

python = Path(a.python).resolve(strict=True)
if not python.is_relative_to(host) or not os.access(python, os.X_OK):
    raise ValueError('Python outside host prefix')
python = str(python)
clang, clangxx, make = (tool(x) for x in ('clang', 'clang++', 'gmake'))
env = sanitized_environment()
env.update(GYP_CROSSCOMPILE='1')
gypfile = work / 'dual.gyp'
source = work / 'main.c'
with ContextLocks([str(host), str(root), str(gyp)], a.lock_root, shared=True), ContextLocks([str(work)], a.lock_root):
    work.mkdir(parents=True, exist_ok=False)
    tools = work / 'tools'
    tools.mkdir()
    for alias, selected in {'rm':'grm', 'mkdir':'gmkdir', 'printf':'gprintf', 'sed':'gsed', 'grep':'ggrep', 'awk':'nawk', 'cat':'gcat', 'touch':'gtouch', 'ln':'gln', 'cp':'gcp'}.items():
        (tools / alias).symlink_to(tool(selected))
    env['PATH'] = str(tools) + ':' + str(host / 'bin') + ':' + str(host / 'sbin')
    source.write_text('int main(void) { return 0; }\n')
    gypfile.write_text("{'targets': [{'target_name':'host_probe','type':'executable','toolsets':['host'],'sources':['main.c']}, {'target_name':'target_probe','type':'executable','toolsets':['target'],'sources':['main.c']}]}\n")
    subprocess.run([python, str(gyp / 'gyp_main.py'), '--depth=.', '-f', 'make-netbsd', 'dual.gyp'], cwd=work, env=env, check=True)
    makefile = work / 'Makefile'
    contents = makefile.read_text()
    assert '-fmake-netbsd' in contents and 'cmd_link_host' in contents and 'cmd_link_target' in contents
    assert 'cmd_alink_thin = rm -f $@ && $(AR.$(TOOLSET)) crs ' in contents
    cc_target = shlex.quote(clang) + ' --target=' + a.target + ' --sysroot=' + shlex.quote(str(root))
    link_target = shlex.quote(clangxx) + ' --target=' + a.target + ' --sysroot=' + shlex.quote(str(root)) + ' -fuse-ld=lld'
    argv = [make, '-j1', 'SHELL='+tool('mksh'), 'CC.host='+shlex.quote(clang), 'CXX.host='+shlex.quote(clangxx), 'LINK.host='+shlex.quote(clangxx),
            'CC.target='+cc_target, 'CXX.target='+link_target, 'LINK.target='+link_target]
    subprocess.run(argv, cwd=work, env=env, check=True)
    # A changed project file makes GNU make exercise its actual regeneration rule.
    gypfile.write_text(gypfile.read_text() + '\n')
    subprocess.run(argv, cwd=work, env=env, check=True)
    assert '-fmake-netbsd' in makefile.read_text()
    subprocess.run([str(work / 'out/Default/host_probe')], cwd=work, env=env, check=True)
print('GYP Darwin host / NetBSD target build and regeneration: PASS')
