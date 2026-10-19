#include <fmt/format.h>

#include <string>

int main() {
  if (fmt::format("{} {}", "EmberBSD", 12.2) != "EmberBSD 12.2") return 1;
  if (fmt::format("{:#x}", 48879) != "0xbeef") return 2;
  if (fmt::format("{:.2f}", 1.25) != "1.25") return 3;
  return 0;
}
