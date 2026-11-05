#include <cstdint>

struct PointerEvent { void *udata; };
struct IntegerEvent { std::intptr_t udata; };

template<class Event>
static void *roundtrip(Event &event, void *value)
{
    auto typed = reinterpret_cast<decltype(event.udata)>(value);
    event.udata = typed;
    return reinterpret_cast<void *>(event.udata);
}

int main()
{
    int value = 7;
    PointerEvent pointer{};
    IntegerEvent integer{};
    return roundtrip(pointer, &value) != &value || roundtrip(integer, &value) != &value;
}
