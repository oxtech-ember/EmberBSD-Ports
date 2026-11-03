/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). */
#include <stdlib.h>
#include <string.h>
static int fail_dup;
static char *test_strdup(const char *s) { if (fail_dup) return NULL; size_t n = strlen(s) + 1; char *p = malloc(n); if (p) memcpy(p, s, n); return p; }
#define strdup test_strdup
#include PROFILE_SOURCE
#include <assert.h>
int main(void) {
  assert(parseFilenamePattern("/tmp/alpha", 1) == 0);
  assert(lprofCurFilename.OwnedFilenamePat &&
         lprofCurFilename.FilenamePat == lprofCurFilename.OwnedFilenamePat);
  lprofCurFilename.ProfilePathPrefix = test_strdup("/tmp/");
  char *old = lprofCurFilename.OwnedFilenamePat;
  fail_dup = 1;
  assert(parseFilenamePattern("new", 1) == -1);
  assert(lprofCurFilename.OwnedFilenamePat == old && lprofCurFilename.ProfilePathPrefix);
  fail_dup = 0;
  assert(parseFilenamePattern("borrowed", 0) == 0);
  free(old);
  assert(!lprofCurFilename.OwnedFilenamePat);
  resetFilenameToDefault();
  assert(setenv("TMPDIR", "xy", 1) == 0);
  assert(parseFilenamePattern("%t%t/end", 1) == 0);
  int computed = getCurFilenameLength();
  char *expanded = malloc((size_t)computed + 1);
  assert(computed >= 0 && expanded);
  assert(getCurFilename(expanded, 1) == expanded);
  assert(strcmp(expanded, "xy/xy//end") == 0);
  assert(strlen(expanded) <= (size_t)computed);
  free(expanded);
  resetFilenameToDefault();
  assert(parseFilenamePattern("%", 1) == 0);
  char trailing[64];
  assert(strcmp(getCurFilename(trailing, 1), "%") == 0);
  resetFilenameToDefault();
  assert(parseFilenamePattern("%p%", 1) == 0);
  computed = getCurFilenameLength();
  expanded = malloc((size_t)computed + 1);
  assert(expanded && getCurFilename(expanded, 1) == expanded);
  char pid[32];
  assert(snprintf(pid, sizeof(pid), "%ld", (long)getpid()) > 0);
  assert(strcmp(expanded, pid) == 0);
  free(expanded);
  resetFilenameToDefault();
  assert(setenv("LLVM_PROFILE_VERBOSE", "1", 1) == 0);
  assert(setenv(LPROF_INIT_ONCE_ENV, "1", 1) == 0);
  parseAndSetFilename("/tmp/first", PNS_runtime_api, 1);
  parseAndSetFilename("/tmp/second", PNS_runtime_api, 1);
  assert(strcmp(lprofCurFilename.FilenamePat, "/tmp/second") == 0);
  assert(strcmp(__llvm_profile_get_path_prefix(), "/tmp/") == 0);
  fail_dup = 1;
  parseAndSetFilename("/tmp/third", PNS_runtime_api, 1);
  fail_dup = 0;
  assert(strcmp(lprofCurFilename.FilenamePat, "default.profraw") == 0);
  resetFilenameToDefault();
  size_t x = 2;
  assert(addFilenameParts(&x, 1, 2, 1) == 0 && x == 1);
  x = (size_t)INT_MAX - 1;
  assert(addFilenameParts(&x, 2, 0, 2) == -1);
  x = 1; assert(addFilenameParts(&x, 1, 2, 0) == -1);
  uint64_t len = 20;
  uint8_t data[21] = {0};
  ProfDataIOVec v[2] = {{&len, sizeof(len), 1, 0}, {data, 1, 20, 0}};
  lprofBinaryIdsBuffer buf = {{0}, 0};
  ProfDataWriter w = {binaryIdsStringWriter, &buf};
  assert(binaryIdsStringWriter(&w, v, 2) == 0 && buf.Length == 40);
  v[0].NumElm = 0;
  assert(binaryIdsStringWriter(&w, v, 2) == UINT32_MAX);
  v[0].NumElm = 2;
  assert(binaryIdsStringWriter(&w, v, 2) == UINT32_MAX);
  v[0].NumElm = 1; len = 0; v[1].NumElm = 0; v[1].Data = NULL;
  buf.Length = 0;
  assert(binaryIdsStringWriter(&w, v, 2) == 0 && buf.Length == 0);
  len = 21; v[1].NumElm = 21; v[1].Data = data; buf.Length = 0;
  assert(binaryIdsStringWriter(&w, v, 2) == UINT32_MAX && buf.Length == 0);
  return 0;
}
