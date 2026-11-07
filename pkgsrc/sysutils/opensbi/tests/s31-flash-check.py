#!/usr/bin/env python3
"""Run boundary cases against OpenSBI's S31 flash range validator."""
import pathlib
import os
import subprocess
import sys
import tempfile

root = pathlib.Path(sys.argv[1])
source = root / "platform/generic/espressif/esp32s31/esp32s31.c"
text = source.read_text()
name = "s31_flash_range_valid"
marker = "bool " + name + "("
start = text.find(marker)
if start < 0:
    raise SystemExit("missing S31 flash range validator")
brace = text.find("{", start)
depth = 0
end = brace
while end < len(text):
    if text[end] == "{":
        depth += 1
    elif text[end] == "}":
        depth -= 1
        if depth == 0:
            end += 1
            break
    end += 1
if depth:
    raise SystemExit("unterminated S31 flash range validator")
function = text[start:end]

flash_source = root / "platform/generic/espressif/esp32s31/flash.c"
flash_text = flash_source.read_text()
result_token = "s31_flash_result("
result_pos = flash_text.find(result_token)
result_start = flash_text.rfind("static int", 0, result_pos)
if result_pos < 0 or result_start < 0:
    raise SystemExit("missing S31 ROM/cache result mapper")
result_brace = flash_text.find("{", result_start)
result_depth = 0
result_end = result_brace
while result_end < len(flash_text):
    if flash_text[result_end] == "{":
        result_depth += 1
    elif flash_text[result_end] == "}":
        result_depth -= 1
        if result_depth == 0:
            result_end += 1
            break
    result_end += 1
if result_depth:
    raise SystemExit("unterminated S31 ROM/cache result mapper")
result_function = flash_text[result_start:result_end]

ack_token = "s31_flash_park_ack_matches("
ack_pos = flash_text.find(ack_token)
ack_start = flash_text.rfind("static bool", 0, ack_pos)
if ack_pos < 0 or ack_start < 0:
    raise SystemExit("missing generation-tagged hart acknowledgement check")
ack_brace = flash_text.find("{", ack_start)
ack_depth = 0
ack_end = ack_brace
while ack_end < len(flash_text):
    if flash_text[ack_end] == "{":
        ack_depth += 1
    elif flash_text[ack_end] == "}":
        ack_depth -= 1
        if ack_depth == 0:
            ack_end += 1
            break
    ack_end += 1
if ack_depth:
    raise SystemExit("unterminated generation-tagged hart acknowledgement check")
ack_function = flash_text[ack_start:ack_end]

cleanup_token = "s31_flash_park_cleanup("
cleanup_pos = flash_text.find(cleanup_token)
cleanup_start = flash_text.rfind("static void", 0, cleanup_pos)
if cleanup_pos < 0 or cleanup_start < 0:
	raise SystemExit("missing generation-safe hart cleanup")
cleanup_brace = flash_text.find("{", cleanup_start)
cleanup_depth = 0
cleanup_end = cleanup_brace
while cleanup_end < len(flash_text):
	if flash_text[cleanup_end] == "{":
		cleanup_depth += 1
	elif flash_text[cleanup_end] == "}":
		cleanup_depth -= 1
		if cleanup_depth == 0:
			cleanup_end += 1
			break
	cleanup_end += 1
if cleanup_depth:
	raise SystemExit("unterminated generation-safe hart cleanup")
cleanup_function = flash_text[cleanup_start:cleanup_end]

host = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#define SBI_EFAIL (-1)
typedef uint32_t u32;
""" + function + result_function + ack_function + cleanup_function + r"""
int main(void)
{
	volatile u32 pending_generation = 2;
	volatile u32 parked_generation = 1;
	const u32 capacity = 16 * 1024 * 1024;
	assert(s31_flash_range_valid(0, 4, capacity, 4, 4096));
	assert(s31_flash_range_valid(capacity - 4, 4, capacity, 4, 4096));
	assert(s31_flash_range_valid(capacity, 0, capacity, 4, 4096));
	assert(!s31_flash_range_valid(capacity + 1, 0, capacity, 4, 4096));
	assert(!s31_flash_range_valid(capacity - 4, 8, capacity, 4, 4096));
	assert(!s31_flash_range_valid(0, 4097, capacity, 4, 4096));
	assert(!s31_flash_range_valid(2, 4, capacity, 4, 4096));
	assert(!s31_flash_range_valid(0, 2, capacity, 4, 4096));
	assert(!s31_flash_range_valid(0, 4, capacity, 0, 4096));
	assert(!s31_flash_range_valid(0, 4, 0, 4, 4096));
	assert(s31_flash_range_valid(4096, 4096, capacity, 4096, 4096));
	assert(!s31_flash_range_valid(4, 4096, capacity, 4096, 4096));
	assert(!s31_flash_range_valid(4096, 8192, capacity, 4096, 4096));
	assert(s31_flash_result(0, 0) == 0);
	assert(s31_flash_result(1, 0) == SBI_EFAIL);
	assert(s31_flash_result(0, SBI_EFAIL) == SBI_EFAIL);
	assert(!s31_flash_park_ack_matches(1, 2));
	assert(!s31_flash_park_ack_matches(0, 2));
	assert(s31_flash_park_ack_matches(2, 2));
	/* An old callback's delayed exit must preserve a newer pending request. */
	s31_flash_park_cleanup(&pending_generation, &parked_generation, 1);
	assert(pending_generation == 2);
	assert(parked_generation == 0);
	return 0;
}
"""

with tempfile.TemporaryDirectory(prefix="opensbi-s31-flash-") as tmp:
	path = pathlib.Path(tmp) / "check.c"
	binary = pathlib.Path(tmp) / "check"
	path.write_text(host)
	subprocess.run([os.environ["CC"], "-std=c11", "-Wall", "-Wextra", "-Werror",
	                str(path), "-o", str(binary)], check=True)
	subprocess.run([str(binary)], check=True)

print("S31 flash range validation passed")
