#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), compile an actual consumer through installed metadata.
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    if len(sys.argv) not in (5, 6) or (len(sys.argv) == 6 and sys.argv[5] not in ("epoxy", "desktop-gl")):
        raise SystemExit("usage: mesa-pkgconfig.py CROSS_TOOLS SYSROOT HOST_PKG_CONFIG NEW_WORK [epoxy|desktop-gl]")
    desktop = len(sys.argv) == 6 and sys.argv[5] == "desktop-gl"
    epoxy = len(sys.argv) == 6
    tools, sysroot, pkgconfig = (Path(arg).resolve(strict=True) for arg in sys.argv[1:4])
    work = Path(sys.argv[4]).absolute()
    if work.exists() or work.is_symlink():
        raise SystemExit("NEW_WORK must not exist")
    work.mkdir(parents=True)
    cc = tools / "bin/aarch64--netbsd-gcc"
    readelf = tools / "bin/aarch64--netbsd-readelf"
    source = Path(__file__).resolve().parent.parent / "cross/mesa-render.c"
    prefix = sysroot / "usr/pkg"
    environment = {"PKG_CONFIG_PATH": "", "PKG_CONFIG_LIBDIR": f"{prefix}/lib/pkgconfig:{prefix}/share/pkgconfig",
                   "PKG_CONFIG_SYSROOT_DIR": str(sysroot)}

    def run(env, name, command):
        command = [str(arg) for arg in command]
        log = work / name
        Path(str(log) + ".command").write_text(shlex.join(command) + "\n")
        result = subprocess.run(command, env=os.environ | env, capture_output=True, text=True, timeout=300, check=False)
        log.write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit(f"failed: {log}")
        return result.stdout.strip()

    modules = "gl glx egl gbm glesv1_cm glesv2 dri".split()
    if epoxy:
        modules.append("epoxy")
    for module in modules:
        version = run(environment, module + "-version.log", [pkgconfig, "--modversion", module])
        if version != ("1.5.10" if module == "epoxy" else "26.2.5"):
            raise SystemExit(f"wrong {module} provider")
        run(environment, module + "-shared.log", [pkgconfig, "--cflags", "--libs", module])
        run(environment, module + "-static-metadata.log", [pkgconfig, "--static", "--cflags", "--libs", module])
    link_modules = ["epoxy", "gbm"] if epoxy else ["egl", "glesv2", "gbm"]
    flags = shlex.split(run(environment, "consumer-flags.log", [pkgconfig, "--cflags", "--libs", *link_modules]))
    if epoxy:
        flags.append("-DEMBER_EPOXY_DISPATCH")
    if desktop:
        flags.append("-DEMBER_DESKTOP_GL")
    executable = work / (("epoxy" if epoxy else "mesa") + "-pkgconfig-render")
    # PIC keeps dispatch-pointer imports as undefined GOT entries instead of COPY relocations.
    command = [cc, f"--sysroot={sysroot}", "-std=c11", "-D_NETBSD_SOURCE", "-O2", "-fPIC", "-pie", "-Wall", "-Wextra", "-Werror",
               source, *flags, "-pthread", f"-Wl,-rpath-link,{prefix}/lib", f"-Wl,-rpath-link,{prefix}/gcc16/lib",
               "-Wl,-rpath,/usr/pkg/lib", "-Wl,-rpath,/usr/pkg/gcc16/lib", "-o", executable]
    run({}, "consumer-build.log", command)
    elf = run({}, "consumer-elf.log", [readelf, "-h", "-d", "-Ws", executable])
    providers = ["libepoxy.so.0", "libgbm.so.1"] if epoxy else ["libEGL.so.1", "libGLESv2.so.2", "libgbm.so.1"]
    if "AArch64" not in elf or not all(f"[{name}]" in elf for name in providers):
        raise SystemExit("consumer is not target ELF with selected providers")
    if epoxy:
        if "[libEGL.so.1]" in elf or "[libGLESv2.so.2]" in elf:
            raise SystemExit("epoxy consumer bypasses dynamic dispatch")
        if not all(re.search(r"UND\s+" + name + r"(?:\s|$)", elf) for name in
                   ("epoxy_eglGetError", "epoxy_glGetString", "epoxy_glDrawArrays")):
            raise SystemExit("missing actual epoxy dispatch symbols")
    if str(sysroot) in elf or str(work) in elf:
        raise SystemExit("consumer runtime metadata leaks the build sysroot")
    inputs = [Path(__file__).resolve(), source, cc, readelf, pkgconfig, executable, work / "consumer-build.log.command"]
    inputs.extend(prefix / "lib/pkgconfig" / (name + ".pc") for name in modules)
    (work / "inputs.sha256").write_text("".join(f"{digest(path)}  {path}\n" for path in inputs))
    print(f"PASS: {len(modules)} actual pkg-config modules, private metadata and cross-linked "
          + ("epoxy dispatch" if epoxy else "EGL/GLES/GBM") + " consumer")
    print("Static metadata queries do not establish a static Mesa build; execute the consumer on the target separately.")


if __name__ == "__main__":
    main()
