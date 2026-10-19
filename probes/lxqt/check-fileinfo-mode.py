#!/usr/bin/env python3
"""Check the real libfm-qt file-mode block with optional GIO attributes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess


HARNESS = r'''
#include <gio/gio.h>
#include <sys/stat.h>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <memory>

static guint32 file_mode(const std::unique_ptr<GFileInfo, decltype(&g_object_unref)>& inf) {
    const char* tmp = g_file_info_get_attribute_string(inf.get(), G_FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE);
    GFileType type = g_file_info_get_file_type(inf.get());
    guint32 mode_ = g_file_info_get_attribute_uint32(inf.get(), G_FILE_ATTRIBUTE_UNIX_MODE);
@ACTUAL_BLOCK@
    return mode_;
}

struct Case { GFileType type; const char* content; guint32 mode; guint32 expected; };
static const Case cases[] = {
    {G_FILE_TYPE_SPECIAL, nullptr, 0, 0},
    {G_FILE_TYPE_SPECIAL, nullptr, S_IFCHR | 0600, S_IFCHR | 0600},
    {G_FILE_TYPE_SPECIAL, "inode/chardevice", 0, S_IFCHR},
    {G_FILE_TYPE_SPECIAL, "inode/blockdevice", 0, S_IFBLK},
    {G_FILE_TYPE_SPECIAL, "inode/fifo", 0, S_IFIFO},
    {G_FILE_TYPE_SPECIAL, "inode/socket", 0, S_IFSOCK},
    {G_FILE_TYPE_SPECIAL, "", 0, 0},
    {G_FILE_TYPE_SPECIAL, "application/octet-stream", 0, 0},
    {G_FILE_TYPE_REGULAR, nullptr, 0, S_IFREG},
    {G_FILE_TYPE_DIRECTORY, nullptr, 0, S_IFDIR},
    {G_FILE_TYPE_SYMBOLIC_LINK, nullptr, 0, S_IFLNK},
    {G_FILE_TYPE_UNKNOWN, nullptr, 0, 0},
    {G_FILE_TYPE_REGULAR, nullptr, S_IFREG | 0644, S_IFREG | 0644},
};

int main(int argc, char** argv) {
    if(argc != 2) return 2;
    int index = std::atoi(argv[1]);
    if(index < 0 || index >= int(sizeof(cases) / sizeof(cases[0]))) return 2;
    const auto& c = cases[index];
    std::unique_ptr<GFileInfo, decltype(&g_object_unref)> inf(g_file_info_new(), &g_object_unref);
    g_file_info_set_file_type(inf.get(), c.type);
    if(c.content) g_file_info_set_attribute_string(inf.get(), G_FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE, c.content);
    if(c.mode) g_file_info_set_attribute_uint32(inf.get(), G_FILE_ATTRIBUTE_UNIX_MODE, c.mode);
    guint32 actual = file_mode(inf);
    if(actual != c.expected) {
        std::fprintf(stderr, "mode case %d: expected %o, got %o\n", index, c.expected, actual);
        return 1;
    }
    std::printf("mode case %d PASS\n", index);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--pkg-config', required=True)
    parser.add_argument('--pkgconfig-dir', type=Path, required=True)
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    source = args.source.resolve() / 'src/core/fileinfo.cpp'
    text = source.read_text()
    start = text.index('    if(0 == mode_) {')
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    block = text[start:end]
    assert 'G_FILE_TYPE_SPECIAL' in block and 'strcmp(tmp, "inode/chardevice")' in block
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    (args.output/'df-before.txt').write_text(subprocess.check_output(['df', '-k', str(args.output)], text=True))
    test = args.output/'fileinfo-mode.cpp'
    test.write_text(HARNESS.replace('@ACTUAL_BLOCK@', block))
    env = dict(os.environ, PKG_CONFIG_LIBDIR=str(args.pkgconfig_dir))
    env.pop('PKG_CONFIG_SYSROOT_DIR', None)
    env.pop('PKG_CONFIG_PATH', None)
    flags = shlex.split(subprocess.check_output([args.pkg_config, '--cflags', '--libs', 'gio-2.0'], env=env, text=True))
    binary = args.output/'fileinfo-mode'
    command = [args.compiler, '-std=c++20', '-g', '-O1', '-fsanitize=address,undefined',
               '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', str(test), '-o', str(binary)] + flags
    compiled = subprocess.run(command, env=env, capture_output=True, text=True)
    (args.output/'build.log').write_text(compiled.stdout + compiled.stderr)
    assert compiled.returncode == 0, compiled.stderr
    env.update(ASAN_OPTIONS='halt_on_error=1:detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    result = {'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'block_sha256': hashlib.sha256(block.encode()).hexdigest(), 'build_command': command,
              'compiler': subprocess.check_output([args.compiler, '--version'], text=True).splitlines()[0],
              'glib_version': subprocess.check_output([args.pkg_config, '--modversion', 'gio-2.0'], env=env, text=True).strip(),
              'scope': 'Actual mode-selection block with real GFileInfo objects and attributes. Other FileInfo behavior is not executed. Dependency libraries are not instrumented. LeakSanitizer is unavailable on macOS/arm64. This is not Valgrind.',
              'baseline': args.baseline, 'cases': []}
    for index in range(13):
        run = subprocess.run([str(binary), str(index)], env=env, capture_output=True, text=True)
        (args.output/f'{index:02d}.stdout').write_text(run.stdout)
        (args.output/f'{index:02d}.stderr').write_text(run.stderr)
        if index == 0 and args.baseline:
            assert run.returncode != 0 and ('runtime error:' in run.stderr or 'AddressSanitizer' in run.stderr), (run.stdout, run.stderr)
        else:
            assert run.returncode == 0 and run.stdout == f'mode case {index} PASS\n' and not run.stderr, (index, run.stdout, run.stderr)
        result['cases'].append({'index': index, 'status': run.returncode, 'expected_failure': args.baseline and index == 0})
    (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'output':str(args.output), 'cases':len(result['cases']), 'baseline_failures':int(args.baseline)}, indent=2))


if __name__ == '__main__':
    main()
