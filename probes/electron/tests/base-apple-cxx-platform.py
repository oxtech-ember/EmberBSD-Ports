#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), not submitted upstream.
"""Check the exact Apple C++ split. Do not execute GN or a native tool."""
import argparse
import hashlib
from pathlib import Path
import re
import sys
import unittest

sys.dont_write_bytecode = True

def deny_child_and_network(event, args):
    if event.startswith(('subprocess.', 'socket.', 'os.exec', 'os.spawn', 'os.posix_spawn')) or event == 'os.system':
        raise RuntimeError('source checks forbid child and network execution: ' + event)

sys.addaudithook(deny_child_and_network)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path, help='Complete pinned Chromium source before or after the split')
args, remaining = parser.parse_known_args()
PATCH = Path(__file__).resolve().parents[1] / 'patches/base-apple-cxx-platform.patch'
HASHES = {'base/BUILD.gn': ('9c58c5a8374a0a05693117c02d04c7ba09746474074c8b51184b858ad3d6c530', 'f8c03ca7b2d92bcb8c22dd94ed3b5371e358deb952ca9591229d01c669cfe76c'), 'base/apple/base_bundle_id.cc': (None, '51b013f78ed13f7fef7dbec4f3f76d8a09f16dbcd86781d5d85ad1c78b19f701'), 'base/apple/foundation_util.mm': ('d6dec7b278cc46a0538415d8ab2e5e13e7ef5ab4ac695242d17e284c0449e0a6', '03ac2e0d366ab94a1250df00016d82cb14b30d0fa62603224d1bb3f04a969d5a'), 'base/strings/sys_string_conversions_apple.mm': ('50b25e54484d3659844ba02961c9412587437e7990e6fe6c1bb628383b3a87a0', 'ccb2dd2c17e042851f81a81673aeb96484399c35992a458e491e9719444a2457'), 'base/strings/sys_string_conversions_apple_cf.cc': (None, '8b5b18de1a11bbaf07ac866ec6705f6e6a17ee42c55d11ad53b9bdae417748e2'), 'base/system/sys_info_apple.cc': (None, '685bc07ff9ca464e9f9065cc95f9bee2cc5dc34d0cfbd1508e5583ecb2466a1b'), 'base/system/sys_info_apple.mm': ('685bc07ff9ca464e9f9065cc95f9bee2cc5dc34d0cfbd1508e5583ecb2466a1b', None), 'base/threading/platform_thread_apple.mm': ('7e9b3661b2d24b69a3e252ee01fca6eb1e63b90bc155c16c856d61d51ed2d521', 'cc0aff80bbd7e7578ed87e2b286fe1dc72a3b6e7d08a5bdf357a9af00c2d1335'), 'base/threading/platform_thread_apple_yield.cc': (None, '3e2cdf6117f9484afe792a5a29c2dabe23f22bb1f670900c41ea62aec19d79d2'), 'base/time/time_apple.mm': ('0015cb2fa5ee082bb61f07e24c150d161b08a7148143914d43c58f4850c68134', '6337b061961743a5941d0bd5bc9196a2886124d8af16fb7368e24e34b558db82'), 'base/time/time_apple_mach.cc': (None, 'c06da2743378a0fe7bceb740ca368aafc943d96806f0bcf5238d522915ae6fa1'), 'base/threading/platform_thread_apple_name.cc': (None, '651aa0ad16047e55d882862c4864ff8b70801a59158bbf934449e92549668ef2'), 'base/threading/platform_thread.cc': ('7cb7235c9d6408e8491dbf344a0d7759e15629389c867fbbe0f45f23083811df', '7cb7235c9d6408e8491dbf344a0d7759e15629389c867fbbe0f45f23083811df'), 'base/threading/platform_thread.h': ('f002f5ddebc27c9b77f7af36e6ad1955d736b88bb8f68e405258531c25525a84', 'f002f5ddebc27c9b77f7af36e6ad1955d736b88bb8f68e405258531c25525a84')}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def check_files(files, index):
    for name, expected in HASHES.items():
        actual = digest(files[name]) if name in files else None
        if actual != expected[index]:
            raise ValueError('complete pinned source differs: ' + name)
    if set(files) != {name for name, hashes in HASHES.items() if hashes[index] is not None}:
        raise ValueError('source roster differs')


