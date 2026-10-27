#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check selected Darwin mimalloc modes, late loading and direct consumer APIs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

SOURCE = r'''
#include <mimalloc.h>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <mutex>
#include <thread>
#include <vector>

static void require(bool value, const char* message) {
  if (!value) { std::fprintf(stderr, "%s\n", message); std::_Exit(4); }
}
template<typename T> static T symbol(void* library, const char* name) {
  void* value = dlsym(library, name);
  require(value != nullptr, name);
  return reinterpret_cast<T>(value);
}
int main(int argc, char** argv) {
  require(argc == 3, "library and override mode required");
  const bool expect_override = std::strcmp(argv[2], "on") == 0;
  void* ordinary_before = std::malloc(71);
  std::mutex mutex;
  std::condition_variable changed;
  int ready = 0;
  bool start = false;
  decltype(&mi_malloc) allocate = nullptr;
  decltype(&mi_malloc_aligned) aligned = nullptr;
  decltype(&mi_free) release = nullptr;
  decltype(&mi_check_owned) owns = nullptr;
  decltype(&mi_heap_new) heap_new = nullptr;
  decltype(&mi_heap_zalloc) heap_zalloc = nullptr;
  decltype(&mi_heap_destroy) heap_destroy = nullptr;
  void* crossing[4] = {};
  std::vector<std::thread> threads;
  for (int id = 0; id != 4; ++id) {
    threads.emplace_back([&, id] {
      {
        std::unique_lock<std::mutex> lock(mutex);
        ++ready;
        changed.notify_all();
        changed.wait(lock, [&] { return start; });
      }
      mi_heap_t* heap = heap_new();
      require(heap != nullptr, "mi_heap_new");
      // The pinned SolveSpace consumer uses these three heap operations.
      const auto* zero = static_cast<unsigned char*>(heap_zalloc(heap, 4096));
      require(zero != nullptr, "mi_heap_zalloc");
      for (int i = 0; i != 4096; ++i) require(zero[i] == 0, "heap zero initialization");
      heap_destroy(heap);
      for (int i = 0; i != 2000; ++i) {
        void* p = aligned(257 + i % 97, 128);
        require(p && (reinterpret_cast<std::uintptr_t>(p) % 128) == 0 && owns(p), "thread allocation/alignment/ownership");
        std::memset(p, id, 257 + i % 97);
        release(p);
      }
      crossing[id] = allocate(1024);
      require(crossing[id] != nullptr, "cross-thread allocation");
    });
  }
  {
    std::unique_lock<std::mutex> lock(mutex);
    changed.wait(lock, [&] { return ready == 4; });
  }
  // The embedding route first loads the allocator after all workers exist.
  void* library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
  require(library != nullptr, dlerror());
  auto version = symbol<decltype(&mi_version)>(library, "mi_version");
  require(version() == 30600, "unexpected mimalloc version");
  allocate = symbol<decltype(allocate)>(library, "mi_malloc");
  aligned = symbol<decltype(aligned)>(library, "mi_malloc_aligned");
  release = symbol<decltype(release)>(library, "mi_free");
  owns = symbol<decltype(owns)>(library, "mi_check_owned");
  heap_new = symbol<decltype(heap_new)>(library, "mi_heap_new");
  heap_zalloc = symbol<decltype(heap_zalloc)>(library, "mi_heap_zalloc");
  heap_destroy = symbol<decltype(heap_destroy)>(library, "mi_heap_destroy");
  void* ordinary_after = std::malloc(89);
  // Also cover the ordinary new/delete path used by pinned Mold.
  auto* cpp = new std::uint64_t[16];
  require(owns(ordinary_before) == expect_override && owns(ordinary_after) == expect_override &&
          owns(cpp) == expect_override, "wrong allocator interposition");
  delete[] cpp;
  std::free(ordinary_before);
  std::free(ordinary_after);
  {
    std::lock_guard<std::mutex> lock(mutex);
    start = true;
  }
  changed.notify_all();
  for (auto& thread : threads) thread.join();
  for (void* p : crossing) { require(owns(p), "cross-thread ownership"); release(p); }
  // Keep the module loaded until process exit; unloading allocator TLS while
  // the process is alive is not a supported operation asserted by this test.
  std::puts("shared allocator mode, late-load threads, heap and C++ allocation checks passed");
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host-prefix', 'sdk-root', 'sdk-source', 'lock-root', 'link-context',
                 'include', 'override-library', 'embedding-library', 'utility-path', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--deployment-target', required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('this regression currently covers native Darwin')
    for value in vars(args).values():
        if isinstance(value, Path) and not value.is_absolute():
            parser.error('select absolute input/output paths')
    prefix = args.host_prefix.resolve()
    for name in ('clang++', 'ld64.lld', 'python3.15'):
        path = prefix / 'bin' / name
        assert path.resolve().is_relative_to(prefix) and os.access(path, os.X_OK), path
    for path in (args.override_library, args.embedding_library, args.include / 'mimalloc.h',
                 args.sdk_source / 'scripts/link-launcher.py'):
        assert path.is_file(), path
    args.work.mkdir(parents=True, exist_ok=False)
    source = args.work / 'consumer.cc'
    source.write_text(SOURCE)
    obj, executable = args.work / 'consumer.o', args.work / 'consumer'
    flags = ['-isysroot', str(args.sdk_root), '-mmacosx-version-min=' + args.deployment_target]
    env = dict(os.environ, PATH=str(args.utility_path))
    for key in ('DYLD_INSERT_LIBRARIES', 'DYLD_LIBRARY_PATH', 'LD_PRELOAD'):
        env.pop(key, None)
    commands = [
        ('compile', [str(prefix / 'bin/clang++'), *flags, '-O2', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                     '-I' + str(args.include), '-c', str(source), '-o', str(obj)]),
        ('link', [str(prefix / 'bin/python3.15'), '-B', str(args.sdk_source / 'scripts/link-launcher.py'),
                  '--lock-root', str(args.lock_root), '--context', str(args.link_context), '--',
                  str(prefix / 'bin/clang++'), *flags, '--ld-path=' + str(prefix / 'bin/ld64.lld'),
                  str(obj), '-lpthread', '-o', str(executable)])]
    results = []
    for name, argv in commands:
        process = subprocess.run(argv, env=env, capture_output=True, text=True)
        (args.work / (name + '.log')).write_text(process.stdout + process.stderr)
        assert process.returncode == 0, process.stdout + process.stderr
        results.append({'case': name, 'argv': argv, 'exit_code': process.returncode})
    for name, library, mode, preload, expected in (
            ('embedding', args.embedding_library, 'off', False, 0),
            ('override', args.override_library, 'on', True, 0),
            ('wrong-embedding-artifact', args.override_library, 'off', True, 4),
            ('wrong-override-artifact', args.embedding_library, 'on', True, 4)):
        case_env = dict(env)
        if preload:
            case_env['DYLD_INSERT_LIBRARIES'] = str(library)
        argv = [str(executable), str(library), mode]
        process = subprocess.run(argv, env=case_env, capture_output=True, text=True)
        output = process.stdout + process.stderr
        (args.work / (name + '.log')).write_text(output)
        assert process.returncode == expected, output
        if expected:
            assert 'wrong allocator interposition' in output, output
        results.append({'case': name, 'argv': argv, 'preload': preload, 'exit_code': process.returncode})
    (args.work / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print('2 native shared allocator modes and 2 incompatible-artifact controls passed; no full application/target acceptance.')


if __name__ == '__main__':
    main()
