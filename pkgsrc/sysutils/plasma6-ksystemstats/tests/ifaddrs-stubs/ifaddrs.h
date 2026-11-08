#pragma once

#include <sys/socket.h>
struct ifaddrs
{
    ifaddrs *ifa_next = nullptr;
    char *ifa_name = nullptr;
    sockaddr *ifa_addr = nullptr;
    void *ifa_data = nullptr;
};
extern "C" int getifaddrs(ifaddrs **);
extern "C" void freeifaddrs(ifaddrs *);
