#pragma once

#include <cstdint>
using socklen_t = unsigned int;
struct sockaddr
{
    unsigned char sa_len = 0;
    unsigned char sa_family = 0;
    const char *numeric = nullptr;
};
#define AF_INET 2
#define AF_INET6 10
#define AF_LINK 18
