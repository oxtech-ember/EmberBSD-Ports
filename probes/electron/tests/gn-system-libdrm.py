#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Verify GN routing and target pkg-config compilation and link."""
import argparse, json, os, shutil, subprocess, tempfile
from pathlib import Path
p = argparse.ArgumentParser()
for name in ('source', 'gn', 'cc', 'pkg-config', 'sysroot', 'host-prefix'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
source, gn, cc, pkg, sysroot, host = (getattr(a, n.replace('-', '_')).resolve(strict=True) for n in ('source', 'gn', 'cc', 'pkg-config', 'sysroot', 'host-prefix'))
env = dict(os.environ, PATH=str(host/'bin'), PKG_CONFIG_PATH='', PKG_CONFIG_LIBDIR=str(sysroot/'usr/pkg/lib/pkgconfig'), PKG_CONFIG_SYSROOT_DIR=str(sysroot))
def run(args, cwd):
    r = subprocess.run([str(x) for x in args], cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(f'{args}: {r.stdout}\n{r.stderr}')
    return r.stdout
with tempfile.TemporaryDirectory(prefix='system-libdrm-') as tmp:
    root = Path(tmp)
    for name in ('third_party/libdrm/BUILD.gn', 'build/config/linux/libdrm/BUILD.gn', 'build/config/linux/libdrm/libdrm.gni'):
        dest = root/name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source/name, dest)
    def write(name, content):
        dest = root/name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(content)
    write('.gn', 'buildconfig = "//BUILDCONFIG.gn"\n')
    write('BUILDCONFIG.gn', 'is_linux = true\nis_chromeos = false\nis_netbsd = true\nis_clang = true\nset_defaults("executable") { configs = [ "//build/config/compiler:chromium_code" ] }\nset_defaults("static_library") { configs = [ "//build/config/compiler:chromium_code" ] }\nset_default_toolchain("//:tools")\n')
    write('build/config/chromeos/args.gni', 'is_chromeos_device = false\n')
    write('build/config/cast.gni', '')
    write('build/config/linux/pkg_config.gni', 'template("pkg_config") {\n assert(invoker.packages == [ "libdrm" ])\n config(target_name) { libs = [ "drm" ] }\n}\n')
    write('build/config/compiler/BUILD.gn', 'config("chromium_code") {}\nconfig("no_chromium_code") {}\n')
    write('BUILD.gn', '''toolchain("tools") {
 tool("cc") { command = "touch {{output}}" outputs = [ "{{source_out_dir}}/{{source_name_part}}.o" ] }
 tool("alink") { command = "touch {{output}}" outputs = [ "{{target_out_dir}}/{{target_output_name}}.a" ] }
 tool("link") { command = "touch {{output}}" outputs = [ "{{target_out_dir}}/{{target_output_name}}" ] }
 tool("stamp") { command = "touch {{output}}" }
}
group("all") { deps = [ "//third_party/libdrm", "//build/config/linux/libdrm" ] }
''')
    for mode in (True, False):
        out = root/('system' if mode else 'bundled'); out.mkdir()
        (out/'args.gn').write_text('use_system_libdrm = '+str(mode).lower()+'\n')
        run([gn, 'gen', out], root)
        entry = json.loads(run([gn, 'desc', out, '//third_party/libdrm', '--format=json'], root))
        typ = next(iter(entry.values()))['type']
        assert typ == ('group' if mode else 'static_library'), typ
        deps = run([gn, 'desc', out, '//third_party/libdrm', 'deps', '--all'], root)
        if mode: assert '//build/config/linux/libdrm:libdrm' in deps and 'make_generated_static_table_fourcc' not in deps
        else: assert 'make_generated_static_table_fourcc' in deps
    flags = run([pkg, '--cflags', '--libs', 'libdrm'], root).split()
    assert '-ldrm' in flags and str(sysroot/'usr/pkg/include') in ' '.join(flags) and str(sysroot/'usr/pkg/lib') in ' '.join(flags)
    program = root/'probe.c'; program.write_text('#include <xf86drm.h>\nint main(void) { return drmGetDevices2(0, 0, 0) < 0; }\n')
    run([cc, program, *flags, '-o', root/'probe'], root)
    print('system and bundled GN routes and target libdrm compile/link passed')
