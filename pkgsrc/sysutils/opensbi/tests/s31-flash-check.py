#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Check S31 flash range and cache synchronization behavior."""
import pathlib
import os
import subprocess
import sys
import tempfile


def extract(text, signature):
	start = text.find(signature)
	if start < 0:
		raise SystemExit("missing production function: " + signature)
	brace = text.find("{", start)
	depth = 0
	for end in range(brace, len(text)):
		if text[end] == "{":
			depth += 1
		elif text[end] == "}":
			depth -= 1
			if depth == 0:
				return text[start:end + 1]
	raise SystemExit("unterminated production function: " + signature)


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

# Exercise cache synchronization and the operation ordering from flash.c.
cache_sync = extract(flash_text, "static int\ns31_flash_sync_buffer(")
cache_disable = extract(flash_text, "static int\ns31_flash_cache_disable(")
cache_restore = extract(flash_text, "static void\ns31_flash_cache_restore(")
flash_invalidate = extract(flash_text, "static int\ns31_flash_invalidate(")
validate_buffer = extract(flash_text, "static int\ns31_flash_validate_buffer(")
flash_result = extract(flash_text, "static int\ns31_flash_result(")
operation = extract(flash_text, "static int\ns31_flash_operation(")

cache_preamble = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
typedef unsigned long ulong;
#define SBI_EFAIL (-1)
#define SBI_ENOTSUPP (-2)
#define SBI_ERR_INVALID_PARAM (-3)
#define SBI_ERR_INVALID_ADDRESS (-4)
#define SBI_ERR_NOT_SUPPORTED (-5)
#define SBI_ERR_ALREADY_STARTED (-6)
#define SBI_DOMAIN_READ 1
#define SBI_DOMAIN_WRITE 2
#define PRV_S 1
#define S31_FLASH_CACHE_LINE 64
#define S31_FLASH_BOUNCE_SIZE 4096
#define S31_FLASH_WRITE_ALIGN 4
#define S31_FLASH_MAX_CAPACITY 0x01000000U
#define S31_SBI_FLASH_READ 7
#define S31_SBI_FLASH_WRITE 8
#define S31_SBI_FLASH_ERASE 9
#define S31_SBI_FLASH_SYNC 10
#define S31_CACHE_MAP_L1_DCACHE 0x10U
#define S31_CACHE_MAP_L1_ALL 0x13U
#define PSRAM_START 0x50000000U
#define PSRAM_SIZE 0x04000000U
#define FLASH_START 0x40000000U
#define FLASH_SIZE 0x04000000U
#define USER_ADDR (PSRAM_START + 64U)

struct s31_rom_flash_chip { u32 chip_size, sector_size, page_size; };
static struct s31_rom_flash_chip test_chip = { 0x01000000U, 4096, 256 };
static int s31_flash_lock;
static u32 s31_flash_bounce[S31_FLASH_BOUNCE_SIZE / sizeof(u32)]
    __attribute__((aligned(64)));
static u32 s31_flash_next_generation;
static int park_error, release_error, rom_error, cache_all_error;
static int buffer_invalidate_error, buffer_writeback_error;
static int flash_invalidate_error, lock_held;
static unsigned int park_calls, release_calls, range_calls;
static u32 last_range_start, last_range_length;
static char events[64];
static size_t event_count;
static u8 cached_bytes[128], backing_bytes[128], written_bytes[64];
static const u8 read_pattern[4] = { 0xa1, 0xb2, 0xc3, 0xd4 };
static const u8 fresh_write[4] = { 0x21, 0x32, 0x43, 0x54 };
static const u8 stale_write[4] = { 0x91, 0x82, 0x73, 0x64 };

static void event(char c) { events[event_count++] = c; events[event_count] = 0; }
static void clear_events(void) { event_count = 0; events[0] = 0; }
static int at(char c) { char *p = strchr(events, c); return p ? (int)(p - events) : -1; }
static void before(char a, char b) { assert(at(a) >= 0 && at(b) > at(a)); }

