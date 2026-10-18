#!/usr/bin/env python3
"""Exercise the actual upstream RGB parser and file reads with sanitizers."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile

archive, work = map(Path, sys.argv[1:])
assert not work.exists(), "Use a new work directory"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == "65de6470f7331b86b90c4644f13074c3edaff6fdb98a2f43b3f53750a924d8d4"
work.mkdir(parents=True)
with tarfile.open(archive) as source:
    source.extractall(work, filter="data")
tree = work / "sxmo-utils-1.18.1"
production = tree / "programs/sxmo_status_led.c"
wrapper = work / "led-check.c"
wrapper.write_text(r'''
#define main sxmo_original_main
#include "sxmo_status_led.c"
#undef main
int main(int argc, char **argv) {
    quiet = true;
    if (argc != 4) return 2;
    if (strcmp(argv[1], "parse") == 0) {
        enum color colors[COLOR_MAX];
        int actual = parse_color_ids(argv[2], strlen(argv[2]), colors);
        if (!!actual != atoi(argv[3])) return 1;
    } else if (strncmp(argv[1], "group", 5) == 0) {
        struct status_handle led;
        int with_zero = strchr(argv[1], '0') != NULL;
        if (with_zero) close(0);
        led_dir = argv[2];
        int actual = open_led_group(&led, "status", "red", "green", "blue", false);
        if (actual) for (int color = 0; color < COLOR_MAX; color++) close_single_led(&led.group[color]);
        if (with_zero && fcntl(0, F_GETFD) != -1) return 1;
        if (!!actual != atoi(argv[3])) return 1;
    } else {
        struct multicolor_handle handle;
        if (strcmp(argv[1], "file0") == 0) close(0);
        led_dir = argv[2];
        int actual = open_multicolor_led("status", &handle);
        if (actual) { fclose(handle.brightness); fclose(handle.multi_intensity); }
        if (!!actual != atoi(argv[3])) return 1;
    }
    return 0;
}
''')
command = [os.environ.get("CC", "/usr/bin/cc"), "-std=c99", "-D_POSIX_C_SOURCE=200809L", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-I" + str(production.parent), str(wrapper), "-lm", "-o", str(work / "led-check")]
environment = {**os.environ, "UBSAN_OPTIONS": "halt_on_error=1"}
normal = work / "normal/rgb:status"
normal.mkdir(parents=True)
for name, content in {"multi_index": "red green blue\n", "max_brightness": "255\n", "brightness": "0\n", "multi_intensity": "0 0 0\n"}.items():
    (normal / name).write_text(content)
fixtures = {}
for name, data in {"full-buffer": b"x" * 128, "empty-file": b""}.items():
    folder = work / name / "rgb:status"
    folder.mkdir(parents=True)
    (folder / "multi_index").write_bytes(data)
    fixtures[name] = folder.parent
folder = work / "read-error/rgb:status/multi_index"
folder.mkdir(parents=True)
fixtures["read-error"] = folder.parent.parent
group = work / "group"
for color in ("red", "green", "blue"):
    folder = group / (color + ":status")
    folder.mkdir(parents=True)
    (folder / "brightness").write_text("0\n")
    (folder / "max_brightness").write_text("255\n")
partial_group = work / "partial-group/red:status"
partial_group.mkdir(parents=True)
(partial_group / "brightness").write_text("0\n")
(partial_group / "max_brightness").write_text("255\n")

def run(arguments, label):
    result = subprocess.run([str(work / "led-check"), *arguments], env=environment, capture_output=True)
    (work / (label + ".stderr")).write_bytes(result.stderr)
    return result.returncode

subprocess.run(command, check=True)
controls = [(["parse", "", "0"], "empty-sentinel"), (["parse", "red green blue red", "0"], "four-colors"), (["file", str(fixtures["full-buffer"]), "0"], "full-buffer"), (["file", str(fixtures["read-error"]), "0"], "read-error"), (["group0", str(partial_group.parent), "0"], "descriptor-zero-leak")]
for arguments, label in controls:
    assert run(arguments, "original-" + label) != 0, label
patch = Path(__file__).resolve().parent.parent / "patches/patch-programs_sxmo_status_led.c"
subprocess.run(["patch", "-p0", "-F", "0", "-i", str(patch)], cwd=tree, check=True)
subprocess.run(command, check=True)
cases = [["parse", value, str(expected)] for value, expected in [("red green blue", 1), ("blue red green\n", 1), ("", 0), ("red green", 0), ("red green blue red", 0), ("red red blue", 0), ("r g b", 0), ("red green brown", 0), ("\xff green blue", 0)]]
cases += [["file", str(folder), "0"] for folder in fixtures.values()]
cases += [["file", str(normal.parent), "1"], ["file0", str(normal.parent), "1"]]
cases += [["group", str(group), "1"], ["group0", str(group), "1"], ["group", str(partial_group.parent), "0"], ["group0", str(partial_group.parent), "0"]]
for number, arguments in enumerate(cases):
    assert run(arguments, "patched-" + str(number)) == 0, arguments
print(f"PASS: {len(cases)} production parser/file cases; five original failure controls; ASan/UBSan and descriptor checks")
