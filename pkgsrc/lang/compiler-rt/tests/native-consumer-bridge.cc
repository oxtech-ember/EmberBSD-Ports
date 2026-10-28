#include <stdexcept>
#include <string>
extern "C" std::string ember_libcxx_message() { return std::string("common libc++"); }
extern "C" void ember_libcxx_throw() { throw std::runtime_error("across dso"); }