static int cache_all(u32 which) { (void)which; event('a'); return cache_all_error; }
static u32 disable_dcache(void) { event('d'); return 1; }
static u32 disable_icache(void) { event('c'); return 2; }
static void enable_icache(u32 state) { (void)state; event('e'); }
static void enable_dcache(u32 state) { (void)state; event('e'); }
static int cache_invalidate(u32 which, u32 start, u32 length)
{
	(void)which; range_calls++; last_range_start = start; last_range_length = length;
	if (start >= PSRAM_START && start < PSRAM_START + PSRAM_SIZE) {
		event('i');
		if (start == USER_ADDR && length == 64 && !buffer_invalidate_error)
        memcpy(cached_bytes, backing_bytes, 64);
		return buffer_invalidate_error;
	}
	event('f'); return flash_invalidate_error;
}
static int cache_writeback(u32 which, u32 start, u32 length)
{
	(void)which; range_calls++; last_range_start = start; last_range_length = length; event('o');
    if (start == USER_ADDR && length == 64 && !buffer_writeback_error)
        memcpy(backing_bytes, cached_bytes, 64);
    return buffer_writeback_error;
}
static int rom_read(u32 address, u32 *buffer, int32_t length)
{
	(void)address; event('q');
    if (rom_error) return rom_error;
    memcpy((void *)buffer, read_pattern, (size_t)length);
    return 0;
}
static int rom_write(u32 address, const u32 *buffer, int32_t length)
{
    (void)address; event('w');
    if (rom_error) return rom_error;
    memcpy(written_bytes, (const void *)buffer, (size_t)length);
    return 0;
}
static int rom_erase(u32 address, u32 length) { (void)address; (void)length; return rom_error; }
static int rom_wait(void *chip) { (void)chip; return rom_error; }
#define S31_ROM_CACHE_WRITEBACK_ALL cache_all
#define S31_ROM_CACHE_INVALIDATE_RANGE cache_invalidate
#define S31_ROM_CACHE_WRITEBACK_RANGE cache_writeback
#define S31_ROM_CACHE_DISABLE_DCACHE disable_dcache
#define S31_ROM_CACHE_DISABLE_ICACHE0 disable_icache
#define S31_ROM_CACHE_DISABLE_ICACHE1 disable_icache
#define S31_ROM_CACHE_ENABLE_DCACHE enable_dcache
#define S31_ROM_CACHE_ENABLE_ICACHE0 enable_icache
#define S31_ROM_CACHE_ENABLE_ICACHE1 enable_icache
#define S31_ROM_FLASH_READ rom_read
#define S31_ROM_FLASH_WRITE rom_write
#define S31_ROM_FLASH_ERASE_AREA rom_erase
#define S31_ROM_FLASH_WAIT_IDLE rom_wait
#define S31_FLASH_DIAG_MARK(c) ((void)0)
#define s31_flash_diag_begin() ((void)0)

static int current_hartid(void) { return 0; }
static bool spin_trylock(void *lock) { (void)lock; if (lock_held) return false; lock_held = 1; return true; }
static void spin_unlock(void *lock) { (void)lock; lock_held = 0; }
static int s31_flash_get_chip(struct s31_rom_flash_chip **chip)
{ *chip = &test_chip; return 0; }
static int s31_flash_park_harts(u32 generation, ulong *expected)
{ (void)generation; park_calls++; event('p'); *expected = 1; return park_error; }
static int s31_flash_release_harts(u32 generation, ulong expected)
{ (void)generation; (void)expected; release_calls++; event('l'); return release_error; }
static void *sbi_domain_thishart_ptr(void) { return NULL; }
static bool sbi_domain_check_addr_range(void *domain, u32 address, u32 length,
    int privilege, unsigned long access)
{ (void)domain; (void)address; (void)length; (void)privilege; (void)access; return true; }
static void *sbi_memcpy(void *dst, const void *src, size_t length)
{
    uintptr_t d = (uintptr_t)dst, s = (uintptr_t)src;
    if (d >= USER_ADDR && d < USER_ADDR + sizeof(cached_bytes))
        dst = cached_bytes + (d - USER_ADDR);
    if (s >= USER_ADDR && s < USER_ADDR + sizeof(cached_bytes))
        src = cached_bytes + (s - USER_ADDR);
    event('m');
    return memcpy(dst, src, length);
}
static bool s31_flash_range_valid(u32 address, u32 length, u32 capacity,
    u32 alignment, u32 maximum);
