#!/usr/bin/env python3
"""Exercise S31 reset-type policy and inspect the target ROM call lowering."""
import os
import pathlib
import re
import subprocess
import sys
import tempfile


source = pathlib.Path(sys.argv[1])
platform = (source / "platform/generic/espressif/esp32s31/esp32s31.c").read_text()


def function(name):
    marker = "static "
    start = platform.index(name)
    start = platform.rfind(marker, 0, start)
    brace = platform.index("{", start)
    depth = 0
    for pos in range(brace, len(platform)):
        if platform[pos] == "{":
            depth += 1
        elif platform[pos] == "}":
            depth -= 1
            if depth == 0:
                return platform[start : pos + 1]
    raise RuntimeError("unterminated function: " + name)


check_fn = function("s31_system_reset_check(")
reset_fn = function("s31_system_reset(")
if "0x2f800094UL" not in platform or "LP_AONCLKRST_HPCORE0_RESET_CTRL_REG" in platform:
    raise SystemExit("S31 reset source no longer selects the documented ROM system reset")
macro_start = platform.index("#define ESP32S31_ROM_SOFTWARE_RESET_SYSTEM")
macro_end = platform.index("\n\nstatic int s31_system_reset_check", macro_start)
rom_macro = platform[macro_start:macro_end]

interface = (source / "include/sbi/sbi_ecall_interface.h").read_text()
reset_types = {}
for name in ("SHUTDOWN", "COLD_REBOOT", "WARM_REBOOT"):
    match = re.search(
        r"^#define SBI_SRST_RESET_TYPE_" + name + r"\s+(0x[0-9a-fA-F]+|[0-9]+)\s*$",
        interface,
        re.MULTILINE,
    )
    if not match:
        raise SystemExit("missing SBI reset type " + name)
    reset_types[name] = int(match.group(1), 0)
if len(set(reset_types.values())) != len(reset_types):
    raise SystemExit("SBI reset types are not distinct")
unknown_type = max(reset_types.values()) + 1
type_defines = "\n".join(
    "#define SBI_SRST_RESET_TYPE_" + name + " " + str(value)
    for name, value in reset_types.items()
)

host_reset = reset_fn.replace("S31_ROM_SYSTEM_RESET();", "test_rom_reset();")
host_reset = host_reset.replace(
    '__asm__ __volatile__("wfi");', "test_wfi();"
)
if host_reset == reset_fn:
    raise RuntimeError("host reset hooks were not applied")

host = r"""
#include <assert.h>
#include <setjmp.h>
#include <string.h>
typedef unsigned int u32;
""" + type_defines + r"""
#define UNKNOWN_RESET_TYPE """ + str(unknown_type) + r"""
static jmp_buf park;
static int reset_calls, diagnostic_calls, wait_calls;
static const char *diagnostic;
static void test_rom_reset(void) { reset_calls++; }
static void test_wfi(void) { wait_calls++; longjmp(park, 1); }
static int test_printf(const char *message) {
    diagnostic_calls++;
    diagnostic = message;
    return 0;
}
#define sbi_printf test_printf
""" + check_fn + "\n" + host_reset + r"""
int main(void) {
    assert(s31_system_reset_check(SBI_SRST_RESET_TYPE_COLD_REBOOT, 0) == 1);
    assert(s31_system_reset_check(SBI_SRST_RESET_TYPE_WARM_REBOOT, 0) == 1);
    assert(s31_system_reset_check(SBI_SRST_RESET_TYPE_SHUTDOWN, 0) == 0);
    assert(s31_system_reset_check(UNKNOWN_RESET_TYPE, 0) == 0);
    if (setjmp(park) == 0)
        s31_system_reset(SBI_SRST_RESET_TYPE_COLD_REBOOT, 0);
    assert(reset_calls == 1 && diagnostic_calls == 1 && wait_calls == 1);
    assert(strcmp(diagnostic, "OpenSBI: ESP32-S31 ROM system reset returned\n") == 0);
    return 0;
}
"""

target = r"""
typedef unsigned int u32;
""" + type_defines + r"""
#define UNKNOWN_RESET_TYPE """ + str(unknown_type) + r"""
""" + rom_macro + r"""
extern int sbi_printf(const char *, ...);
""" + check_fn + "\n" + reset_fn + "\n"
target += r"""
__attribute__((noinline, used)) int target_check(u32 type, u32 reason) {
    return s31_system_reset_check(type, reason);
}
__attribute__((noinline, used)) void target_reset(u32 type, u32 reason) {
    s31_system_reset(type, reason);
}
"""

with tempfile.TemporaryDirectory(prefix="opensbi-s31-reset-") as tmp:
    tmpdir = pathlib.Path(tmp)
    host_c = tmpdir / "host.c"
    host_exe = tmpdir / "host"
    host_c.write_text(host)
    subprocess.run(
        [os.environ["CC"], "-std=c11", "-Wall", "-Wextra", "-Werror",
         "-Wno-unused-parameter", "-fsanitize=address,undefined",
         "-fno-sanitize-recover=all", str(host_c), "-o", str(host_exe)],
        check=True,
    )
    subprocess.run([str(host_exe)], check=True)

    target_c = tmpdir / "target.c"
    target_s = tmpdir / "target.s"
    target_c.write_text(target)
    subprocess.run(
        [os.environ["RISCV_CC"], "-target", "riscv32-unknown-elf",
         "-march=rv32imac_zicsr_zifencei", "-mabi=ilp32", "-O2",
         "-fno-pic", "-fno-pie", "-S", str(target_c), "-o", str(target_s)],
        check=True,
    )
    asm = target_s.read_text()
    has_full_immediate = re.search(r"\bli\s+(a\d+),\s*796917908\b", asm)
    has_lui_addi = re.search(
        r"\blui\s+(a\d+),\s*194560\s*\n\s*addi\s+\1,\s*\1,\s*148\b",
        asm,
    )
    if not (has_full_immediate or has_lui_addi) or not re.search(r"\bjalr\b", asm):
        raise SystemExit(
            "RV32 output does not call S31 ROM reset entry 0x2f800094:\\n" + asm
        )

print("S31 reset policy, return fallback, and RV32 ROM call checks passed")
