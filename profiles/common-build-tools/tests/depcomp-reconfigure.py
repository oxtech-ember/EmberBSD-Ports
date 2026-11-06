#!/usr/bin/env python3
# Copyright (c) 2026 EmberBSD contributors
# SPDX-License-Identifier: BSD-2-Clause
"""Check native depcomp selection across a second Autoconf configure."""

import argparse
import os
from pathlib import Path
import subprocess


def run(command, cwd, env):
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=120, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"{command}:\n{result.stdout[-3000:]}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("prefix", "tools", "old-mk", "new-mk", "output"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    tools = args.tools.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    shell = tools / "sh"
    env = dict(os.environ, PATH=f"{tools}:{prefix}/bin:{prefix}/gnu/bin",
               CC=str(prefix / "bin/clang"), CONFIG_SHELL=str(shell),
               SHELL=str(shell))

    for name, mk in (("old", args.old_mk), ("new", args.new_mk)):
        work = output / name
        work.mkdir(exist_ok=False)
        (work / "configure.ac").write_text(
            "AC_INIT([test],[1])\nAM_INIT_AUTOMAKE([foreign])\n"
            "AC_PROG_CC\nAC_CONFIG_FILES([Makefile])\nAC_OUTPUT\n"
        )
        (work / "Makefile.am").write_text(
            "bin_PROGRAMS = probe\nprobe_SOURCES = main.c\n"
        )
        (work / "main.c").write_text(
            '#include "value.h"\nint main(void){return VALUE;}\n'
        )
        (work / "value.h").write_text("#define VALUE 0\n")
        run([str(prefix / "bin/aclocal")], work, env)
        run([str(prefix / "bin/automake"), "--add-missing", "--foreign"], work, env)
        run([str(prefix / "bin/autoconf")], work, env)
        run([str(shell), "./configure"], work, env)
        (work / "owner.mk").write_text(f'''WRKSRC={work}
TOOLBASE={prefix}
USE_CROSS_COMPILE=no
OVERRIDE_DIRDEPTH=0
RM=rm
LN=ln
ECHO=echo
CHMOD=chmod
TOOLS_SH={shell}
STEP_MSG=echo
RUN=@
.include "{mk.resolve()}"
''')
        run([str(prefix / "bin/bmake"), "-f", "owner.mk", "depcomp-override"], work, env)
        configured = run([str(shell), "./configure"], work, env)
        mode = [line for line in configured.splitlines()
                if "dependency style of" in line][-1]
        print(name, mode, flush=True)
        if name == "old":
            assert mode.endswith("none"), mode
            continue
        assert mode.endswith("gcc3"), mode
        make = [str(prefix / "bin/gmake"), f"SHELL={shell}"]
        run(make, work, env)
        before = (work / "main.o").stat().st_mtime_ns
        run(make, work, env)
        assert (work / "main.o").stat().st_mtime_ns == before
        (work / "value.h").write_text("#define VALUE 1\n")
        build_output = run(make, work, env)
        assert (work / "main.o").stat().st_mtime_ns != before, build_output
        result = subprocess.run([str(work / "probe")], env=env, timeout=120, check=False)
        assert result.returncode == 1
        print("new: no-op and changed-header rebuild PASS", flush=True)


if __name__ == "__main__":
    main()
