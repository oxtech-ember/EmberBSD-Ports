/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). */
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "InstrProfiling.h"
int __llvm_profile_runtime = 0;
int __llvm_profile_check_compatibility(const char *, uint64_t);
int __llvm_profile_merge_from_buffer(const char *, uint64_t);
__attribute__((noinline)) static int decision(int a, int b) { return a && b; }
__attribute__((no_profile_instrument_function)) int main(void) {
  uint64_t sz = __llvm_profile_get_size_for_buffer();
  size_t pagesize = (size_t)sysconf(_SC_PAGESIZE);
  size_t alloc = ((size_t)sz + pagesize - 1) / pagesize * pagesize;
  char *src = mmap(NULL, alloc, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANON, -1, 0);
  assert(src != MAP_FAILED && sz > sizeof(__llvm_profile_header));
  __llvm_profile_reset_counters();
  assert(decision(1, 0) == 0);
  const uint64_t *cb = (const uint64_t *)__llvm_profile_begin_counters();
  const uint64_t *ce = (const uint64_t *)__llvm_profile_end_counters();
  size_t nc = (size_t)(ce-cb); assert(nc && nc < 64);
  uint64_t original[64], prior[64]; memcpy(original, cb, nc * sizeof(*cb));
  const unsigned char *bb = (const unsigned char *)__llvm_profile_begin_bitmap();
  const unsigned char *be = (const unsigned char *)__llvm_profile_end_bitmap();
  size_t nb = (size_t)(be-bb); assert(nb && nb < 64);
  unsigned char bits[64], oldbits[64]; memcpy(bits, bb, nb);
  assert(__llvm_profile_write_buffer(src) == 0);
  assert(__llvm_profile_check_compatibility(src, sz) == 0);
  for (size_t n = 0; n < sizeof(__llvm_profile_header); n++) {
    char *small = malloc(n ? n : 1); assert(small); memcpy(small, src, n);
    assert(__llvm_profile_check_compatibility(small, n) != 0); free(small);
  }
  assert(mprotect(src, alloc, PROT_READ) == 0);
  __llvm_profile_reset_counters();
  assert(decision(1, 1) == 1);
  memcpy(prior, cb, nc * sizeof(*cb)); memcpy(oldbits, bb, nb);
  assert(__llvm_profile_merge_from_buffer(src, sz) == 0);
  for (size_t i=0;i<nc;i++) assert(cb[i] == prior[i] + original[i]);
  for (size_t i=0;i<nb;i++) assert(bb[i] == (unsigned char)(oldbits[i] | bits[i]));
  assert(munmap(src, alloc) == 0);
  return 0;
}
