// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD, AI-assisted Linux public API consumer. No modeled UMD or device.
#include <dirent.h>
#include <sys/stat.h>
#include <sys/auxv.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <link.h>
#include <unistd.h>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <standard_api.h>

#if !defined(__linux__) || !defined(__aarch64__)
#error "This no-device execution probe requires Linux/AArch64"
#endif

static unsigned checks;
static void
check(bool ok, const char *what)
{
    if (!ok) {
        std::fprintf(stderr, "FAIL: %s\n", what);
        std::exit(1);
    }
    ++checks;
}

static std::string
canonical(const char *path)
{
    char *p = realpath(path, nullptr);
    if (!p)
        return {};
    std::string result(p);
    std::free(p);
    return result;
}

static void
no_device()
{
    struct stat sb;
    errno = 0;
    check(lstat("/dev/aipu", &sb) == -1 && errno == ENOENT,
        "requires /dev/aipu absent, including symlinks");
}

static unsigned
fd_count()
{
    DIR *directory = opendir("/proc/self/fd");
    check(directory != nullptr, "open actual descriptor inventory");
    unsigned count = 0;
    errno = 0;
    while (auto *entry = readdir(directory)) {
        if (entry->d_name[0] != '.')
            ++count;
    }
    const int saved_errno = errno;
    check(closedir(directory) == 0 && saved_errno == 0, "descriptor inventory complete");
    return count;
}

struct providers {
    std::string library, executable;
    unsigned umd = 0, cxx = 0, gcc = 0;
};

static int
loaded(struct dl_phdr_info *info, size_t, void *opaque)
{
    auto *p = static_cast<providers *>(opaque);
    if (!info->dlpi_name || !*info->dlpi_name)
        return 0;
    if (getauxval(AT_SYSINFO_EHDR) != 0 &&
        info->dlpi_addr == getauxval(AT_SYSINFO_EHDR))
        return 0;
    auto path = canonical(info->dlpi_name);
    if (path.empty()) {
        std::fprintf(stderr, "FAIL: unresolved loaded provider: %s\n", info->dlpi_name);
        return 1;
    }
    if (path == p->executable)
        return 0;
    std::printf("LOADED: %s\n", path.c_str());
    if (path == p->library)
        ++p->umd;
    else if (path.find("libstdc++.so.") != std::string::npos)
        ++p->cxx;
    // glibc backtrace may load the system unwinder on its first error report.
    else if (path.find("libgcc_s.so.") != std::string::npos &&
        (path.find("/usr/lib/") == 0 || path.find("/lib/") == 0 ||
        path.find("/usr/local/lib64/") == 0))
        ++p->gcc;
    else if (path.find("/usr/lib/") != 0 && path.find("/lib/") != 0 &&
        path.find("/usr/libexec/valgrind/") != 0) {
        std::fprintf(stderr, "FAIL: foreign loaded provider: %s\n", path.c_str());
        return 1;
    }
    return 0;
}

template<typename Function>
static Function
symbol(void *handle, const char *name, const std::string &expected)
{
    dlerror();
    void *address = dlsym(handle, name);
    check(address != nullptr && dlerror() == nullptr, name);
    Dl_info info{};
    check(dladdr(address, &info) != 0 && info.dli_fname != nullptr &&
        canonical(info.dli_fname) == expected, "public symbol belongs to exact full UMD");
    return reinterpret_cast<Function>(address);
}

int
main(int argc, char **argv)
{
    check((argc == 2 || argc == 3) && argv[1][0] == '/', "absolute private UMD path required");
    const auto library = canonical(argv[1]);
    check(!library.empty() && library == argv[1], "canonical exact UMD path");
    const auto executable = canonical(argv[0]);
    check(!executable.empty(), "absolute executable path");
    if (argc == 3)
        check(dlopen(argv[2], RTLD_NOW | RTLD_LOCAL) != nullptr,
            "load the foreign-library causal control");
    no_device();
    const unsigned before = fd_count();
    for (unsigned cycle = 0; cycle < 4; ++cycle) {
        no_device();
        void *handle = dlopen(library.c_str(), RTLD_NOW | RTLD_LOCAL);
        if (!handle)
            std::fprintf(stderr, "dlopen: %s\n", dlerror());
        check(handle != nullptr, "load complete DSO with immediate binding");
        auto init = symbol<decltype(&aipu_init_context)>(handle, "aipu_init_context", library);
        auto deinit = symbol<decltype(&aipu_deinit_context)>(handle, "aipu_deinit_context", library);
        auto error = symbol<decltype(&aipu_get_error_message)>(handle, "aipu_get_error_message", library);
        check(init(nullptr) == AIPU_STATUS_ERROR_NULL_PTR, "null init output rejected");
        aipu_ctx_handle_t *ctx = reinterpret_cast<aipu_ctx_handle_t *>(1);
        no_device();
        check(init(&ctx) == AIPU_STATUS_ERROR_OPEN_DEV_FAIL, "real device open failure propagated");
        check(ctx == nullptr, "failed context output cleared");
        check(deinit(ctx) == AIPU_STATUS_ERROR_NULL_PTR, "no context to destroy after failure");
        aipu_ctx_handle_t invalid{};
        check(deinit(&invalid) == AIPU_STATUS_ERROR_INVALID_CTX, "unknown context rejected");
        const char *message = nullptr;
        check(error(nullptr, AIPU_STATUS_ERROR_OPEN_DEV_FAIL, &message) ==
            AIPU_STATUS_ERROR_OPEN_DEV_FAIL && message && *message,
            "real static open-failure message");
        std::printf("OPEN_ERROR: %s\n", message);
        check(error(nullptr, AIPU_STATUS_ERROR_OPEN_DEV_FAIL, nullptr) ==
            AIPU_STATUS_ERROR_NULL_PTR, "null error-message output rejected");
        providers state{library, executable};
        const int inventory = dl_iterate_phdr(loaded, &state);
        // Never exit in the loader callback: release the caller's handle first.
        const int closed = dlclose(handle);
        check(inventory == 0 && state.umd == 1 && state.cxx == 0 && state.gcc <= 1,
            "one exact UMD, no shared libstdc++; at most one system backtrace unwinder");
        check(closed == 0, "dlclose");
        check(fd_count() == before, "no descriptor leak across public failure lifecycle");
        std::printf("PASS: no-device public lifecycle cycle %u\n", cycle + 1);
    }
    std::printf("PASS: full UMD no-device API, %u checks; no device/model execution\n", checks);
    return 0;
}
