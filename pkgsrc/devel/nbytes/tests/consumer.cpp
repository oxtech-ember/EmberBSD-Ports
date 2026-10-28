#include <nbytes.h>
#include <cstring>
int main() {
  char bytes[] = {1, 2, 3, 4};
  const char expected[] = {2, 1, 4, 3};
  if (!nbytes::SwapBytes16(bytes, sizeof(bytes)) ||
      std::memcmp(bytes, expected, sizeof(bytes)) != 0)
    return 1;
  if (nbytes::SwapBytes16(bytes, 3))
    return 2;
  return 0;
}
