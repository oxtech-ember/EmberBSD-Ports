#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check actual pkgsrc consumer dependency metadata for native and cross C++ roles."""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
for option in ('pkgsrc', 'makeconf', 'bmake'):
    p.add_argument('--' + option, required=True, type=Path)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
env = dict(os.environ, MAKECONF=str(a.makeconf))
for recipe in ('devel/abseil', 'textproc/icu'):
    base = [str(a.bmake), '-C', str(a.pkgsrc / recipe), '-f', str(root / 'pkgsrc' / recipe / 'Makefile')]
    def query(args, var):
        return subprocess.run(base + args + ['show-var', 'VARNAME=' + var], env=env,
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True).stdout.strip()
    key = query(['USE_CROSS_COMPILE=no'], '_EMBER_NATIVE_TOOLSET_KEY')
    verified = 'EMBERBSD_NATIVE_TOOLSET_VERIFIED=' + key
    binding = query([verified, 'USE_CROSS_COMPILE=no'], 'EMBERBSD_NATIVE_CXX_BINDING_RECORD')
    namespace = query([verified, 'USE_CROSS_COMPILE=no'], 'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE')
    assert binding and not namespace, (recipe, binding, namespace)
    platform = query([verified, 'USE_CROSS_COMPILE=no'], 'DEPENDS')
    replacement = query([verified, 'USE_CROSS_COMPILE=no', 'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], 'DEPENDS')
    cross = query([verified, 'USE_CROSS_COMPILE=yes', 'EMBERBSD_NATIVE_CXX_ABI_NAMESPACE=__ember1'], 'DEPENDS')
    assert 'libcxx>=' not in platform, (recipe, platform)
    assert 'libcxx>=23.1.4nb1:../../lang/libcxx' in replacement, (recipe, replacement)
    assert 'libcxx>=23.1.4nb1:../../lang/libcxx' not in cross, (recipe, cross)
    print(recipe + ': PASS platform binding, replacement runtime and cross metadata')
