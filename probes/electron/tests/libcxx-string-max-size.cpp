// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted E12 libc++ regression).
#include <cstddef>
#include <cstdint>
#include <limits>
#include <memory>
#include <string>

template <class T, class Size = std::size_t, class Difference = std::ptrdiff_t>
struct LimitedAllocator : std::allocator<T> {
  using value_type = T;
  using size_type = Size;
  using difference_type = Difference;
  size_type limit;
  constexpr explicit LimitedAllocator(size_type n = std::numeric_limits<size_type>::max()) noexcept : limit(n) {}
  template <class U> constexpr LimitedAllocator(const LimitedAllocator<U, Size, Difference>& other) noexcept : limit(other.limit) {}
  constexpr size_type max_size() const noexcept { return limit; }
  template <class U> struct rebind { using other = LimitedAllocator<U, Size, Difference>; };
};
template <class T, class U, class S, class D> constexpr bool operator==(const LimitedAllocator<T,S,D>& a, const LimitedAllocator<U,S,D>& b) noexcept { return a.limit == b.limit; }
template <class T, class U, class S, class D> constexpr bool operator!=(const LimitedAllocator<T,S,D>& a, const LimitedAllocator<U,S,D>& b) noexcept { return !(a == b); }

template <class CharT, std::size_t N, class Size = std::size_t, class Difference = std::ptrdiff_t>
constexpr std::size_t limited_string_max() {
  using Alloc = LimitedAllocator<CharT, Size, Difference>;
  using S = std::basic_string<CharT, std::char_traits<CharT>, Alloc>;
  S value{Alloc{static_cast<Size>(N)}};
  return static_cast<std::size_t>(value.max_size());
}
template <class CharT>
constexpr std::size_t default_string_max() {
  return std::basic_string<CharT>{}.max_size();
}

using LimitedCharString = std::basic_string<char, std::char_traits<char>, LimitedAllocator<char>>;
constexpr LimitedCharString short_with_zero_limit{"abc", LimitedAllocator<char>{0}};
constexpr LimitedCharString short_with_one_limit{"abc", LimitedAllocator<char>{1}};
static_assert(short_with_zero_limit.size() == 3 && short_with_zero_limit.size() <= short_with_zero_limit.max_size(), "SSO stays available with allocator limit zero");
static_assert(short_with_one_limit.size() == 3 && short_with_one_limit.size() <= short_with_one_limit.max_size(), "SSO stays available with allocator limit one");
static_assert(limited_string_max<char, 0>() == std::string{}.capacity(), "zero allocator limit preserves SSO capacity");
static_assert(limited_string_max<char, 1>() == std::string{}.capacity(), "one-byte allocator limit preserves SSO capacity");
static_assert(limited_string_max<char, 8>() == std::string{}.capacity(), "small allocator limit preserves SSO capacity");
static_assert(limited_string_max<char, 9>() == std::string{}.capacity(), "small allocator limit preserves SSO capacity");
static_assert(limited_string_max<char, 16>() == std::string{}.capacity(), "allocator limit below SSO backing requirement preserves SSO capacity");
static_assert(limited_string_max<char, 32>() == 23, "allocator-backed string capacity stays within allocator maximum");
static_assert(default_string_max<char>() <= static_cast<std::size_t>(std::numeric_limits<std::ptrdiff_t>::max()), "char string max_size fits ptrdiff_t");
static_assert(default_string_max<char8_t>() <= static_cast<std::size_t>(std::numeric_limits<std::ptrdiff_t>::max()) / sizeof(char8_t), "char8_t string max_size fits ptrdiff_t byte bound");
static_assert(default_string_max<char16_t>() <= static_cast<std::size_t>(std::numeric_limits<std::ptrdiff_t>::max()) / sizeof(char16_t), "char16_t string max_size fits ptrdiff_t byte bound");
static_assert(default_string_max<char32_t>() <= static_cast<std::size_t>(std::numeric_limits<std::ptrdiff_t>::max()) / sizeof(char32_t), "char32_t string max_size fits ptrdiff_t byte bound");
static_assert(default_string_max<wchar_t>() <= static_cast<std::size_t>(std::numeric_limits<std::ptrdiff_t>::max()) / sizeof(wchar_t), "wchar_t string max_size fits ptrdiff_t byte bound");
static_assert(limited_string_max<char16_t, std::numeric_limits<std::size_t>::max()>() <= static_cast<std::size_t>(std::numeric_limits<std::ptrdiff_t>::max()) / sizeof(char16_t), "custom char16_t allocator is byte bounded");
static_assert(limited_string_max<char32_t, std::numeric_limits<std::size_t>::max()>() <= static_cast<std::size_t>(std::numeric_limits<std::ptrdiff_t>::max()) / sizeof(char32_t), "custom char32_t allocator is byte bounded");
static_assert(limited_string_max<char, std::numeric_limits<std::size_t>::max(), std::size_t, std::int16_t>() <= static_cast<std::size_t>(std::numeric_limits<std::int16_t>::max()), "custom difference_type bounds string max_size");
static_assert(limited_string_max<char, std::numeric_limits<std::uint32_t>::max(), std::uint32_t, std::int64_t>() <= std::numeric_limits<std::uint32_t>::max(), "custom size_type maximum is preserved");
