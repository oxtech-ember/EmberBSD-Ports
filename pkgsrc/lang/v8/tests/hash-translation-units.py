#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check V8 headers do not change std::hash across translation units."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True, help='prepared shared V8 source')
p.add_argument('--cxx', type=Path, required=True, help='selected host SDK C++ compiler')
p.add_argument('--work', type=Path, required=True, help='new temporary work directory')
p.add_argument('--flag', action='append', default=[], help='additional selected compiler/linker flag')
a = p.parse_args()
source = a.source.resolve(strict=True)
assert a.cxx.is_absolute() and a.cxx.is_file()
cxx = a.cxx  # Preserve argv[0] for compiler-driver and wrapper selection.
assert a.work.is_absolute() and not a.work.exists()
a.work.mkdir()
files = {
 'insert.cc': r'''#include <unordered_set>
extern "C" void insert(std::unordered_set<int>* s) { s->insert(1); }
extern "C" size_t external_hash() { return std::hash<int>{}(1); }
''',
 'lookup.cc': r'''#include "src/base/hashing.h"
#include <unordered_map>
#include <unordered_set>
extern "C" bool lookup(const std::unordered_set<int>* s) { return s->find(1) != s->end(); }
extern "C" size_t internal_hash() { return std::hash<int>{}(1); }
struct Key { int value; size_t hash_value() const { return v8::base::hash<int>{}(value); }
  bool operator==(const Key&) const = default; };
extern "C" bool custom_hashes() {
  std::unordered_set<Key, v8::base::hash<Key>> keys; keys.insert(Key{7});
  std::unordered_map<std::pair<int,int>, int, v8::base::hash<std::pair<int,int>>> pairs;
  pairs[{1,2}] = 3; return keys.contains(Key{7}) && pairs.at({1,2}) == 3;
}
''',
 'main.cc': r'''#include <unordered_set>
extern "C" void insert(std::unordered_set<int>*);
extern "C" bool lookup(const std::unordered_set<int>*);
extern "C" size_t external_hash();
extern "C" size_t internal_hash();
extern "C" bool custom_hashes();
int main() { std::unordered_set<int> values; insert(&values);
  return !(lookup(&values) && external_hash() == internal_hash() && custom_hashes()); }
''',
}
objects = []
for name, text in files.items():
    path = a.work / name
    path.write_text(text)
    obj = path.with_suffix('.o')
    subprocess.run([str(cxx), *a.flag, '-std=c++20', '-I'+str(source),
                    '-I'+str(source/'include'), '-c', str(path), '-o', str(obj)], check=True)
    objects.append(obj)
exe = a.work/'hash-tu'
subprocess.run([str(cxx), *a.flag, *(str(x) for x in objects), '-o', str(exe)], check=True)
subprocess.run([str(exe)], check=True)
print('V8 std::hash across translation units and explicit custom/pair hash: PASS')
