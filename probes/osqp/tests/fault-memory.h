/* SPDX-License-Identifier: MIT */
/* Origin: EmberBSD (AI-assisted), isolated upstream allocator-hook regression. */
#ifndef EMBER_OSQP_FAULT_MEMORY_H
#define EMBER_OSQP_FAULT_MEMORY_H
#include <stddef.h>
#define c_malloc fault_malloc
#define c_calloc fault_calloc
#define c_realloc fault_realloc
#define c_free fault_free
void *fault_malloc(size_t);
void *fault_calloc(size_t, size_t);
void *fault_realloc(void *, size_t);
void fault_free(void *);
#endif
