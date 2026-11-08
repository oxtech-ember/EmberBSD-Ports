#pragma once

#include <cstring>
#include <sys/socket.h>
#define NI_MAXHOST 128
#define NI_NUMERICHOST 1
inline int getnameinfo(const sockaddr *address, socklen_t, char *host,
                       socklen_t hostLength, char *, socklen_t, int)
{
    const char *value = address->numeric ? address->numeric
                        : address->sa_family == AF_INET6 ? "2001:db8::1" : "192.0.2.1";
    std::strncpy(host, value, hostLength);
    host[hostLength - 1] = '\0';
    return 0;
}
