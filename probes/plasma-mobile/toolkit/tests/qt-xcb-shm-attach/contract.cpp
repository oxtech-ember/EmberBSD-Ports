// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD; AI-assisted behavioral contract for Qt's XCB SysV SHM helper.
#include <cerrno>
#include <cstdarg>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#define CHECK(condition) do { \
    if (!(condition)) { \
        std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition); \
        ++failures; \
    } \
} while (false)

using quint8 = std::uint8_t;
using size_t = std::size_t;
static constexpr int IPC_PRIVATE = 0x4311;
static constexpr int IPC_CREAT = 0x0200;
static constexpr int IPC_RMID = 0x0800;

struct xcb_connection_t {};
struct xcb_shm_segment_info_t {
    std::uint32_t shmseg = 0;
    int shmid = 0;
    quint8 *shmaddr = nullptr;
};
struct xcb_void_cookie_t {
    std::uint32_t sequence = 0;
    std::uint32_t shmseg = 0;
    int shmid = 0;
};
struct xcb_generic_error_t { std::uint8_t error_code = 0; };

class QXcbBackingStoreImage {
public:
    static bool createSystemVShmSegment(xcb_connection_t *connection,
                                        size_t segmentSize = 1,
                                        xcb_shm_segment_info_t *shmInfo = nullptr);
};

struct Segment {
    void *memory = nullptr;
    size_t bytes = 0;
    unsigned clientAttachments = 0;
    unsigned serverAttachments = 0;
    bool removed = false;
    bool alive = true;
};

static int failures;
static int nextShmId = 100;
static std::uint32_t nextXcbId = 500;
static std::uint32_t nextSequence = 1;
static bool failShmGet;
static bool failShmAt;
static bool failXcbAttach;
static bool clobberErrnoOnRemove;
static unsigned allocatedErrors;
static unsigned freedErrors;
static unsigned freedSegments;
static unsigned rejectedRemovedSegments;
static std::map<int, Segment> segments;
static std::unordered_map<void *, int> localAddresses;
static std::unordered_map<std::uint32_t, int> serverSegments;
static std::set<void *> xcbErrors;
static std::vector<std::string> warnings;

static void maybeFree(int id)
{
    auto found = segments.find(id);
    if (found == segments.end())
        return;
    Segment &segment = found->second;
    if (segment.alive && segment.removed && segment.clientAttachments == 0
            && segment.serverAttachments == 0) {
        std::free(segment.memory);
        segment.memory = nullptr;
        segment.alive = false;
        ++freedSegments;
    }
}

static unsigned liveSegments()
{
    unsigned result = 0;
    for (const auto &entry : segments)
        result += entry.second.alive;
    return result;
}

static int shmget(int key, size_t bytes, int flags)
{
    CHECK(key == IPC_PRIVATE);
    CHECK(flags == (IPC_CREAT | 0600));
    if (failShmGet) {
        errno = ENOSPC;
        return -1;
    }
    const int id = nextShmId++;
    void *memory = std::malloc(bytes);
    CHECK(memory != nullptr);
    segments.emplace(id, Segment{memory, bytes});
    return id;
}

static void *shmat(int id, const void *address, int flags)
{
    CHECK(address == nullptr);
    CHECK(flags == 0);
    Segment &segment = segments.at(id);
    if (failShmAt) {
        errno = ENOMEM;
        return reinterpret_cast<void *>(static_cast<std::intptr_t>(-1));
    }
    CHECK(segment.alive);
    ++segment.clientAttachments;
    localAddresses.emplace(segment.memory, id);
    return segment.memory;
}

static int shmctl(int id, int command, void *buffer)
{
    CHECK(command == IPC_RMID);
    CHECK(buffer == nullptr);
    Segment &segment = segments.at(id);
    segment.removed = true;
    maybeFree(id);
    if (clobberErrnoOnRemove)
        errno = EIO;
    return 0;
}

static int shmdt(const void *address)
{
    auto found = localAddresses.find(const_cast<void *>(address));
    CHECK(found != localAddresses.end());
    if (found == localAddresses.end())
        return -1;
    const int id = found->second;
    localAddresses.erase(found);
    Segment &segment = segments.at(id);
    CHECK(segment.clientAttachments > 0);
    --segment.clientAttachments;
    maybeFree(id);
    return 0;
}

static std::uint32_t xcb_generate_id(xcb_connection_t *)
{
    return nextXcbId++;
}

static xcb_void_cookie_t xcb_shm_attach_checked(xcb_connection_t *, std::uint32_t shmseg,
                                                std::uint32_t shmid, bool readOnly)
{
    CHECK(!readOnly);
    return {nextSequence++, shmseg, static_cast<int>(shmid)};
}

// Model NetBSD's observed rule: the server cannot attach an IPC_RMID segment.
static xcb_generic_error_t *xcb_request_check(xcb_connection_t *, xcb_void_cookie_t cookie)
{
    Segment &segment = segments.at(cookie.shmid);
    if (failXcbAttach || segment.removed) {
        rejectedRemovedSegments += segment.removed;
        auto *error = static_cast<xcb_generic_error_t *>(std::malloc(sizeof(xcb_generic_error_t)));
        CHECK(error != nullptr);
        if (!error)
            return nullptr;
        error->error_code = 10;
        xcbErrors.insert(error);
        ++allocatedErrors;
        return error;
    }
    ++segment.serverAttachments;
    serverSegments.emplace(cookie.shmseg, cookie.shmid);
    return nullptr;
}

