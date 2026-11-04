// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors; real SDDM VT source with mocked device syscalls.
#include <QDebug>
#include <QString>
#include <QFileInfo>
#include <qscopeguard.h>
#include <cerrno>
#include <cstring>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <map>
typedef unsigned char unchar; // NetBSD user ABI spelling, absent on Darwin.
#include <dev/wscons/wsdisplay_usl_io.h>
#include <dev/wscons/wsconsio.h>

static int active = 1, nextfd = 10, setProcess = 0, textTransitions = 0;
static int modes[8];
static std::map<int, int> descriptors;
static bool queryFailure, activeOpenFailure;
static int fakeOpen(const char *path, int, ...) {
    int screen;
    if (std::sscanf(path, "/dev/ttyE%d", &screen) != 1 || screen < 0 || screen >= 8) {
        errno = ENOENT;
        return -1;
    }
    if (activeOpenFailure && screen + 1 == active && screen != 0) {
        errno = EACCES;
        return -1;
    }
    descriptors[nextfd] = screen + 1;
    return nextfd++;
}
static int fakeClose(int fd) { descriptors.erase(fd); return 0; }
static ssize_t fakeWrite(int, const void *, size_t count) { return count; }
static int fakeIoctl(int fd, unsigned long request, ...) {
    auto it = descriptors.find(fd);
    if (it == descriptors.end()) { errno = EBADF; return -1; }
    const int screen = it->second;
    va_list ap;
    va_start(ap, request);
    int result = 0;
    if (request == VT_GETACTIVE) {
        int *value = va_arg(ap, int *);
        if (queryFailure) { errno = EIO; result = -1; }
        else *value = active;
    } else if (request == VT_GETMODE) {
        auto *mode = va_arg(ap, vt_mode *);
        *mode = {};
        mode->mode = VT_AUTO;
    } else if (request == WSDISPLAYIO_GMODE) {
        *va_arg(ap, int *) = modes[screen - 1];
    } else if (request == KDSETMODE) {
        const int value = va_arg(ap, int);
        if (value == KD_TEXT) ++textTransitions;
        modes[screen - 1] = value == KD_TEXT
            ? WSDISPLAYIO_MODE_EMUL : WSDISPLAYIO_MODE_MAPPED;
    } else if (request == VT_SETMODE) {
        auto *mode = va_arg(ap, vt_mode *);
        if (mode->mode == VT_PROCESS) ++setProcess;
    } else if (request == VT_ACTIVATE) {
        int destination = va_arg(ap, int);
        // Match wsdisplay_switch: an unmanned graphics screen cannot detach.
        if (destination != active && modes[active - 1] != WSDISPLAYIO_MODE_EMUL) {
            errno = EBUSY;
            result = -1;
        } else active = destination;
    } else if (request == VT_WAITACTIVE) {
        if (va_arg(ap, int) != active) { errno = EBUSY; result = -1; }
    } else { errno = ENOTTY; result = -1; }
    va_end(ap);
    return result;
}

// Compile the actual implementation. The mock replaces only device syscalls;
// Qt and the wscons ioctl declarations are the real selected dependencies.
#define __NetBSD__ 1
#ifndef SIGRTMAX
#define SIGRTMAX 63
#endif
#define open fakeOpen
#define close fakeClose
#define write fakeWrite
#define ioctl fakeIoctl
#ifndef VT_SOURCE
#define VT_SOURCE "VirtualTerminal.cpp"
#endif
#include VT_SOURCE
#undef ioctl
#undef write
#undef close
#undef open
#undef __NetBSD__

static void require(bool ok, const char *message) {
    if (!ok) { std::fprintf(stderr, "FAIL: %s\n", message); std::exit(1); }
}
static void reset(int initial, int mode) {
    require(descriptors.empty(), "descriptor leak");
    std::memset(modes, 0, sizeof(modes));
    active = initial;
    modes[active - 1] = mode;
    setProcess = textTransitions = 0;
    queryFailure = activeOpenFailure = false;
}
static void checkJump(int initial, int oldMode, int destination) {
    reset(initial, oldMode);
    SDDM::VirtualTerminal::jumpToVt(destination, true);
    require(active == destination, "requested VT did not become active");
    require(modes[destination - 1] == WSDISPLAYIO_MODE_MAPPED,
            "destination lost graphics mode");
    require(setProcess == 0, "pre-exec VT_PROCESS owner installed");
    if (initial == destination)
        require(textTransitions == 0, "same VT was switched to text mode");
    require(descriptors.empty(), "descriptor leak after successful switch");
}
int main() {
    qInstallMessageHandler([](QtMsgType, const QMessageLogContext &, const QString &) {});
    checkJump(1, WSDISPLAYIO_MODE_EMUL, 2);
    checkJump(5, WSDISPLAYIO_MODE_MAPPED, 2);
    checkJump(5, WSDISPLAYIO_MODE_DUMBFB, 2);
    checkJump(2, WSDISPLAYIO_MODE_MAPPED, 2);
    checkJump(2, WSDISPLAYIO_MODE_DUMBFB, 2);
    reset(5, WSDISPLAYIO_MODE_MAPPED);
    queryFailure = true;
    SDDM::VirtualTerminal::jumpToVt(2, true);
    require(active == 5 && descriptors.empty(), "failed query changed VT/leaked fd");
    reset(5, WSDISPLAYIO_MODE_MAPPED);
    activeOpenFailure = true;
    SDDM::VirtualTerminal::jumpToVt(2, true);
    require(active == 5 && descriptors.empty(), "failed open changed VT/leaked fd");
    std::puts("PASS: text/graphics/dumbfb handoff, same VT, query/open failure, fd lifetime");
}
