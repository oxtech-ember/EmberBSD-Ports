#include <sys/types.h>
#include <LIEF/errors.hpp>
#include <LIEF/runtime/osx/Host.hpp>
#include <LIEF/runtime/windows/Host.hpp>
#include <cassert>
#include <cstdint>
#include <utility>

int main() {
  LIEF::runtime::osx::Host::version_t osx(1, 2, 3);
  LIEF::runtime::windows::Host::version_t windows(4, 5, 6);
  LIEF::result<uint64_t> value(uint64_t{42});
  assert(osx.major == 1 && osx.minor == 2 && osx.patch == 3);
  assert(windows.major == 4 && windows.minor == 5 && windows.build_number == 6);
  assert(std::move(value).value_or(0) == 42);
  return 0;
}
