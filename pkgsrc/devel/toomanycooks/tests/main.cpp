#define TMC_IMPL
#include <tmc/all_headers.hpp>
#include <tmc/version.hpp>
static_assert(TMC_VERSION == 0x00010601);

tmc::task<int> fib(int n)
{
    if (n < 2) co_return n;
    auto [a, b] = co_await tmc::spawn_tuple(fib(n - 1), fib(n - 2));
    co_return a + b;
}
int main()
{
    tmc::cpu_executor().init();
    return tmc::post_waitable(tmc::cpu_executor(), fib(10)).get() == 55 ? 0 : 1;
}
