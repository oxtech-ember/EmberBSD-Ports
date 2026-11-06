#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the NetBSD Chromium executable-path branch and owner patch."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', required=True, type=Path,
                    help='Chromium base/base_paths_posix.cc before this patch')
parser.add_argument('--patch-tool', required=True, type=Path)
parser.add_argument('--owner-patch', type=Path, default=ROOT /
                    'probes/electron/patches/netbsd-cross-source.patch')
a = parser.parse_args()
cxx = os.environ.get('CXX')
if not cxx:
    parser.error('CXX must select the native SDK C++ compiler')

owner = a.owner_patch.read_text()
section = owner.split('diff --git a/base/base_paths_posix.cc b/base/base_paths_posix.cc\n', 1)[1]
section = section.split('diff --git ', 1)[0]
hunks = re.findall(r'(?ms)^@@ [^\n]+\n.*?(?=^@@ |\Z)', section)
selected = [h for h in hunks if 'MakeAbsoluteFilePath(FilePath(bin_dir.value()))' in h]
if len(selected) != 1:
    raise SystemExit('expected exactly one NetBSD executable-path owner hunk')

header = r'''#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <initializer_list>
#include <limits.h>
#include <optional>
#include <sstream>
#include <string>
#include <unistd.h>
struct FilePath {
  std::string p;
  FilePath(std::string v) : p(v) {}
  bool empty() const { return p.empty(); }
  const std::string& value() const { return p; }
};
static std::string supplied;
static std::optional<std::string> StringSysctl(std::initializer_list<int>) { return supplied; }
// Same documented failure and realpath behavior as base::MakeAbsoluteFilePath.
static FilePath MakeAbsoluteFilePath(const FilePath& p) {
  char buf[PATH_MAX];
  return realpath(p.p.c_str(), buf) ? FilePath(buf) : FilePath("");
}
#define CTL_KERN 1
#define KERN_PROC_ARGS 2
#define KERN_PROC_PATHNAME 3
#define NOTREACHED() std::ostringstream()
#define VLOG(x) std::ostringstream()
static bool run(FilePath* result) {
'''
footer = r'''
}
int main(int argc, char**) {
  const bool fixed = argc == 2;
  char temp[] = "/tmp/chromium-exe-path.XXXXXXXX";
  if (!mkdtemp(temp)) return 10;
  char canonical[PATH_MAX];
  if (!realpath(temp, canonical)) return 14;
  std::string dir(canonical), file=dir+"/electron", link=dir+"/link";
  { std::ofstream out(file); out << "test"; }
  if (symlink("electron", link.c_str())) return 11;
  const auto expected = MakeAbsoluteFilePath(FilePath(file)).value();
  int mismatches = 0;
  for (const auto& candidate : {file, dir+"/./electron", link}) {
    supplied = candidate; FilePath output("sentinel");
    if (!run(&output) || output.value() != expected) mismatches++;
  }
  supplied = dir+"/missing"; FilePath output("sentinel");
  const bool missing_result = run(&output);
  const bool missing_ok = !missing_result && output.value() == "sentinel";
  unlink(link.c_str()); unlink(file.c_str()); rmdir(dir.c_str());
  if (fixed) return mismatches == 0 && missing_ok ? 0 : 12;
  // The old branch must exhibit both the original dot/symlink mismatch and
  // erroneous success/output change for an absent executable.
  return mismatches == 2 && missing_result && output.value() == supplied ? 0 : 13;
}
'''

def branch(path):
    text = path.read_text()
    begin = '#elif BUILDFLAG(IS_NETBSD)\n'
    end = '#elif BUILDFLAG(IS_SOLARIS)'
    if text.count(begin) != 1:
        raise ValueError('unexpected NetBSD provider')
    return text.split(begin, 1)[1].split(end, 1)[0]

with tempfile.TemporaryDirectory(prefix='chromium-exe-path-') as tmp:
    root = Path(tmp)
    source = root / 'base/base_paths_posix.cc'
    source.parent.mkdir()
    source.write_bytes(a.source.read_bytes())
    baseline = branch(source)
    hunk = root / 'netbsd.patch'
    hunk.write_text('--- a/base/base_paths_posix.cc\n+++ b/base/base_paths_posix.cc\n' + selected[0])
    subprocess.run([str(a.patch_tool), '--batch', '-p1', '-F0', '-i', str(hunk)],
                   cwd=root, check=True, stdout=subprocess.PIPE)
    for name, code, args in (('baseline', baseline, []), ('patched', branch(source), ['fixed'])):
        cpp = root / (name + '.cc')
        binary = root / name
        cpp.write_text(header + code + footer)
        subprocess.run([cxx, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        str(cpp), '-o', str(binary)], check=True)
        subprocess.run([str(binary), *args], check=True)
        print(name + ': PASS')
