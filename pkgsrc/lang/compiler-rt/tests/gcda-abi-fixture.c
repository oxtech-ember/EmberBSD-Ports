/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 The EmberBSD Project contributors. */
/* Developed with AI assistance. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static unsigned writes, resets;
static void write_callback(void) { writes++; }
static void reset_callback(void) { resets++; }
void llvm_gcda_emit_arcs(uint32_t, uint64_t *);
void llvm_gcda_summary_info(void);
void llvm_gcda_end_file(void);
void llvm_gcov_init(void (*)(void), void (*)(void));
void llvm_writeout_files(void);
#ifdef TEST_CURRENT_GCOV_ABI
void llvm_gcda_start_file(const char *, uint32_t, uint32_t);
void llvm_gcda_emit_function(uint32_t, uint32_t, uint32_t);
void llvm_reset_counters(void);
void llvm_delete_reset_function_list(void);
void llvm_register_reset_function(void (*)(void));
#else
void llvm_gcda_start_file(const char *, const char[4], uint32_t);
void llvm_gcda_emit_function(uint32_t, const char *, uint32_t, uint8_t, uint32_t);
void llvm_gcda_increment_indirect_counter(uint32_t *, uint64_t **);
void llvm_register_flush_function(void (*)(void));
void llvm_delete_writeout_function_list(void);
void llvm_delete_flush_function_list(void);
void __gcov_flush(void);
#endif

int
main(int argc, char **argv)
{
	unsigned pass;

	assert(argc == 2);
	llvm_gcov_init(write_callback, reset_callback);
	llvm_writeout_files();
#ifdef TEST_CURRENT_GCOV_ABI
	llvm_reset_counters();
	llvm_delete_reset_function_list();
	llvm_reset_counters();
	llvm_register_reset_function(reset_callback);
	llvm_reset_counters();
	llvm_delete_reset_function_list();
#else
	__gcov_flush();
	llvm_delete_flush_function_list();
	__gcov_flush();
	llvm_register_flush_function(reset_callback);
	__gcov_flush();
	llvm_delete_flush_function_list();
	llvm_delete_writeout_function_list();
	llvm_writeout_files();
	{
		uint32_t predecessor = UINT32_MAX;
		uint64_t value = 41;
		uint64_t *counters[] = { &value, NULL };
		llvm_gcda_increment_indirect_counter(&predecessor, counters);
		assert(value == 41);
		predecessor = 1;
		llvm_gcda_increment_indirect_counter(&predecessor, counters);
		assert(value == 41);
		predecessor = 0;
		llvm_gcda_increment_indirect_counter(&predecessor, counters);
		assert(value == 42);
	}
#endif
	assert(writes == 1 && resets == 2);
	for (pass = 0; pass != 2; pass++) {
		uint64_t counters[] = { 7, UINT64_C(0x1122334455667788) };
#ifdef TEST_CURRENT_GCOV_ABI
		llvm_gcda_start_file(argv[1], UINT32_C(0x3430382a), 0x12345678);
		llvm_gcda_emit_function(42, 0x11223344, 0x55667788);
#else
		llvm_gcda_start_file(argv[1], "*804", 0x12345678);
		llvm_gcda_emit_function(42, "fixture_name", 0x11223344, 1, 0x55667788);
#endif
		llvm_gcda_emit_arcs(2, counters);
		assert(counters[0] == 7 * (pass + 1));
		assert(counters[1] == UINT64_C(0x1122334455667788) * (pass + 1));
#ifdef TEST_CURRENT_GCOV_ABI
		llvm_gcda_emit_function(43, 7, 9);
#else
		llvm_gcda_emit_function(43, NULL, 7, 0, 9);
#endif
		{
			uint64_t counter = 3;
			llvm_gcda_emit_arcs(1, &counter);
			assert(counter == 3 * (pass + 1));
		}
		llvm_gcda_summary_info();
		llvm_gcda_end_file();
	}
	puts("PASS: callbacks, legacy counter boundaries, file creation and merge");
	return 0;
}
