// SPDX-License-Identifier: MIT
#include MLAS_GUARD_HEADER

#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

static bool fail_mapping;
static int mapping_calls;
static int protection_calls;
static int release_calls;
static int allocation_protection;

extern "C" void* __real_mmap(void*, size_t, int, int, int, off_t);
extern "C" int __real_mprotect(void*, size_t, int);
extern "C" int __real_munmap(void*, size_t);

extern "C" void* __wrap_mmap(void* address, size_t length, int protection,
                              int flags, int descriptor, off_t offset) {
  ++mapping_calls;
  allocation_protection = protection;
  if (fail_mapping) {
    errno = ENOMEM;
    std::puts("Injected mmap failure: MAP_FAILED, ENOMEM");
    return MAP_FAILED;
  }
  void* result = __real_mmap(address, length, protection, flags, descriptor, offset);
  std::printf("mmap: protection=%#x result=%s errno=%d\n", protection,
              result == MAP_FAILED ? "MAP_FAILED" : "mapped", result == MAP_FAILED ? errno : 0);
  return result;
}

extern "C" int __wrap_mprotect(void* address, size_t length, int protection) {
  ++protection_calls;
  const int result = __real_mprotect(address, length, protection);
  const int error = result == 0 ? 0 : errno;
  std::printf("mprotect: protection=%#x result=%d errno=%d (%s)\n", protection,
              result, error, std::strerror(error));
  errno = error;
  return result;
}

extern "C" int __wrap_munmap(void* address, size_t length) {
  ++release_calls;
  return __real_munmap(address, length);
}

extern "C" [[noreturn]] void __wrap_abort() noexcept {
  if (fail_mapping && mapping_calls == 1 && protection_calls == 0) {
    std::puts("PASS mapping failure stopped before mprotect");
    std::exit(0);
  }
  if (fail_mapping && protection_calls != 0) {
    std::puts("FAIL mapping failure reached mprotect");
    std::exit(3);
  }
  std::puts("FAIL real guard mapping aborted");
  std::exit(4);
}

int main(int argc, char** argv) {
  if (argc != 2 || (std::strcmp(argv[1], "--real") != 0 &&
                    std::strcmp(argv[1], "--fail-map") != 0 &&
                    std::strcmp(argv[1], "--guard") != 0)) {
    return 2;
  }
  fail_mapping = std::strcmp(argv[1], "--fail-map") == 0;
  {
    MatrixGuardBuffer<uint32_t> buffer;
    uint32_t* values = buffer.GetBuffer(4);
    if (fail_mapping || mapping_calls != 1 || protection_calls != 1 || values[0] != 32) {
      return 5;
    }
#if defined(__NetBSD__)
    if ((PROT_MPROTECT_EXTRACT(allocation_protection) & (PROT_READ | PROT_WRITE)) !=
        (PROT_READ | PROT_WRITE)) {
      std::puts("FAIL mapping did not declare its later RW permissions");
      return 6;
    }
#endif
    if (std::strcmp(argv[1], "--guard") == 0) {
      std::fflush(nullptr);
      const pid_t child = fork();
      if (child < 0) return 7;
      if (child == 0) {
        const struct rlimit no_core{0, 0};
        if (setrlimit(RLIMIT_CORE, &no_core) != 0) _exit(8);
        const volatile uint32_t value = values[4];
        (void)value;
        _exit(9);
      }
      int status = 0;
      if (waitpid(child, &status, 0) != child || !WIFSIGNALED(status) || WTERMSIG(status) != SIGSEGV) {
        return 10;
      }
      std::puts("PASS upper guard remains inaccessible (child SIGSEGV)");
    }
  }
  if (release_calls != 1) return 11;
  std::puts("PASS real mapping: writable data, released reservation");
  return 0;
}
