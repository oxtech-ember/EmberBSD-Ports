// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
// Portable C++20 constant evaluation for the selected Clang target.
#include <limits>

template <typename T> constexpr bool check_floating_constants() {
  constexpr T one = T(1);
  constexpr T epsilon = std::numeric_limits<T>::epsilon();
  constexpr T large = std::numeric_limits<T>::max();
  return std::numeric_limits<T>::radix == 2 && epsilon > T(0) &&
         one + epsilon > one && one + epsilon / T(2) == one &&
         (one + one / T(2)) * T(2) == T(3) && large / T(2) > one;
}

static_assert(check_floating_constants<float>());
static_assert(check_floating_constants<double>());
static_assert(check_floating_constants<long double>());
