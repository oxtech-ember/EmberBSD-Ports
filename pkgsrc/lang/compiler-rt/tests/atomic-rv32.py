#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check RV32 libc's selected compiler-rt atomic ABI source."""
import argparse
from pathlib import Path
import subprocess
import textwrap


def symbols(nm, obj):
    result = subprocess.run([nm, '-g', '--defined-only', str(obj)], check=True,
                            text=True, stdout=subprocess.PIPE)
    names = set()
    for line in result.stdout.splitlines():
        name = line.split()[-1]
        if name.startswith('___atomic'):
            name = name[1:]
        names.add(name)
    return names


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--cc', required=True)
    cli.add_argument('--nm', required=True)
    cli.add_argument('--source', type=Path, required=True)
    cli.add_argument('--out-dir', type=Path, required=True)
    args = cli.parse_args()
    args.out_dir.mkdir(parents=True)

    patched = args.source / 'compiler-rt/lib/builtins/atomic.c'
    if not (args.source / 'llvm-source.json').is_file():
        raise AssertionError('--source must be a prepared common LLVM runtime tree')
    if 'COMPILER_RT_ATOMIC_BUILTIN_EXCLUDE_1_2_4' not in patched.read_text():
        raise AssertionError('prepared common source lacks the RV32 atomic width selector patch')
    obj = args.out_dir / 'atomic-selected.o'
    subprocess.run([args.cc, '-std=c11', '-DCOMPILER_RT_ATOMIC_BUILTIN_EXCLUDE_1_2_4',
                    '-Wno-deprecated-declarations', '-I', str(patched.parent),
                    '-c', str(patched), '-o', str(obj)], check=True)
    defined = symbols(args.nm, obj)
    expected = {'__atomic_is_lock_free', '__atomic_load', '__atomic_store',
                '__atomic_compare_exchange', '__atomic_fetch_add_8',
                '__atomic_fetch_and_8', '__atomic_fetch_nand_8',
                '__atomic_fetch_or_8', '__atomic_fetch_sub_8',
                '__atomic_fetch_xor_8', '__atomic_compare_exchange_8',
                '__atomic_exchange_8', '__atomic_load_8', '__atomic_store_8'}
    missing = expected - defined
    forbidden = {name for name in defined if name.startswith('__atomic_') and
                 name.rsplit('_', 1)[-1] in {'1', '2', '4'}}
    if missing or forbidden:
        raise AssertionError('atomic selector symbols mismatch: missing=' + repr(sorted(missing)) +
                             ' forbidden=' + repr(sorted(forbidden)))

    # Force only the 8-byte path through compiler-rt's real hashed lock while
    # retaining the host's native pointer-width lock implementation.
    source = patched.read_text()
    lockfree8 = '#define IS_LOCK_FREE_8(p) ATOMIC_ALWAYS_LOCK_FREE_OR_ALIGNED_LOCK_FREE(8, p)'
    if source.count(lockfree8) != 1:
        raise AssertionError('cannot isolate the 8-byte fallback for native execution')
    forced = args.out_dir / 'atomic-forced-lock.c'
    forced.write_text(source.replace(lockfree8, '#define IS_LOCK_FREE_8(p) false'))
    fixture = args.out_dir / 'atomic-contention.c'
    fixture.write_text(textwrap.dedent(r'''
        #include <assert.h>
        #include <pthread.h>
        #include <stdbool.h>
        #include <stdint.h>
        #include <stddef.h>
        #include <stdio.h>

        #define CAT_INNER(a, b) a##b
        #define CAT(a, b) CAT_INNER(a, b)
        #define STRING_INNER(x) #x
        #define STRING(x) STRING_INNER(x)
        #define ABI_SYMBOL(name) STRING(CAT(__USER_LABEL_PREFIX__, name))

        extern uint64_t builtin_add8(uint64_t *, uint64_t, int)
            __asm__(ABI_SYMBOL(__atomic_fetch_add_8));
        extern bool generic_cas(size_t, void *, void *, void *, int, int)
            __asm__(ABI_SYMBOL(__atomic_compare_exchange));
        extern void generic_load(size_t, void *, void *, int)
            __asm__(ABI_SYMBOL(__atomic_load));
        extern void generic_store(size_t, void *, void *, int)
            __asm__(ABI_SYMBOL(__atomic_store));
        extern bool atomic_is_lock_free(size_t, void *)
            __asm__(ABI_SYMBOL(__atomic_is_lock_free));

        static uint64_t counter;
        static const unsigned iterations = 150000;

        static void *fixed_width_worker(void *unused)
        {
            (void)unused;
            for (unsigned i = 0; i < iterations; i++)
                (void)builtin_add8(&counter, 1, __ATOMIC_SEQ_CST);
            return NULL;
        }

        static void *generic_worker(void *unused)
        {
            (void)unused;
            for (unsigned i = 0; i < iterations; i++) {
                uint64_t expected = 0;
                for (;;) {
                    uint64_t desired = expected + 1;
                    if (generic_cas(sizeof(counter), &counter, &expected,
                        &desired, __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST))
                        break;
                }
            }
            return NULL;
        }

        int main(void)
        {
            pthread_t fixed, generic;
            unsigned char bytes[24] = { 0 };
            uint64_t input = UINT64_C(0x12345678abcdef01), output = 0;

            assert(!atomic_is_lock_free(sizeof(counter), &counter));
            assert(atomic_is_lock_free(sizeof(uint32_t), &input));
            generic_store(sizeof(input), bytes + 1, &input, __ATOMIC_SEQ_CST);
            generic_load(sizeof(output), bytes + 1, &output, __ATOMIC_SEQ_CST);
            assert(output == input);

            assert(pthread_create(&fixed, NULL, fixed_width_worker, NULL) == 0);
            assert(pthread_create(&generic, NULL, generic_worker, NULL) == 0);
            assert(pthread_join(fixed, NULL) == 0);
            assert(pthread_join(generic, NULL) == 0);
            assert(counter == (uint64_t)iterations * 2);
            puts("PASS: compiler-rt RV32 atomic fallback contention and generic ABI");
            return 0;
        }
    '''))
    runtime = args.out_dir / 'atomic-contention'
    subprocess.run([args.cc, '-std=c11', '-O1', '-g', '-Wall', '-Wextra',
                    '-Wno-deprecated-declarations', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', '-pthread',
                    '-DCOMPILER_RT_ATOMIC_BUILTIN_EXCLUDE_1_2_4',
                    '-I', str(patched.parent), str(forced), str(fixture),
                    '-o', str(runtime)], check=True)
    subprocess.run([str(runtime)], check=True)
    print('PASS: RV32 libc atomic symbol selection')


if __name__ == '__main__':
    main()