def apply_exact(files, patch, reverse=False):
    """Apply complete, unique source hunks in memory. Refuse fuzz."""
    result, lines, index = dict(files), patch.splitlines(True), 0
    while index < len(lines):
        if not lines[index].startswith('--- '):
            index += 1
            continue
        old_path, new_path = lines[index][4:].strip(), lines[index + 1][4:].strip()
        name = (new_path if old_path == '/dev/null' else old_path)[2:]
        if old_path not in ('/dev/null', 'a/' + name) or new_path not in ('/dev/null', 'b/' + name):
            raise ValueError('unexpected source path')
        if name not in HASHES:
            raise ValueError('unexpected patch member')
        origin, destination = (new_path, old_path) if reverse else (old_path, new_path)
        if origin == '/dev/null' and name in result:
            raise ValueError('new source already exists')
        text, cursor = result.get(name, ''), 0
        index += 2
        while index < len(lines) and lines[index].startswith('@@ '):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n', lines[index])
            if not match:
                raise ValueError('invalid hunk header')
            old, new = [], []
            index += 1
            while index < len(lines) and lines[index][:1] in (' ', '+', '-') and not lines[index].startswith('--- '):
                line = lines[index]
                if line[0] in ' -':
                    old.append(line[1:])
                if line[0] in ' +':
                    new.append(line[1:])
                index += 1
            if (len(old), len(new)) != (int(match[2] or 1), int(match[4] or 1)):
                raise ValueError('hunk counts differ')
            expected, replacement = (''.join(new), ''.join(old)) if reverse else (''.join(old), ''.join(new))
            offsets = [m.start() for m in re.finditer(re.escape(expected), text[cursor:])]
            if len(offsets) != 1:
                raise ValueError('require one complete context match')
            start = cursor + offsets[0]
            text = text[:start] + replacement + text[start + len(expected):]
            cursor = start + len(replacement)
        if destination == '/dev/null':
            if text:
                raise ValueError('deleted source is not empty')
            result.pop(name)
        else:
            result[name] = text
    return result


CURRENT = {name: (args.source / name).read_text() for name in HASHES if (args.source / name).exists()}
state = None
for index in (0, 1):
    try:
        check_files(CURRENT, index)
        state = index
    except ValueError:
        pass
if state is None:
    parser.error('source must match one complete pinned before or after state')
BEFORE = CURRENT if state == 0 else apply_exact(CURRENT, PATCH.read_text(), reverse=True)
AFTER = apply_exact(BEFORE, PATCH.read_text())


