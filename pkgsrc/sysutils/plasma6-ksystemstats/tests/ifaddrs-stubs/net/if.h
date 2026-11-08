#pragma once

#include <cstdint>
struct if_data
{
    int ifi_type = 0;
    std::uint64_t ifi_ibytes = 0;
    std::uint64_t ifi_obytes = 0;
};
#define IFT_ETHER 6
#define IFT_IEEE80211 71
