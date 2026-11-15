#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compile selected production functions verbatim.
"""Focused executable checks for the NetBSD mDNSResponder adaptations."""
import argparse
from pathlib import Path
import subprocess
import sys


def function(source, name):
    """Extract one complete C function while ignoring braces in comments/strings."""
    start = source.index(name)
    opening = source.index('{', start)
    depth = 0
    state = 'code'
    escaped = False
    i = opening
    while i < len(source):
        c = source[i]
        n = source[i + 1] if i + 1 < len(source) else ''
        if state == 'line-comment':
            if c == '\n':
                state = 'code'
        elif state == 'block-comment':
            if c == '*' and n == '/':
                state = 'code'
                i += 1
        elif state in ('string', 'char'):
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif (state == 'string' and c == '"') or (state == 'char' and c == "'"):
                state = 'code'
        elif c == '/' and n == '/':
            state = 'line-comment'
            i += 1
        elif c == '/' and n == '*':
            state = 'block-comment'
            i += 1
        elif c == '"':
            state = 'string'
        elif c == "'":
            state = 'char'
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1
    raise ValueError('unterminated function: ' + name)


def compile_run(cc, work, name, source, flags=(), includes=()):
    c_file = work / (name + '.c')
    binary = work / name
    c_file.write_text(source)
    command = [cc, '-std=c11', '-Wall', '-Wextra', '-Werror', *flags]
    for include in includes:
        command.extend(['-I', str(include)])
    command.extend([str(c_file), '-o', str(binary)])
    subprocess.run(command, check=True)
    subprocess.run([str(binary)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, help='prepared mDNSResponder source root')
    parser.add_argument('--work', required=True, help='new test output directory')
    parser.add_argument('--cc', required=True, help='absolute host C compiler')
    parser.add_argument('--sanitize', action='store_true',
                        help='run the interface lifecycle fixture with ASan and UBSan')
    args = parser.parse_args()
    source = Path(args.source).resolve()
    work = Path(args.work).resolve()
    cc = Path(args.cc).resolve()
    if not cc.is_absolute() or not cc.is_file():
        parser.error('--cc must name an existing absolute compiler')
    work.mkdir(parents=True, exist_ok=False)
    posix = (source / 'mDNSPosix/PosixDaemon.c').read_text()
    net = (source / 'mDNSPosix/mDNSPosix.c').read_text()
    common = (source / 'mDNSShared/PlatformCommon.c').read_text()
    core = (source / 'mDNSCore/mDNS.c').read_text()

    route_fixture = r'''#include <assert.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t mDNSu8;
typedef uint32_t mDNSu32;
typedef union { mDNSu8 b[4]; mDNSu32 NotAnInteger; } mDNSv4Addr;
typedef union { mDNSu8 b[16]; mDNSu32 l[4]; } mDNSv6Addr;
typedef struct { int type; union { mDNSv4Addr v4; mDNSv6Addr v6; } ip; } mDNSAddr;
typedef struct { char c[256]; } domainname;
typedef struct { int unused; } mDNS;
enum { mDNSAddrType_None = 0, mDNSAddrType_IPv4 = 4 };
#define CONFIG_FILE "/fixture/mdnsd.conf"
#define uDNS_SERVERS_FILE "/fixture/resolv.conf"
static domainname DynDNSHostname, DynDNSZone;
static mDNSAddr probed;
static int info_logs, error_logs, config_changes, primary_changes;
static int ParseDNSServers(mDNS *m, const char *p) { (void)m; (void)p; return -1; }
static void LogInfo(const char *fmt, ...) { (void)fmt; info_logs++; }
static void __attribute__((unused)) LogMsg(const char *fmt, ...) { (void)fmt; error_logs++; }
static void mDNS_SetPrimaryInterfaceInfo(mDNS *m, const mDNSAddr *a, const void *b, const void *c)
{ (void)m; (void)a; (void)b; (void)c; primary_changes++; }
static void ReadDDNSSettingsFromConfFile(mDNS *m, const char *p, domainname *h, domainname *z, int *d)
{ (void)m; (void)p; (void)z; (void)d; h->c[0] = 0; }
static void mDNSPlatformSourceAddrForDest(mDNSAddr *src, const mDNSAddr *dst)
{ probed = *dst; src->type = mDNSAddrType_IPv4; }
static void mDNS_AddDynDNSHostName(mDNS *m, domainname *h, void *a, void *b)
{ (void)m; (void)h; (void)a; (void)b; }
static void mDNS_ConfigChanged(mDNS *m) { (void)m; config_changes++; }
'''
    route_main = r'''int main(void)
{
    mDNS context = {0};
    const mDNSu8 expected[4] = {198, 51, 100, 42};
    Reconfigure(&context);
    assert(probed.type == mDNSAddrType_IPv4);
    assert(memcmp(probed.ip.v4.b, expected, sizeof(expected)) == 0);
    assert(info_logs == 1 && error_logs == 0);
    assert(config_changes == 1 && primary_changes == 2);
    return 0;
}
'''
    compile_run(args.cc, work, 'reconfigure', route_fixture + function(posix, 'static void Reconfigure(mDNS *m)') + route_main)

    privilege_preamble = r'''#include <assert.h>
#include <errno.h>
#include <grp.h>
#include <pwd.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
typedef enum { mStatus_NoError = 0, mStatus_Invalid = -1 } mStatus;
#define mDNSlocal static
#define MDNSD_USER "fixture-mdns-user"
#define PUB_S "%s"
#define MDNS_LOG_CATEGORY_DEFAULT 1
#define MDNS_LOG_ERROR 2
static struct passwd pw;
static int user_exists, gid_calls, uid_calls, log_calls, fail_gid, fail_uid;
static struct passwd *fixture_getpwnam(const char *name)
{ assert(strcmp(name, MDNSD_USER) == 0); return user_exists ? &pw : NULL; }
static int fixture_setgid(gid_t id) { assert(id == pw.pw_gid); gid_calls++; if (fail_gid) { errno = EPERM; return -1; } return 0; }
static int fixture_setuid(uid_t id) { assert(id == pw.pw_uid); uid_calls++; if (fail_uid) { errno = EPERM; return -1; } return 0; }
static void fixture_logmsg(const char *fmt, ...) { (void)fmt; log_calls++; }
static void fixture_logredact(int a, int b, const char *fmt, ...)
{ (void)a; (void)b; (void)fmt; log_calls++; }
#define getpwnam fixture_getpwnam
#define setgid fixture_setgid
#define setuid fixture_setuid
#define LogMsg fixture_logmsg
#define LogRedact fixture_logredact
'''
    privilege_main = r'''int main(void)
{
    user_exists = 0;
#ifdef MDNSD_NOROOT
    assert(DropPrivileges() == mStatus_Invalid);
#else
    assert(DropPrivileges() == mStatus_NoError);
#endif
    assert(log_calls == 1 && gid_calls == 0 && uid_calls == 0);
    user_exists = 1; pw.pw_gid = 31; pw.pw_uid = 42;
    fail_gid = 1; fail_uid = 1;
    assert(DropPrivileges() == mStatus_NoError);
    assert(gid_calls == 1 && uid_calls == 1 && log_calls == 3);
    return 0;
}
'''
    drop = function(posix, 'mDNSlocal mStatus DropPrivileges(void)')
    compile_run(args.cc, work, 'drop-privileges-noroot', privilege_preamble + drop + privilege_main,
                flags=('-DMDNSD_NOROOT',))
    compile_run(args.cc, work, 'drop-privileges-fallback', privilege_preamble + drop + privilege_main)

    send_fixture = r'''#include <assert.h>
#include <errno.h>
typedef int mDNSBool;
#define mDNSlocal static
#define mDNStrue 1
#define mDNSfalse 0
#define __NetBSD__ 1
'''
    send_main = r'''int main(void)
{
    assert(mDNSPosixShouldReturnTransientSendError(EHOSTDOWN, 0));
    assert(mDNSPosixShouldReturnTransientSendError(ENETDOWN, 0));
    assert(mDNSPosixShouldReturnTransientSendError(EHOSTUNREACH, 0));
    assert(mDNSPosixShouldReturnTransientSendError(ENETUNREACH, 0));
    assert(mDNSPosixShouldReturnTransientSendError(EADDRNOTAVAIL, 1));
    assert(!mDNSPosixShouldReturnTransientSendError(EADDRNOTAVAIL, 0));
    assert(!mDNSPosixShouldReturnTransientSendError(EHOSTDOWN, 1));
    return 0;
}
'''
    compile_run(args.cc, work, 'transient-send-errors', send_fixture +
                function(net, 'mDNSlocal mDNSBool mDNSPosixShouldReturnTransientSendError') + send_main)

    ipv6 = function(net, 'mDNSlocal void mDNSPosixIgnoreIPv6SocketFailure')
    ipv6_preamble = '#include <assert.h>\ntypedef int mStatus;\n#define mDNSlocal static\nenum { mStatus_NoError = 0 };\n'
    compile_run(args.cc, work, 'ipv6-fallback-netbsd', ipv6_preamble + '#define __NetBSD__ 1\n' + ipv6 + r'''int main(void)
{
    int error = 17, socket = 8;
    mDNSPosixIgnoreIPv6SocketFailure(&error, &socket);
    assert(error == mStatus_NoError && socket == -1);
    error = mStatus_NoError; socket = 9;
    mDNSPosixIgnoreIPv6SocketFailure(&error, &socket);
    assert(error == mStatus_NoError && socket == 9);
    return 0;
}
''')
    compile_run(args.cc, work, 'ipv6-error-other-platform', ipv6_preamble + ipv6 + r'''int main(void)
{
    int error = 17, socket = 8;
    mDNSPosixIgnoreIPv6SocketFailure(&error, &socket);
    assert(error == 17 && socket == 8);
    return 0;
}
''')

    platform = r'''#include <assert.h>
#include <errno.h>
#include <arpa/inet.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include "mDNSEmbeddedAPI.h"
static int connected_family, connected_port, info_logs, error_logs, closed;
static int fixture_socket(int domain, int type, int protocol)
{ (void)type; (void)protocol; assert(domain == AF_INET); return 12; }
static int fixture_connect(int fd, const struct sockaddr *addr, socklen_t len)
{
    (void)len; assert(fd == 12); connected_family = addr->sa_family;
    if (addr->sa_family == AF_INET) connected_port = ((const struct sockaddr_in *)addr)->sin_port;
    else connected_port = ((const struct sockaddr_in6 *)addr)->sin6_port;
    errno = EADDRNOTAVAIL; return -1;
}
static int fixture_getsockname(int fd, struct sockaddr *addr, socklen_t *len)
{ (void)fd; (void)addr; (void)len; assert(0); return -1; }
static int fixture_close(int fd) { assert(fd == 12); closed++; return 0; }
static void fixture_logmsg(const char *fmt, ...) { (void)fmt; error_logs++; }
static void fixture_loginfo(const char *fmt, ...) { (void)fmt; info_logs++; }
#undef LogMsg
#undef LogInfo
#define socket fixture_socket
#define connect fixture_connect
#define getsockname fixture_getsockname
#define close fixture_close
#define LogMsg fixture_logmsg
#define LogInfo fixture_loginfo
'''
    platform_main = r'''int main(void)
{
    mDNSAddr src = {0}, dst = {0};
    dst.type = mDNSAddrType_IPv4;
    dst.ip.v4.b[0] = 198; dst.ip.v4.b[1] = 51; dst.ip.v4.b[2] = 100; dst.ip.v4.b[3] = 42;
    mDNSPlatformSourceAddrForDest(&src, &dst);
    assert(connected_family == AF_INET && ntohs((uint16_t)connected_port) == 7);
    assert(info_logs == 1 && error_logs == 0 && closed == 1);
    dst.ip.v4.b[3] = 43; closed = 0;
    mDNSPlatformSourceAddrForDest(&src, &dst);
    assert(ntohs((uint16_t)connected_port) == 7 && info_logs == 1 && error_logs == 1 && closed == 1);
    dst.type = mDNSAddrType_IPv6; closed = 0;
    mDNSPlatformSourceAddrForDest(&src, &dst);
    assert(connected_family == AF_INET6 && ntohs((uint16_t)connected_port) == 7);
    assert(info_logs == 1 && error_logs == 2 && closed == 1);
    return 0;
}
'''
    platform_code = platform + function(common, 'mDNSexport void mDNSPlatformSourceAddrForDest(') + platform_main
    compile_run(args.cc, work, 'source-address-probe', platform_code,
                flags=('-DNOT_HAVE_SA_LEN',), includes=(source / 'mDNSCore', source / 'mDNSShared'))

    advertise_fixture = r'''#include <assert.h>
#include <stdint.h>
typedef unsigned int mDNSu32;
typedef struct NetworkInterfaceInfo NetworkInterfaceInfo;
struct NetworkInterfaceInfo { int Advertise; NetworkInterfaceInfo *next; };
typedef struct { int rrtype; } ResourceRecord;
typedef struct { ResourceRecord resrec; int AutoTarget; } AuthRecord;
typedef struct {
    int AdvertiseLocalAddresses;
    mDNSu32 AutoTargetServices;
    NetworkInterfaceInfo *HostInterfaces;
} mDNS;
enum { kDNSType_SRV = 33, Target_AutoHost = 1, kDeadvertiseFlag_NormalHostname = 1 };
#define mDNSlocal static
#define PRI_S "%s"
#define RRLocalOnly(rr) 0
#define AuthRecord_uDNS(rr) 0
#define LogRedact(...) ((void)0)
#define ARDisplayString(m, rr) "record"
static unsigned advertisements, deadvertisements;
static void AdvertiseInterface(mDNS *m, NetworkInterfaceInfo *set)
{ (void)m; assert(set->Advertise); advertisements++; }
static void DeadvertiseInterface(mDNS *m, NetworkInterfaceInfo *set, int flags)
{ (void)m; assert(set->Advertise && flags == kDeadvertiseFlag_NormalHostname); deadvertisements++; }
'''
    advertise_functions = '\n'.join((
        function(core, 'mDNSlocal void AdvertiseInterfaceIfNeeded(mDNS *const m, NetworkInterfaceInfo *set)\n{'),
        function(core, 'mDNSlocal void AdvertiseNecessaryInterfaceRecords(mDNS *const m)'),
        function(core, 'mDNSlocal void DecrementAutoTargetServices('),
    ))
    advertise_main = r'''int main(void)
{
    mDNS m = {0};
    NetworkInterfaceInfo interface = {1, 0};
    AuthRecord service = {{kDNSType_SRV}, Target_AutoHost};
    m.HostInterfaces = &interface;

    /* The interface-registration helper honors Init(true) with no AutoTarget service. */
    m.AdvertiseLocalAddresses = 1;
    AdvertiseInterfaceIfNeeded(&m, &interface);
    assert(advertisements == 1 && deadvertisements == 0);

    /* Keep the interface Advertise gate and the client-only Init(false) contract. */
    interface.Advertise = 0;
    AdvertiseNecessaryInterfaceRecords(&m);
    assert(advertisements == 1);
    interface.Advertise = 1;
    m.AdvertiseLocalAddresses = 0;
    AdvertiseInterfaceIfNeeded(&m, &interface);
    assert(advertisements == 1);
    m.AutoTargetServices = 1;
    AdvertiseInterfaceIfNeeded(&m, &interface);
    assert(advertisements == 2);

    /* Removing the last AutoHost service must retain Init(true) host records. */
    m.AdvertiseLocalAddresses = 1;
    m.AutoTargetServices = 1;
    DecrementAutoTargetServices(&m, &service);
    assert(m.AutoTargetServices == 0 && deadvertisements == 0);

    /* Init(false) still removes records that existed only for AutoHost service. */
    m.AdvertiseLocalAddresses = 0;
    m.AutoTargetServices = 1;
    DecrementAutoTargetServices(&m, &service);
    assert(m.AutoTargetServices == 0 && deadvertisements == 1);
    return 0;
}
'''
    compile_run(args.cc, work, 'core-advertise-local-addresses',
                advertise_fixture + advertise_functions + advertise_main)

    watcher_functions = '\n'.join((
        function(net, 'mDNSlocal mStatus WatchForInterfaceChange(mDNS *const m)'),
        function(net, 'mDNSlocal void StopWatchingForInterfaceChange(mDNS *const m)'),
        function(net, 'mDNSexport mStatus mDNSPlatformInit(mDNS *const m)'),
        function(net, 'mDNSexport void mDNSPlatformClose(mDNS *const m)'),
    ))
    watcher_fixture = r'''#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
typedef int mStatus;
typedef int mDNSBool;
typedef struct { char c[256]; } domainlabel;
typedef struct IfChangeRec IfChangeRec;
typedef struct { IfChangeRec *ifChangeRec; int unicastSocket4; } mDNS_PlatformSupport;
typedef struct mDNS {
    mDNS_PlatformSupport *p;
    int CanReceiveUnicastOn5353;
    domainlabel nicelabel, hostlabel;
} mDNS;
typedef int mDNSIPPort;
typedef void (*mDNSPosixEventCallback)(int, void *);
enum { mStatus_NoError = 0, mStatus_NoMemoryErr = 12, mDNStrue = 1 };
#define HAVE_IPV6 0
#define POSIX_HAS_TLS 0
#define UNICAST_DISABLED 1
#define mDNSlocal static
#define mDNSexport
struct IfChangeRec { int NotifySD; mDNS *mDNS; };
static int zeroIPPort, route_listener_count, next_fd = 17;
static int queued_events, lost_events, setup_result;
static int add_result, open_result, add_calls, remove_calls, close_calls, udp_close_calls, free_calls;
static int refreshed_interfaces, init_complete_calls, cleared_interfaces;
static void *mDNSPlatformMemAllocateClear(size_t size) { return calloc(1, size); }
static void mDNSPlatformMemFree(void *ptr) { free_calls++; free(ptr); }
static int mDNSPlatformInit_CanReceiveUnicast(void) { return 1; }
static void GetUserSpecifiedFriendlyComputerName(domainlabel *label) { label->c[0] = 0; }
static void GetUserSpecifiedRFC1034ComputerName(domainlabel *label) { label->c[0] = 0; }
static void MakeDomainLabelFromLiteralString(domainlabel *label, const char *text)
{ strncpy(label->c, text, sizeof(label->c) - 1); }
static void mDNS_SetFQDN(mDNS *m) { (void)m; }
static int SetupSocket(struct sockaddr *addr, mDNSIPPort port, int index, int *fd)
{ (void)addr; (void)port; (void)index; *fd = 99; return 0; }
static mStatus SetupInterfaceList(mDNS *m)
{
    (void)m;
    /* Simulate DHCP adding the first IPv4 address during getifaddrs(). */
    if (route_listener_count != 0) queued_events++;
    else lost_events++;
    return setup_result;
}
static void mDNSCoreInitComplete(mDNS *m, mStatus status)
{ (void)m; assert(status == 0); init_complete_calls++; }
static mStatus PosixErrorToStatus(int error) { return error; }
static void ClearInterfaceList(mDNS *m) { (void)m; cleared_interfaces++; }
void mDNSPlatformClose(mDNS *const m);
static mStatus OpenIfNotifySocket(int *fd)
{
    if (open_result != 0) { *fd = -1; return open_result; }
    *fd = next_fd++; route_listener_count++; return 0;
}
static void InterfaceChangeCallback(int fd, void *context) { (void)fd; (void)context; }
static mStatus mDNSPosixAddFDToEventLoop(int fd, mDNSPosixEventCallback cb, void *context)
{ (void)fd; (void)cb; (void)context; add_calls++; return add_result; }
static mStatus mDNSPosixRemoveFDFromEventLoop(int fd)
{ assert(fd >= 17 && fd < 99); remove_calls++; return 0; }
static int fixture_close(int fd)
{
    if (fd >= 17 && fd < 99) { close_calls++; route_listener_count--; }
    else if (fd == 99) udp_close_calls++;
    else assert(0);
    return 0;
}
#define close fixture_close
static void RunQueuedEventLoop(void)
{ if (queued_events != 0) { queued_events--; refreshed_interfaces++; } }
'''
    watcher_main = r'''int main(void)
{
    mDNS_PlatformSupport support = {0}, support2 = {0};
    mDNS m = {&support, 0, {{0}}, {{0}}};
    mDNS m2 = {&support2, 0, {{0}}, {{0}}};
    mStatus result;

    /* The old ordering drops an address event emitted during the first snapshot. */
    result = SetupInterfaceList(&m);
    assert(result == 0);
    assert(lost_events == 1 && queued_events == 0);
    result = WatchForInterfaceChange(&m);
    assert(result == 0);
    StopWatchingForInterfaceChange(&m);
    assert(add_calls == 1);

    /* The actual initializer now subscribes before SetupInterfaceList. */
    lost_events = queued_events = 0;
    result = mDNSPlatformInit(&m);
    assert(result == 0);
    assert(lost_events == 0 && queued_events == 1 && init_complete_calls == 1);
    RunQueuedEventLoop();
    assert(refreshed_interfaces == 1 && queued_events == 0);
    mDNSPlatformClose(&m);
    assert(support.ifChangeRec == NULL && support.unicastSocket4 == -1);
    assert(route_listener_count == 0 && udp_close_calls == 1);
    mDNSPlatformClose(&m); /* repeated close is safe */
    assert(route_listener_count == 0 && udp_close_calls == 1);

    /* A failure after watcher registration tears down route and UDP sockets. */
    setup_result = 5;
    result = mDNSPlatformInit(&m);
    assert(result == 5);
    assert(support.ifChangeRec == NULL && support.unicastSocket4 == -1);
    assert(route_listener_count == 0 && udp_close_calls == 2);
    assert(init_complete_calls == 1);
    mDNSPlatformClose(&m);
    assert(route_listener_count == 0 && udp_close_calls == 2);

    /* Contexts are per instance, including independent close. */
    setup_result = 0;
    result = WatchForInterfaceChange(&m);
    assert(result == 0);
    result = WatchForInterfaceChange(&m2);
    assert(result == 0);
    assert(support.ifChangeRec != NULL && support2.ifChangeRec != NULL);
    assert(route_listener_count == 2);
    StopWatchingForInterfaceChange(&m);
    assert(support.ifChangeRec == NULL && support2.ifChangeRec != NULL);
    assert(route_listener_count == 1);
    StopWatchingForInterfaceChange(&m2);
    assert(support2.ifChangeRec == NULL && route_listener_count == 0);

    /* Watcher setup failures release every descriptor they acquired. */
    add_result = 5;
    result = WatchForInterfaceChange(&m);
    assert(result == 5);
    assert(support.ifChangeRec == NULL && route_listener_count == 0);
    open_result = 5;
    result = WatchForInterfaceChange(&m);
    assert(result == 5);
    assert(support.ifChangeRec == NULL && route_listener_count == 0);
    assert(add_calls == 6 && remove_calls == 5);
    assert(close_calls == 6 && udp_close_calls == 2 && free_calls == 7);
    assert(cleared_interfaces == 4);
    return 0;
}
'''
    compile_run(args.cc, work, 'interface-event-before-snapshot',
                watcher_fixture + watcher_functions + watcher_main,
                flags=(('-fsanitize=address,undefined', '-fno-omit-frame-pointer')
                       if args.sanitize else ()))

    netlink_open = function(net, 'mDNSlocal mStatus OpenIfNotifySocket(int *pFD)')
    netlink_fixture = r'''#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>
#include <sys/socket.h>
typedef int mStatus;
enum { mStatus_NoError = 0 };
#define mDNSlocal static
#define AF_NETLINK 99
#define NETLINK_ROUTE 0
#define RTMGRP_LINK 1
#define RTMGRP_IPV4_IFADDR 2
#define RTMGRP_IPV6_IFADDR 4
struct sockaddr_nl { unsigned short nl_family; unsigned int nl_groups; };
static int bind_failure, socket_failure, close_calls;
static void mDNSPlatformMemZero(void *ptr, size_t size) { memset(ptr, 0, size); }
static int fixture_socket(int domain, int type, int protocol)
{
    assert(domain == AF_NETLINK && type == SOCK_RAW && protocol == NETLINK_ROUTE);
    if (socket_failure) { errno = ENFILE; return -1; }
    return 46;
}
static int fixture_fcntl(int fd, int command, int flags)
{ assert(fd == 46 && command == F_SETFL && flags == O_NONBLOCK); return 0; }
static int fixture_bind(int fd, const struct sockaddr *addr, socklen_t len)
{
    const struct sockaddr_nl *netlink = (const struct sockaddr_nl *)addr;
    assert(fd == 46 && len == sizeof(*netlink));
    assert(netlink->nl_family == AF_NETLINK);
    assert(netlink->nl_groups == (RTMGRP_LINK | RTMGRP_IPV4_IFADDR | RTMGRP_IPV6_IFADDR));
    if (bind_failure) { errno = EACCES; return -1; }
    return 0;
}
static int fixture_close(int fd) { assert(fd == 46); close_calls++; errno = EBADF; return 0; }
#define socket fixture_socket
#define fcntl fixture_fcntl
#define bind fixture_bind
#define close fixture_close
'''
    netlink_main = r'''int main(void)
{
    int fd = -1;
    int result;
    bind_failure = 1;
    result = OpenIfNotifySocket(&fd);
    assert(result == EACCES);
    assert(fd == -1 && close_calls == 1);

    bind_failure = 0;
    result = OpenIfNotifySocket(&fd);
    assert(result == 0);
    assert(fd == 46 && close_calls == 1);

    socket_failure = 1; fd = -1;
    result = OpenIfNotifySocket(&fd);
    assert(result == ENFILE);
    assert(fd == -1 && close_calls == 1);
    return 0;
}
'''
    compile_run(args.cc, work, 'netlink-watcher-bind-failure',
                netlink_fixture + netlink_open + netlink_main)
    print('mDNS NetBSD/core source adaptations: production-function regressions passed')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print('test-netbsd-adaptations: ' + str(exc), file=sys.stderr)
        sys.exit(1)
