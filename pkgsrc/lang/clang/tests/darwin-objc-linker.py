#!/usr/bin/env python3
"""Exercise Clang's Darwin ObjC linker capability choice and a real link."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--clang', required=True)
p.add_argument('--ld64-lld', required=True)
p.add_argument('--sdk', required=True)
p.add_argument('--resource-dir')
p.add_argument('--expect-default-lld', action='store_true')
a = p.parse_args()
clang = str(Path(a.clang).resolve(strict=True))
linker = str(Path(a.ld64_lld).resolve(strict=True))
sdk = str(Path(a.sdk).resolve(strict=True))
resource = ['-resource-dir=' + str(Path(a.resource_dir).resolve(strict=True))] if a.resource_dir else []
base = [clang, *resource, '-target', 'arm64-apple-macos26', '-isysroot', sdk,
        '-mlinker-version=1250']

with tempfile.TemporaryDirectory(prefix='clang objc linker ') as tmp:
    root = Path(tmp)
    source = root / 'probe.m'
    source.write_text('#import <Foundation/Foundation.h>\n'
                      'int main(void) { @autoreleasepool { return '
                      '[[NSProcessInfo processInfo] processIdentifier] <= 0; } }\n')
    alias = root / 'renamed linker'
    alias.symlink_to(linker)
    missing = str(root / 'nonexistent')
    cases = [
        ('lld-flavor', ['-fuse-ld=lld'], False),
        ('apple-flavor', ['-fuse-ld=ld'], True),
        ('explicit-path', ['--ld-path=' + linker], False),
        ('renamed-symlink', ['--ld-path=' + str(alias)], False),
        ('missing-path', ['--ld-path=' + missing], False),
        ('apple-flavor-path', ['-fuse-ld=ld', '--ld-path=' + missing], True),
        ('explicit-enable', ['--ld-path=' + missing, '-fobjc-msgsend-class-selector-stubs'], True),
        ('explicit-disable', ['-fuse-ld=ld', '-fno-objc-msgsend-class-selector-stubs'], False),
    ]
    if a.expect_default_lld:
        cases.insert(0, ('lld-default', [], False))
    for name, flags, expected in cases:
        run = subprocess.run(base + flags + ['-fsyntax-only', '-###', str(source)],
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if run.returncode:
            raise AssertionError((name, run.stderr))
        actual = '"-fobjc-msgsend-class-selector-stubs"' in run.stderr
        if actual != expected or '"-fobjc-msgsend-selector-stubs"' not in run.stderr:
            raise AssertionError((name, run.stderr))
    old_off = subprocess.run(base + ['-fuse-ld=ld', '-fno-objc-msgsend-selector-stubs',
                                     '-fsyntax-only', '-###', str(source)],
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if (old_off.returncode or '"-fobjc-msgsend-selector-stubs"' in old_off.stderr or
            '"-fobjc-msgsend-class-selector-stubs"' not in old_off.stderr):
        raise AssertionError(('explicit-old-selector-disable', old_off.stderr))
    for language in ('c', 'c++'):
        subprocess.run([clang, *resource, '-Wall', '-Werror', '-x', language,
                        '-fsyntax-only', '/dev/null'], check=True)
        subprocess.run([clang, *resource, '-Wall', '-Werror', '-x', language,
                        '--start-no-unused-arguments', '--ld-path=' + linker,
                        '--end-no-unused-arguments', '-fsyntax-only', '/dev/null'],
                       check=True)
        unused = subprocess.run([clang, *resource, '-Wall', '-Werror', '-x', language,
                                 '-fuse-ld=lld', '-fsyntax-only', '/dev/null'],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if unused.returncode == 0 or 'unused' not in unused.stderr:
            raise AssertionError((language, 'linker option warning changed', unused.stderr))
    executable = root / 'objc-consumer'
    subprocess.run([clang, *resource, '-isysroot', sdk, '-mmacosx-version-min=26.0',
                    '--ld-path=' + linker, '-framework', 'Foundation', str(source),
                    '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
print('PASS: Darwin linker selection, explicit overrides, warnings and ObjC link/run')
