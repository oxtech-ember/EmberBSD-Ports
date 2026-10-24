#include <cstdio>
#include <sstream>
#include <string>

#include "third_party/liburlpattern/part.h"

template <typename T>
bool Check(T value, const char* expected) {
  std::ostringstream stream;
  stream << value;
  if (stream.str() == expected) {
    return true;
  }
  std::fprintf(stderr, "expected [%s], got [%s]\n", expected,
               stream.str().c_str());
  return false;
}

int main() {
  using liburlpattern::Modifier;
  using liburlpattern::PartType;
  unsigned failures = 0;
  failures += !Check(PartType::kFullWildcard, "kFullWildcard");
  failures += !Check(PartType::kSegmentWildcard, "kSegmentWildcard");
  failures += !Check(PartType::kRegex, "kRegex");
  failures += !Check(PartType::kFixed, "kFixed");
  failures += !Check(Modifier::kZeroOrMore, "kZeroOrMore");
  failures += !Check(Modifier::kOptional, "kOptional");
  failures += !Check(Modifier::kOneOrMore, "kOneOrMore");
  failures += !Check(Modifier::kNone, "kNone");
  failures += !Check(static_cast<PartType>(-1), "Unknown PartType(-1)");
  failures += !Check(static_cast<PartType>(4), "Unknown PartType(4)");
  failures += !Check(static_cast<Modifier>(-1), "Unknown Modifier(-1)");
  failures += !Check(static_cast<Modifier>(4), "Unknown Modifier(4)");
  if (failures != 0) {
    return 1;
  }
  std::puts("PASS 12 liburlpattern enum stream cases");
  return 0;
}