class AppleCxxSourceTests(unittest.TestCase):
    def test_complete_pinned_states(self):
        check_files(BEFORE, 0)
        check_files(AFTER, 1)

    def test_forward_and_reverse_are_exact(self):
        self.assertEqual(apply_exact(AFTER, PATCH.read_text(), reverse=True), BEFORE)
        self.assertEqual(apply_exact(BEFORE, PATCH.read_text()), AFTER)

    def test_whole_sysinfo_source_move(self):
        self.assertNotIn('base/system/sys_info_apple.mm', AFTER)
        self.assertEqual(BEFORE['base/system/sys_info_apple.mm'], AFTER['base/system/sys_info_apple.cc'])

    def test_yield_body_and_mixed_remainder(self):
        mm, cc = 'base/threading/platform_thread_apple.mm', 'base/threading/platform_thread_apple_yield.cc'
        heading = '// static\nvoid PlatformThreadBase::YieldCurrentThread() {'
        start = BEFORE[mm].index(heading)
        end = BEFORE[mm].index('// static\nvoid PlatformThreadBase::SetName', start)
        lifted = BEFORE[mm][start:end]
        self.assertEqual(digest(lifted), '535af43cd774c8ec2cecd47b6876346dd20650d8925aad33245504fd407cfdab')
        self.assertIn(lifted, AFTER[cc])
        name_start = BEFORE[mm].index('// static\nvoid PlatformThreadBase::SetName(')
        name_end = BEFORE[mm].index('// Whether optimized real-time thread config', name_start)
        name_body = BEFORE[mm][name_start:name_end]
        self.assertEqual(AFTER[mm], BEFORE[mm].replace(lifted, '').replace(name_body, '').replace('#include <mach/thread_switch.h>\n', ''))

    def test_apple_gn_routes_and_retained_bridges(self):
        gn = AFTER['base/BUILD.gn']
        apple = gn.split('  # Mac or iOS.\n  if (is_apple) {', 1)[1].split('  # Desktop Mac.', 1)[0]
        for name in ('apple/base_bundle_id.cc', 'strings/sys_string_conversions_apple_cf.cc',
                     'time/time_apple_mach.cc', 'system/sys_info_apple.cc', 'threading/platform_thread_apple_yield.cc',
                     'threading/platform_thread_apple_name.cc'):
            self.assertEqual(apple.count('"' + name + '"'), 1)
            self.assertEqual(gn.count('"' + name + '"'), 1)
        self.assertNotIn('"system/sys_info_apple.mm"', gn)
        for name in ('apple/foundation_util.mm', 'strings/sys_string_conversions_apple.mm',
                     'time/time_apple.mm', 'threading/platform_thread_apple.mm'):
            self.assertIn('"' + name + '"', apple)
        self.assertIn('SysUTF8ToNSString', AFTER['base/strings/sys_string_conversions_apple.mm'])
        self.assertIn('Time::ToNSDate', AFTER['base/time/time_apple.mm'])
        self.assertIn('NSThread', AFTER['base/threading/platform_thread_apple.mm'])

    def test_new_sources_keep_license_and_cpp_language(self):
        for name, hashes in HASHES.items():
            if hashes[0] is None:
                with self.subTest(source=name):
                    text = AFTER[name]
                    self.assertIn('The Chromium Authors', text)
                    self.assertIn('BSD-style license', text)
                    self.assertNotIn('#import', text)
                    self.assertNotIn('Foundation/Foundation.h', text)
                    self.assertNotIn('@autoreleasepool', text)

    def test_body_or_route_mutants_are_refused(self):
        cases = (
            ('base/threading/platform_thread_apple_yield.cc', 'timeout_ms = 1;', 'timeout_ms = 0;'),
            ('base/apple/base_bundle_id.cc', 'SetBaseBundleID', 'RemovedSetBaseBundleID'),
            ('base/system/sys_info_apple.cc', 'return ByteSize(physical_memory);', 'return ByteSize(0);'),
            ('base/BUILD.gn', '"apple/base_bundle_id.cc"', '"unrelated.cc"'),
        )
        for name, old, new in cases:
            with self.subTest(source=name):
                self.assertIn(old, AFTER[name])
                changed = dict(AFTER, **{name: AFTER[name].replace(old, new)})
                with self.assertRaises(ValueError):
                    check_files(changed, 1)

    def test_removed_route_cannot_be_restored(self):
        changed = dict(AFTER)
        changed['base/system/sys_info_apple.mm'] = BEFORE['base/system/sys_info_apple.mm']
        with self.assertRaises(ValueError):
            check_files(changed, 1)


    def test_name_body_and_shared_state_boundary(self):
        mm, cc = 'base/threading/platform_thread_apple.mm', 'base/threading/platform_thread_apple_name.cc'
        start = BEFORE[mm].index('// static\nvoid PlatformThreadBase::SetName(')
        end = BEFORE[mm].index('// Whether optimized real-time thread config', start)
        lifted = BEFORE[mm][start:end]
        self.assertEqual(digest(lifted), '3ea81d42d519b8cf00b77561b96f248dc089214a985e797d9f803c0b52d56427')
        self.assertEqual(AFTER[cc].count(lifted), 1)
        for name in ('base/threading/platform_thread.cc', 'base/threading/platform_thread.h'):
            self.assertEqual(BEFORE[name], AFTER[name])
        self.assertIn('void PlatformThreadBase::SetNameCommon(const std::string& name) {\n  ThreadIdNameManager::GetInstance()->SetName(name);\n}', AFTER['base/threading/platform_thread.cc'])
        self.assertIn('protected:\n  static void SetNameCommon(const std::string& name);', AFTER['base/threading/platform_thread.h'])
        self.assertNotIn('void PlatformThreadBase::SetNameCommon', AFTER[cc])
        self.assertLess(lifted.index('SetNameCommon(name);'), lifted.index('name.substr(0, kMaxNameLength)'))
        self.assertLess(lifted.index('name.substr(0, kMaxNameLength)'), lifted.index('pthread_setname_np('))

    def test_name_body_mutants_are_refused(self):
        name = 'base/threading/platform_thread_apple_name.cc'
        for old, new in (('SetNameCommon(name);', ';'), ('kMaxNameLength = 63;', 'kMaxNameLength = 62;'),
                         ('pthread_setname_np(shortened_name.c_str());', ';')):
            with self.subTest(mutation=new):
                self.assertIn(old, AFTER[name])
                changed = dict(AFTER, **{name: AFTER[name].replace(old, new)})
                with self.assertRaises(ValueError):
                    check_files(changed, 1)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
