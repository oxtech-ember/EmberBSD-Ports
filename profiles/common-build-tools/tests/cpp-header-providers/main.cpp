#include <argparse/argparse.hpp>
#include <sul/dynamic_bitset.hpp>
#include <libpopcnt.h>
#include <magic_enum/magic_enum.hpp>
#include <BS_thread_pool.hpp>

enum class ProviderSmokeEnum
{
    ready
};

static_assert(magic_enum::enum_name(ProviderSmokeEnum::ready) == "ready",
              "magic_enum header must expose enum_name");

int main()
{
    argparse::ArgumentParser parser("cpp-header-providers");

    sul::dynamic_bitset<> bits(8);
    bits.set(3);
    if (bits.count() != 1)
        return 1;

    const unsigned int value = 0x5;
    if (popcnt(&value, sizeof(value)) != 2)
        return 2;

    BS::light_thread_pool pool(1);
    auto task = pool.submit_task([] { return 7; });
    if (task.get() != 7)
        return 3;

    (void)parser;
    return 0;
}
