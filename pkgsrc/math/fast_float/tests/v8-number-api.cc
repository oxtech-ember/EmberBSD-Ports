// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
#include <dragonbox/dragonbox.h>
#include <fast_float/fast_float.h>
#include <assert.h>
#include <system_error>

template<class C> void parse(const C *s, const C *end) {
  double v = 0;
  auto flags = static_cast<fast_float::chars_format>(fast_float::chars_format::general |
      fast_float::chars_format::no_infnan | fast_float::chars_format::allow_leading_plus);
  auto result = fast_float::from_chars(s, end, v, flags);
  assert(result.ec == std::errc{} && result.ptr == end && v == 1.25);
}
int main() {
  auto d = jkj::dragonbox::to_decimal(-1.25);
  assert(d.is_negative && d.significand == 125 && d.exponent == -2);
  const char a[] = "+1.25"; const char16_t b[] = u"+1.25";
  parse(a, a + 5); parse(b, b + 5);
}
