#!/usr/bin/env python3
"""Check the actual CJS locale-array destructor on the native build host."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def function(text, name):
    start = text.index('static ', text.index(name) - 32)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def harness(text):
    start = text.index('typedef struct {')
    end = text.index('static void gjs_clear_locale_id')
    selected = [function(text, name) for name in (
        'gjs_clear_locale_id', 'get_number_of_locale_categories',
        'gjs_locales_free', 'gjs_locales_new')]
    return ('#include <glib.h>\n#include <locale.h>\n#include <stdlib.h>\n' +
            text[start:end] + '\n'.join(selected) + r'''
static void populate(GjsLocale *array, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        array[i].id = newlocale(LC_ALL_MASK, "C", (locale_t)0);
        g_assert(array[i].id != (locale_t)0);
        array[i].name = g_strdup("C");
        array[i].prior_name = g_strdup("POSIX");
    }
}

static GPrivate locale_key = G_PRIVATE_INIT((GDestroyNotify)gjs_locales_free);

static gpointer worker(gpointer unused) {
    (void)unused;
    GjsLocale *array = gjs_locales_new();
    populate(array, get_number_of_locale_categories());
    g_private_set(&locale_key, array);
    return NULL;
}

int main(int argc, char **argv) {
    g_assert(argc == 2);
    int mode = atoi(argv[1]);
    if (mode == 3) {
        for (int i = 0; i < 4; ++i) {
            GThread *thread = g_thread_new("locale-cleanup", worker, NULL);
            g_thread_join(thread);
        }
        return 0;
    }
    GjsLocale *array = gjs_locales_new();
    if (mode == 1)
        populate(array, 1);
    else if (mode == 2)
        populate(array, get_number_of_locale_categories());
    GDestroyNotify release = (GDestroyNotify)gjs_locales_free;
    release(array);
    return 0;
}
''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('work', type=Path)
    parser.add_argument('--cc', default='/usr/bin/clang')
    parser.add_argument('--pkg-config', required=True)
    parser.add_argument('--pkg-config-libdir', required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    source = args.source / 'libgjs-private/gjs-util.c'
    baseline = source.read_text()
    candidate_dir = args.work / 'candidate/libgjs-private'
    candidate_dir.mkdir(parents=True)
    shutil.copyfile(source, candidate_dir / source.name)
    patch = Path(__file__).resolve().parents[1] / 'patches/patch-libgjs-private_gjs-util.c'
    subprocess.run(['patch', '-f', '-F0', '-p0', '-d', str(candidate_dir.parent),
                    '-i', str(patch)], check=True)
    candidate = (candidate_dir / source.name).read_text()
    env = dict(os.environ, PKG_CONFIG_SYSROOT_DIR='', PKG_CONFIG_PATH='',
               PKG_CONFIG_LIBDIR=args.pkg_config_libdir)
    flags = shlex.split(subprocess.check_output(
        [args.pkg_config, '--cflags', '--libs', 'glib-2.0'], env=env, text=True))
    results = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
               'compiler': subprocess.check_output([args.cc, '--version'], text=True),
               'leak_detection': sys.platform != 'darwin',
               'cases': []}
    for label, text in [('baseline', baseline), ('candidate', candidate)]:
        cfile = args.work / (label + '.c')
        cfile.write_text(harness(text))
        for sanitizer in [False, True]:
            suffix = '-san' if sanitizer else ''
            program = args.work / (label + suffix + '-bin')
            command = [args.cc, '-g', '-O1', '-Wall', '-Wextra', '-Werror',
                       str(cfile), '-o', str(program)]
            if sanitizer:
                command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
            command += flags
            subprocess.run(command, check=True, env=env)
            for case in range(4):
                leak_detection = int(results['leak_detection'])
                run_env = dict(env, ASAN_OPTIONS=f'detect_leaks={leak_detection}:halt_on_error=1',
                               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                result = subprocess.run([str(program), str(case)], env=run_env,
                                        capture_output=True, text=True, timeout=30)
                (args.work / f'{label}{suffix}-{case}.log').write_text(
                    result.stdout + result.stderr)
                results['cases'].append({'source': label, 'sanitizer': sanitizer,
                                         'case': case, 'status': result.returncode})
                expected_pass = label == 'candidate'
                if (result.returncode == 0) != expected_pass:
                    raise RuntimeError(f'unexpected result: {label}{suffix} case {case}')
                if sanitizer and label == 'baseline' and not any(
                        marker in result.stderr for marker in
                        ('AddressSanitizer:', 'UndefinedBehaviorSanitizer:')):
                    raise RuntimeError('baseline must fail inside a memory sanitizer')
    (args.work / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print('PASS: 8 upstream failures and 8 repaired cleanup cases')


if __name__ == '__main__':
    main()
