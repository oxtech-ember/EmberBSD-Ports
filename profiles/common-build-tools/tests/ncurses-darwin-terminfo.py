#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise default and explicit terminfo lookup in a relocated Darwin ncurses package."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True, type=Path, help="relocated ncurses SDK prefix")
    parser.add_argument("--cc", required=True, type=Path, help="selected Darwin SDK compiler or wrapper")
    parser.add_argument("--work-parent", required=True, type=Path)
    args = parser.parse_args()
    prefix = args.prefix.resolve(strict=True)
    compiler = args.cc.resolve(strict=True)
    data = prefix / "share/terminfo"
    with tempfile.TemporaryDirectory(dir=args.work_parent) as name:
        work = Path(name)
        home = work / "home"
        home.mkdir()
        env = {k: v for k, v in os.environ.items()
               if k not in ("TERMINFO", "TERMINFO_DIRS", "TERMCAP", "TERMPATH")}
        env["HOME"] = str(home)
        assert subprocess.check_output([prefix / "bin/infocmp", "-D"], env=env,
                                       text=True).splitlines() == [str(data)]
        for terminal, cap, tabset in (("a210", "if", "std"), ("abm85e", "if", "stdcrt"),
                                      ("adm36", "if", "vt100"), ("dec-vt330", "rf", "vt300")):
            selected = subprocess.check_output([prefix / "bin/tput", "-T", terminal, cap],
                                               env=env, text=True)
            path = prefix / "share/tabset" / tabset
            assert selected == str(path) and path.read_bytes()
        custom = work / "private-init"
        custom.write_bytes(b"\033[1G")
        source_entry = work / "custom.src"
        source_entry.write_text(f"ember-custom-init|custom tabset test,\n\tif={custom},\n")
        override = work / "custom-database"
        override.mkdir()
        subprocess.run([prefix / "bin/tic", "-o", override, source_entry], check=True, env=env)
        selected = subprocess.check_output([prefix / "bin/tput", "-T", "ember-custom-init", "if"],
                                           env={**env, "TERMINFO": str(override)}, text=True)
        assert selected == str(custom)
        source = work / "lookup.c"
        source.write_text(
            "#include <ncurses/curses.h>\n#include <ncurses/term.h>\n#include <stdlib.h>\n"
            "int main(int argc, char **argv) {\n"
            "    int err;\n"
            "    if (argc != 3 || setupterm(argv[1], 1, &err) == ERR || err != 1) return 1;\n"
            "    return tigetnum(\"colors\") != atoi(argv[2]);\n}\n")
        static_prefix = work / "application"
        (static_prefix / "bin").mkdir(parents=True)
        databases = [static_prefix / "share/terminfo", work / "override"]
        for path, colors in zip(databases, (53, 37)):
            path.mkdir(parents=True)
            entry = work / "term.src"
            entry.write_text(f"ember-terminfo-test|Darwin ncurses probe,\n\tcolors#{colors},\n")
            subprocess.run([prefix / "bin/tic", "-o", path, entry], env=env, check=True)
        flags = [compiler, "-I" + str(prefix / "include"),
                 "-I" + str(prefix / "include/ncurses"), source]
        shared = work / "shared"
        static = static_prefix / "bin/static"
        subprocess.run([*flags, "-L" + str(prefix / "lib"), "-lncurses",
                        "-Wl,-rpath," + str(prefix / "lib"), "-o", shared], check=True)
        subprocess.run([*flags, prefix / "lib/libncurses.a", "-o", static], check=True)
        subprocess.run([shared, "xterm-256color", "256"], env=env, check=True)
        subprocess.run([static, "ember-terminfo-test", "53"], env=env, check=True)
        for exe in (shared, static):
            for variable in ("TERMINFO", "TERMINFO_DIRS"):
                subprocess.run([exe, "ember-terminfo-test", "37"],
                               env={**env, variable: str(databases[1])}, check=True)
        subprocess.run([static, "ember-terminfo-test", "53"],
                       env={**env, "TERMINFO_DIRS": ":"}, check=True)
    print("Passed relocated shared and static Darwin terminfo lookups")


if __name__ == "__main__":
    main()
