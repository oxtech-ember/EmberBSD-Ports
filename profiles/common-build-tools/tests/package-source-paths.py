"""Check source locations emitted by the selected package compilers."""

import argparse
import json
import shlex
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", required=True, type=Path)
    parser.add_argument("--host-prefix", required=True, type=Path)
    parser.add_argument("--makeconf", required=True, type=Path)
    args = parser.parse_args()
    bindir = args.host_prefix.resolve() / "bin"
    pkgsrc = args.pkgsrc.resolve()
    cases = (
        ("graphics/libavif", "CWRAPPERS_PREPEND.cc", "clang", "unit.c"),
        ("textproc/xerces-c", "CWRAPPERS_PREPEND.cxx", "clang++", "unit.cpp"),
        ("graphics/libimagequant", "RUSTFLAGS", "rustc", "unit.rs"),
    )
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp).resolve()
        source = work / "package-source"
        source.mkdir()
        for package, variable, compiler, name in cases:
            query = [bindir / "bmake", "-C", pkgsrc / package, f"PKGSRCDIR={pkgsrc}",
                     f"MAKECONF={args.makeconf.resolve()}", f"WRKDIR={work}",
                     "-V", "${" + variable + "}", "-V", "${USE_CROSS_COMPILE}",
                     "-V", "${CROSS_DESTDIR}", "-V", "${TOOLBASE}"]
            value, cross, sysroot, tools = subprocess.check_output(query, text=True).splitlines()
            flags = shlex.split(value)
            header_paths = []
            if compiler == "rustc":
                code = '#![no_std]\n#[used]\npub static SOURCE: &str = file!();\n'
                options = ["--crate-type=lib", "--emit=obj"]
            else:
                code = 'const char *package_source(void) { return __FILE__; }\n'
                options = ["-c"]
                if cross.lower() == "yes" and sysroot:
                    header_paths = [(sysroot + "/usr/include/test.h", "/usr/include/test.h"),
                                    (tools + "/lib/clang/test/header.h", "/usr/lib/clang/test/header.h")]
                    for index, (physical, _) in enumerate(header_paths):
                        code += f'#line 1 {json.dumps(physical)}\n'
                        code += f'const char *header_{index}(void) {{ return __FILE__; }}\n'
            (source / name).write_text(code)
            obj = work / (name + ".o")
            subprocess.run([bindir / compiler, *flags, *options, source / name, "-o", obj],
                           check=True)
            data = obj.read_bytes()
            if bytes(work) in data or f"package-source/{name}".encode() not in data:
                raise SystemExit(f"{package}: {compiler} did not emit a relative source location")
            for physical, logical in header_paths:
                if physical.encode() in data or logical.encode() not in data:
                    raise SystemExit(f"{package}: {compiler} did not map {logical}")
            print(f"{package}: {name} has a relative source location")


if __name__ == "__main__":
    main()
