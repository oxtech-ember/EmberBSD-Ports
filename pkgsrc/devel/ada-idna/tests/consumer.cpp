#include <idna.h>
#include <string>
int main() {
  if (ada::idna::to_ascii("b\xC3\xBC" "cher.de") != "xn--bcher-kva.de") return 1;
  if (!ada::idna::to_ascii(std::string("\xC0\xAF", 2)).empty()) return 2;
  return 0;
}
