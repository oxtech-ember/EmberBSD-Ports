#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "../files/network/NetBsdBackend.cpp"

namespace
{
enum class Result { Success, Failure };
Result nextResult = Result::Success;
ifaddrs *nextList = nullptr;
unsigned frees = 0;

ifaddrs *entry(const char *name, unsigned char family, if_data *counters = nullptr,
               const char *numeric = nullptr)
{
    auto *node = new ifaddrs;
    node->ifa_name = ::strdup(name);
    node->ifa_addr = new sockaddr;
    node->ifa_addr->sa_len = sizeof(sockaddr);
    node->ifa_addr->sa_family = family;
    node->ifa_addr->numeric = numeric;
    node->ifa_data = counters;
    return node;
}

ifaddrs *sample(std::uint64_t download, std::uint64_t upload)
{
    auto *data = new if_data{IFT_ETHER, download, upload};
    auto *link = entry("em0", AF_LINK, data);
    link->ifa_next = entry("em0", AF_INET);
    link->ifa_next->ifa_next = entry("em0", AF_INET6);
    return link;
}

void queue(ifaddrs *list)
{
    nextList = list;
    nextResult = Result::Success;
}

void require(bool condition, const char *message)
{
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", message);
        std::abort();
    }
}
}

extern "C" int getifaddrs(ifaddrs **list)
{
    if (nextResult == Result::Failure) {
        *list = nullptr;
        return -1;
    }
    *list = nextList;
    nextList = nullptr;
    return 0;
}

extern "C" void freeifaddrs(ifaddrs *list)
{
    ++frees;
    while (list) {
        ifaddrs *next = list->ifa_next;
        if (list->ifa_data)
            delete static_cast<if_data *>(list->ifa_data);
        delete list->ifa_addr;
        std::free(list->ifa_name);
        delete list;
        list = next;
    }
}

int main()
{
    IfaddrsNetDevice device(QString("em0"), QString("em0"));

    queue(sample(1000, 2000));
    device.update();
    require(frees == 1, "successful sample frees the address list");
    require(device.m_totalDownloadSensor->number == 1000, "first download total");
    require(device.m_totalUploadSensor->number == 2000, "first upload total");
    require(device.m_ipv4Sensor->text == "192.0.2.1", "IPv4 addresses are retained");
    require(device.m_ipv6Sensor->text == "2001:db8::1", "IPv6 addresses are retained");

    queue(sample(400, 1500));
    device.update();
    require(device.m_totalDownloadSensor->number == 400, "counter reset updates total");
    require(device.m_totalUploadSensor->number == 1500, "counter reset updates upload total");
    require(device.m_downloadSensor->number == 0, "counter reset does not emit a negative rate");

    queue(sample(450, 1700));
    device.update();
    require(device.m_downloadSensor->number == 50, "rate uses reset counter as previous sample");
    require(device.m_uploadSensor->number == 200, "upload rate uses reset counter as previous sample");

    device.m_totalDownloadSensor->number = 777;
    device.m_totalUploadSensor->number = 888;
    device.m_downloadSensor->number = 321;
    device.m_ipv4Sensor->text = "192.0.2.1";
    nextResult = Result::Failure;
    device.update();
    require(device.m_totalDownloadSensor->number == 777, "getifaddrs failure leaves totals unchanged");
    require(device.m_totalUploadSensor->number == 888, "getifaddrs failure leaves upload unchanged");
    require(device.m_downloadSensor->number == 321, "getifaddrs failure leaves rates unchanged");
    require(device.m_ipv4Sensor->text == "192.0.2.1", "getifaddrs failure leaves addresses unchanged");

    auto *withoutLink = entry("em0", AF_INET, nullptr, "198.51.100.8");
    queue(withoutLink);
    device.update();
    require(device.m_totalDownloadSensor->number == 777, "missing link data leaves counters unchanged");
    require(device.m_ipv4Sensor->text == "198.51.100.8", "missing link data still updates addresses");
    require(device.m_downloadSensor->number == 321, "missing link data leaves rates unchanged");
}
