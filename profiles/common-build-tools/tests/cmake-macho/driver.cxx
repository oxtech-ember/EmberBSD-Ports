// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
#include "cmMachO.h"

#include <iostream>

int main(int argc, char** argv)
{
  if (argc != 2) {
    return 64;
  }
  cmMachO file(argv[1]);
  if (!file) {
    if (file.GetErrorMessage().empty() || !file.GetArchitectures().empty()) {
      return 65;
    }
    std::cout << "invalid\n";
    return 2;
  }
  auto architectures = file.GetArchitectures();
  if (!file.GetErrorMessage().empty() ||
      architectures.size() != file.GetHeaders().size()) {
    return 66;
  }
  for (auto const& architecture : architectures) {
    std::cout << architecture << '\n';
  }
  std::string name;
  if (file.GetInstallName(name)) {
    name.resize(name.find('\0'));
    std::cout << "install=" << name << '\n';
  }
  return 0;
}
