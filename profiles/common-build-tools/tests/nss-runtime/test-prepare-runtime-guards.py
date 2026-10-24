#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test NSS runtime preparation metadata guards without invoking a compiler."""
import argparse
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True


def accepted(label, check):
    check()


def refused(label, check):
    try:
        check()
    except ValueError:
        return
    raise AssertionError(label + ' was accepted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe-patch', type=Path)
    parser.add_argument('--nspr-contents', type=Path)
    args = parser.parse_args()
    if (args.recipe_patch is None) != (args.nspr_contents is None):
        parser.error('Pass both real metadata paths or neither.')

    builder = runpy.run_path(str(Path(__file__).with_name('prepare-runtime.py')),
                             run_name='nss_runtime_guard_module')
    verify_recipe = builder['verify_nss_recipe_pin']
    verify_identity = builder['verify_package_identity']
    pinned_patch = (
        '--- a/devel/nss/Makefile\n'
        '+++ b/devel/nss/Makefile\n'
        '@@ -4,6 +4,6 @@\n'
        ' \n'
        '-DISTNAME=\t\tnss-3.129\n'
        '+DISTNAME=\t\tnss-3.132\n'
    )
    accepted('valid recipe patch', lambda: verify_recipe(pinned_patch))
    refused('unchanged DISTNAME line', lambda: verify_recipe(
        pinned_patch.replace('+DISTNAME=', ' DISTNAME=', 1)))
    refused('wrong package version', lambda: verify_recipe(
        pinned_patch.replace('+DISTNAME=\t\tnss-3.132', '+DISTNAME=\t\tnss-3.133', 1)))
    refused('unexpected package revision', lambda: verify_recipe(
        pinned_patch + '+PKGREVISION=\t\t1\n'))
    refused('duplicate recipe pin', lambda: verify_recipe(pinned_patch + pinned_patch))

    accepted('NSS package record', lambda: verify_identity(
        '@cwd /usr/pkg\n@name nss-3.132\n', 'nss-3.132'))
    accepted('NSPR record after cwd', lambda: verify_identity(
        '@cwd /usr/pkg\n@name nspr-4.40\n@comment package metadata\n', 'nspr-4.40'))
    refused('wrong NSPR version', lambda: verify_identity(
        '@cwd /usr/pkg\n@name nspr-4.400\n', 'nspr-4.40'))
    refused('missing package identity', lambda: verify_identity(
        '@cwd /usr/pkg\n@comment no identity\n', 'nspr-4.40'))
    refused('duplicate package identity', lambda: verify_identity(
        '@cwd /usr/pkg\n@name nspr-4.40\n@name nspr-4.40\n', 'nspr-4.40'))

    if args.recipe_patch is not None:
        verify_recipe(args.recipe_patch.read_text(encoding='utf-8'))
        verify_identity(args.nspr_contents.read_text(encoding='utf-8'), 'nspr-4.40')

    print('PASS: recipe pin and package identity accept/refusal cases; no compiler invoked')


if __name__ == '__main__':
    main()
