#!/usr/bin/env python3
"""Run the memory-only LVGL smoke test against an installed or staged package."""
import argparse
import os
import platform
import sys
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--host-prefix', required=True, type=Path)
parser.add_argument('--lvgl-prefix', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
host_prefix = args.host_prefix.resolve(strict=True)
clang = (host_prefix / 'bin/clang').resolve(strict=True)
if not clang.is_relative_to(host_prefix):
    parser.error('clang must resolve within the selected host prefix')
linker_name = 'ld64.lld' if sys.platform == 'darwin' else 'ld.lld'
linker = (host_prefix / 'bin' / linker_name).resolve(strict=True)
if not linker.is_relative_to(host_prefix):
    parser.error('linker must resolve within the selected host prefix')
env = dict(os.environ, PATH=os.pathsep.join((str(host_prefix / 'bin'),
                                            str(host_prefix / 'gnu/bin'))))
triple = subprocess.check_output([str(clang), '-print-target-triple'],
                                 env=env, text=True).strip()
aliases = {'arm64': 'aarch64', 'amd64': 'x86_64'}
host_arch = aliases.get(platform.machine().lower(), platform.machine().lower())
compiler_arch = aliases.get(triple.split('-', 1)[0], triple.split('-', 1)[0])
if compiler_arch != host_arch:
    parser.error(f'native compiler architecture {compiler_arch} does not match {host_arch}')
lvgl_prefix = args.lvgl_prefix.resolve(strict=True)
source = Path(__file__).resolve().with_name('smoke.c')
command = [str(clang), '-fuse-ld=lld', '-fsanitize=address,undefined',
           '-fno-sanitize-recover=all', '-g',
           '-I' + str(lvgl_prefix / 'include'), '-DLV_CONF_INCLUDE_SIMPLE',
           '-DLV_KCONFIG_IGNORE', str(source), str(lvgl_prefix / 'lib/liblvgl.a'),
           '-o', str(args.output)]
subprocess.run(command, check=True, env=env)
subprocess.run([str(args.output.resolve(strict=True))], check=True, env=env)
