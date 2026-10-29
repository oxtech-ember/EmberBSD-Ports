// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <ada.h>
int main() {
  auto url = ada::parse("https://example.com/path?query=1");
  return url && url->get_hostname() == "example.com" ? 0 : 1;
}
