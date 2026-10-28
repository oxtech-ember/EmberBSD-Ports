#ifdef NDEBUG
#error Active assertions required
#endif
#include <cassert>
#include <filesystem>
#include <locale>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <__config>
static_assert(_LIBCPP_HARDENING_MODE == _LIBCPP_HARDENING_MODE_EXTENSIVE);
static_assert(_LIBCPP_ABI_VERSION == 1);
extern "C" std::string ember_libcxx_message();
extern "C" void ember_libcxx_throw();
int main() {
  assert(ember_libcxx_message() == "common libc++");
  bool caught = false;
  try { ember_libcxx_throw(); } catch (const std::runtime_error& e) { caught = std::string(e.what()) == "across dso"; }
  assert(caught);
  std::filesystem::path path("dir/file");
  assert(path.filename().string() == "file");
  assert(!std::locale::classic().name().empty());
  int result = 0; std::thread worker([&] { result = 42; }); worker.join(); assert(result == 42);
  std::vector<int> values{1, 2, 3}; assert(values.at(2) == 3);
}
