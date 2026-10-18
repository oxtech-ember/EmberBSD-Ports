// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Exercise the actual OCCT stack trace API.
#include <Standard.hxx>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main(int argc, char** argv)
{
  if (argc != 2)
    return 2;
  const char* mode = argv[1];
  if (std::strcmp(mode, "unterminated") == 0)
  {
    char* data = static_cast<char*>(std::malloc(8));
    if (!data)
      return 2;
    std::memset(data, 'x', 8);
    const bool result = Standard::StackTrace(data, 8, 3, nullptr, 0);
    bool unchanged = true;
    for (int i = 0; i < 8; ++i)
      unchanged = unchanged && data[i] == 'x';
    std::free(data);
    return !result && unchanged ? 0 : 1;
  }
  char buffer[4096] = "prefix";
  if (std::strcmp(mode, "capacity") == 0)
  {
    const bool result = Standard::StackTrace(buffer, 3, 3, nullptr, 0);
    if (result || std::strcmp(buffer, "prefix") != 0)
    {
      std::fputs("declared capacity contract violated\n", stderr);
      return 1;
    }
    return 0;
  }
  if (std::strcmp(mode, "overflow") == 0)
    return Standard::StackTrace(buffer, sizeof(buffer), INT_MAX, nullptr, 0) ? 1 : 0;
  if (std::strcmp(mode, "skip-overflow") == 0)
    return Standard::StackTrace(buffer, sizeof(buffer), 1, nullptr, INT_MAX) ? 1 : 0;
  if (std::strcmp(mode, "exhausted") == 0)
    return Standard::StackTrace(buffer, sizeof(buffer), 3, nullptr, 1000) ? 1 : 0;
  if (std::strcmp(mode, "valid") != 0)
    return 2;
  const bool result = Standard::StackTrace(buffer, sizeof(buffer), 8, nullptr, 0);
  if (!result || std::strncmp(buffer, "prefix", 6) != 0 || !std::strstr(buffer, "Backtrace"))
    return 1;
  std::puts("OCCT stack trace bounds and valid output: PASS");
  return 0;
}