"""

cache_harness_tail = r"""
static void caller_postread_invalidate(void)
{ memcpy(cached_bytes, backing_bytes, 4); }
static void reset_state(void)
{
    memset(cached_bytes, 0, sizeof(cached_bytes));
    memset(backing_bytes, 0, sizeof(backing_bytes));
    memset(written_bytes, 0, sizeof(written_bytes));
    clear_events(); park_error = release_error = rom_error = cache_all_error = 0;
    buffer_invalidate_error = buffer_writeback_error = flash_invalidate_error = 0;
    park_calls = release_calls = range_calls = 0;
}
static void test_helper_bounds_and_errors(void)
{
    unsigned int before_calls;
    reset_state();
    assert(s31_flash_sync_buffer(PSRAM_START, 4, false) == 0);
	assert(at('i') >= 0 && last_range_start == PSRAM_START && last_range_length == 64);
    assert(s31_flash_sync_buffer(PSRAM_START + PSRAM_SIZE - 4, 4, true) == 0);
	assert(at('o') >= 0 && last_range_start == PSRAM_START + PSRAM_SIZE - 64 && last_range_length == 64);
    before_calls = range_calls;
	assert(s31_flash_sync_buffer(0xffffffffU, 0, true) == 0);
    assert(s31_flash_sync_buffer(PSRAM_START + PSRAM_SIZE - 4, 8, true) == SBI_ERR_INVALID_ADDRESS);
    assert(s31_flash_sync_buffer(0xfffffff0U, 64, false) == SBI_ERR_INVALID_ADDRESS);
    assert(range_calls == before_calls);
    buffer_invalidate_error = 1;
    assert(s31_flash_sync_buffer(USER_ADDR, 4, false) == SBI_EFAIL);
    buffer_invalidate_error = 0; buffer_writeback_error = 1;
    assert(s31_flash_sync_buffer(USER_ADDR, 4, true) == SBI_EFAIL);
}
static void test_current_read_and_write(void)
{
    reset_state();
    assert(s31_flash_operation(S31_SBI_FLASH_READ, 0, USER_ADDR, 4) == 0);
    before('p', 'a'); before('q', 'm'); before('m', 'o'); before('o', 'l');
    caller_postread_invalidate();
    assert(memcmp(cached_bytes, read_pattern, 4) == 0);
    reset_state();
	memcpy(backing_bytes, stale_write, 4);
	memcpy(cached_bytes, stale_write, 4);
	assert(s31_flash_operation(S31_SBI_FLASH_WRITE, 0, USER_ADDR, 4) == 0);
	assert(memcmp(written_bytes, stale_write, 4) == 0);
	memcpy(backing_bytes, fresh_write, 4);
	clear_events();
    assert(s31_flash_operation(S31_SBI_FLASH_WRITE, 0, USER_ADDR, 4) == 0);
    before('p', 'i'); before('i', 'm'); before('m', 'a'); before('a', 'w'); before('w', 'l');
    assert(memcmp(written_bytes, fresh_write, 4) == 0);
}
static void test_errors_release_harts(void)
{
    reset_state(); rom_error = -77;
    assert(s31_flash_operation(S31_SBI_FLASH_READ, 0, USER_ADDR, 4) == SBI_EFAIL);
	assert(park_calls == 1 && release_calls == 1);
    reset_state(); buffer_invalidate_error = 1;
    assert(s31_flash_operation(S31_SBI_FLASH_WRITE, 0, USER_ADDR, 4) == SBI_EFAIL);
    assert(release_calls == 1);
    assert(at('p') >= 0 && at('l') > at('p'));
	reset_state(); buffer_writeback_error = 1;
	assert(s31_flash_operation(S31_SBI_FLASH_READ, 0, USER_ADDR, 4) == SBI_EFAIL);
	assert(release_calls == 1 && at('o') > at('e'));
	reset_state(); flash_invalidate_error = 1;
	assert(s31_flash_operation(S31_SBI_FLASH_WRITE, 0, USER_ADDR, 4) == SBI_EFAIL);
	assert(release_calls == 1);
    reset_state(); release_error = -88;
	assert(s31_flash_operation(S31_SBI_FLASH_READ, 0, USER_ADDR, 4) == -88);
    assert(release_calls == 1);
	reset_state(); rom_error = -77; release_error = -88;
	assert(s31_flash_operation(S31_SBI_FLASH_READ, 0, USER_ADDR, 4) == SBI_EFAIL);
	assert(release_calls == 1);
}
int main(void)
{
    test_helper_bounds_and_errors();
    test_current_read_and_write();
    test_errors_release_harts();
    return 0;
}
"""

range_function = extract(text, "bool s31_flash_range_valid(")
cache_components = "\n\n".join((cache_disable, cache_restore, flash_invalidate,
	validate_buffer, flash_result))
if not os.environ.get("CC"):
	raise SystemExit("set CC to the selected native Clang compiler")
cc = os.environ["CC"]
sanitizer_flags = ["-std=gnu11", "-Wall", "-Wextra", "-Werror",
	"-fsanitize=address,undefined", "-fno-sanitize-recover=all"]
actual_harness = (cache_preamble + range_function + "\n" + cache_sync +
	"\n" + cache_components + "\n" + operation + cache_harness_tail)

with tempfile.TemporaryDirectory(prefix="opensbi-s31-cache-") as tmp:
	path = pathlib.Path(tmp) / "cache-check.c"
	binary = pathlib.Path(tmp) / "cache-check"
	path.write_text(actual_harness)
	subprocess.run([cc, *sanitizer_flags, str(path), "-o", str(binary)], check=True)
	subprocess.run([str(binary)], check=True)
	cppcheck = os.environ.get("CPPCHECK")
	if cppcheck:
		subprocess.run([cppcheck, "--enable=warning,performance,portability",
			"--error-exitcode=1", "--std=c11", str(path)], check=True)
	analyzer = os.environ.get("CLANG_ANALYZER")
	if analyzer:
		subprocess.run([analyzer, "--analyze", "-std=gnu11", "-o", os.devnull,
			str(path)], check=True)

print("S31 flash buffer synchronization and operation ordering passed")