static void xcb_shm_detach(xcb_connection_t *, std::uint32_t shmseg)
{
    auto found = serverSegments.find(shmseg);
    CHECK(found != serverSegments.end());
    if (found == serverSegments.end())
        return;
    const int id = found->second;
    serverSegments.erase(found);
    Segment &segment = segments.at(id);
    CHECK(segment.serverAttachments > 0);
    --segment.serverAttachments;
    maybeFree(id);
}

static void trackedFree(void *pointer)
{
    if (xcbErrors.erase(pointer))
        ++freedErrors;
    std::free(pointer);
}

static void recordWarning(const char *format, ...)
{
    char buffer[512];
    std::va_list args;
    va_start(args, format);
    std::vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);
    warnings.emplace_back(buffer);
}

#define qCWarning(category, ...) recordWarning(__VA_ARGS__)
#define free trackedFree
// __QT_XCB_SHM_HELPER__
#undef free
#undef qCWarning

static void resetCase()
{
    failures = 0;
    CHECK(liveSegments() == 0);
    segments.clear();
    localAddresses.clear();
    serverSegments.clear();
    xcbErrors.clear();
    warnings.clear();
    failShmGet = false;
    failShmAt = false;
    failXcbAttach = false;
    clobberErrnoOnRemove = false;
    allocatedErrors = 0;
    freedErrors = 0;
    freedSegments = 0;
    rejectedRemovedSegments = 0;
}

static bool finishCase(const char *name)
{
    CHECK(liveSegments() == 0);
    CHECK(localAddresses.empty());
    CHECK(serverSegments.empty());
    CHECK(xcbErrors.empty());
    CHECK(allocatedErrors == freedErrors);
    if (failures == 0) {
        std::printf("PASS %s\n", name);
        return true;
    }
    std::fprintf(stderr, "FAIL %s: %d assertion(s)\n", name, failures);
    return false;
}

static bool successWithRetainedInfo()
{
    resetCase();
    xcb_connection_t connection;
    xcb_shm_segment_info_t info;
    const bool created = QXcbBackingStoreImage::createSystemVShmSegment(&connection, 4096, &info);
    CHECK(created);
    if (!created && rejectedRemovedSegments > 0)
        std::fprintf(stderr, "MODEL: XCB rejected an IPC_RMID segment before attach\n");
    CHECK(info.shmid >= 100);
    CHECK(info.shmaddr != nullptr);
    if (info.shmid >= 100) {
        const Segment &segment = segments.at(info.shmid);
        CHECK(segment.removed);
        CHECK(segment.clientAttachments == 1);
        CHECK(segment.serverAttachments == 1);
        xcb_shm_detach(&connection, info.shmseg);
        CHECK(liveSegments() == 1);
        CHECK(shmdt(info.shmaddr) == 0);
    }
    CHECK(freedSegments == 1);
    return finishCase("success-retained-info");
}

static bool successWithoutRetainedInfo()
{
    resetCase();
    xcb_connection_t connection;
    const bool created = QXcbBackingStoreImage::createSystemVShmSegment(&connection, 4096, nullptr);
    CHECK(created);
    CHECK(freedSegments == 1);
    CHECK(liveSegments() == 0);
    return finishCase("success-null-info-test-run");
}

static bool shmgetFailure()
{
    resetCase();
    failShmGet = true;
    xcb_connection_t connection;
    CHECK(!QXcbBackingStoreImage::createSystemVShmSegment(&connection, 4096, nullptr));
    CHECK(liveSegments() == 0);
    CHECK(freedSegments == 0);
    return finishCase("shmget-failure");
}

static bool shmatFailureCleanup()
{
    resetCase();
    failShmAt = true;
    clobberErrnoOnRemove = true;
    xcb_connection_t connection;
    CHECK(!QXcbBackingStoreImage::createSystemVShmSegment(&connection, 4096, nullptr));
    CHECK(freedSegments == 1);
    CHECK(liveSegments() == 0);
    const std::string expected = std::string("shmat() failed (") + std::to_string(ENOMEM)
        + ": " + std::strerror(ENOMEM) + ")";
    bool preservedErrno = false;
    for (const std::string &warning : warnings)
        preservedErrno |= warning.find(expected) != std::string::npos;
    CHECK(preservedErrno);
    return finishCase("shmat-failure-cleanup-and-errno");
}

static bool xcbAttachFailureCleanup()
{
    resetCase();
    failXcbAttach = true;
    xcb_connection_t connection;
    CHECK(!QXcbBackingStoreImage::createSystemVShmSegment(&connection, 4096, nullptr));
    CHECK(freedSegments == 1);
    CHECK(liveSegments() == 0);
    CHECK(allocatedErrors == 1);
    CHECK(freedErrors == 1);
    return finishCase("xcb-attach-failure-cleanup");
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        std::fprintf(stderr, "Usage: %s CASE\n", argv[0]);
        return 2;
    }
    const std::string test = argv[1];
    bool (*run)() = nullptr;
    if (test == "success-retained-info") run = successWithRetainedInfo;
    else if (test == "success-null-info-test-run") run = successWithoutRetainedInfo;
    else if (test == "shmget-failure") run = shmgetFailure;
    else if (test == "shmat-failure-cleanup-and-errno") run = shmatFailureCleanup;
    else if (test == "xcb-attach-failure-cleanup") run = xcbAttachFailureCleanup;
    else {
        std::fprintf(stderr, "Unknown case: %s\n", argv[1]);
        return 2;
    }
    return run() ? 0 : 1;
}
