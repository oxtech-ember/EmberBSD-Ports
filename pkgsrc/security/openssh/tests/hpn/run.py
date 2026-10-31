#!/usr/bin/env python3
"""Exercise selected OpenSSH HPN configuration and window paths on the host."""
import argparse
import subprocess
import sys
from pathlib import Path


def extract(source, signature):
    start = source.index(signature)
    end = source.index("\n}\n", start) + 3
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--lpk", action="store_true",
                        help="also exercise the native LDAP configuration")
    args = parser.parse_args()
    cc, source, build, prefix, work = (p.resolve() for p in (
        args.cc, args.source, args.build_dir, args.prefix, args.work_dir))
    work.mkdir(parents=True, exist_ok=True)
    tests = Path(__file__).resolve().parent
    flags = ["-fsanitize=address,undefined"] if args.sanitize else []
    include = ["-I", str(source), "-I", str(build), "-I", str(prefix / "include")]
    common = [str(cc), *flags, "-DWITH_HPN", "-DHAVE_CONFIG_H", *include]
    if args.lpk:
        common.append("-DWITH_NETBSD_LPK")
    archives = [str(build / "libssh.a"), str(build / "openbsd-compat/libopenbsd-compat.a")]
    ld = ["-L", str(prefix / "lib"), f"-Wl,-rpath,{prefix / 'lib'}",
          "-Wl,-dead_strip" if sys.platform == "darwin" else "-Wl,--gc-sections",
          "-lcrypto", "-lz"]

    if args.lpk:
        ld += ["-lldap", "-llber"]
    objects = ("readconf", "servconf", "ldapauth") if args.lpk else ("readconf", "servconf")
    for name in objects:
        obj = work / (name + ".o")
        subprocess.run([*common, "-ffunction-sections", "-c", str(source / (name + ".c")),
                        "-o", str(obj)], check=True, cwd=work)
    lpk_objects = [str(work / "ldapauth.o")] if args.lpk else []
    for name, obj, extra in (("client", "readconf.o", []),
                             ("server", "servconf.o", [str(build / "groupaccess.o")]),
                             ("server-parse", "servconf.o", [str(build / "groupaccess.o")])):
        exe = work / name
        subprocess.run([*common, str(tests / (name + ".c")), str(work / obj), *lpk_objects,
                        *extra, *archives, *ld, "-o", str(exe)], check=True, cwd=work)
        subprocess.run([str(exe)], check=True, cwd=work)
        print(name, "PASS", flush=True)
    for name, file, signatures in (
            ("init", "ssh.c", ("static void\nhpn_options_init(",)),
            ("window", "channels.c", ("static u_int\nchannel_tcpwinsz(",
                                      "static int\nchannel_check_window("))):
        template = (tests / (name + ".c.in")).read_text()
        text = (source / file).read_text()
        for signature in signatures:
            key = signature.split("(")[0].split()[-1]
            template = template.replace("@@" + key + "@@", extract(text, signature))
        fixture, exe = work / (name + ".c"), work / name
        fixture.write_text(template)
        subprocess.run([str(cc), *flags, "-Wall", "-Wextra", "-Werror", str(fixture),
                        "-o", str(exe)], check=True, cwd=work)
        subprocess.run([str(exe)], check=True, cwd=work)


if __name__ == "__main__":
    main()
