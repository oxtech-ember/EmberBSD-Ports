// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted E12 libc++ regression).
#include <functional>
#include <new>
#include <stdexcept>
#include <string>
#include <utility>

#include <stdio.h>

static int fail(const char* what, int line) {
  fprintf(stderr, "failure at line %d: %s\n", line, what);
  return line;
}

#define CHECK(condition) do { if (!(condition)) return fail(#condition, __LINE__); } while (0)

template <class T>
struct AllocationStats {
  static size_t allocations;
  static size_t deallocations;
  static size_t largest_request;
};
template <class T> size_t AllocationStats<T>::allocations = 0;
template <class T> size_t AllocationStats<T>::deallocations = 0;
template <class T> size_t AllocationStats<T>::largest_request = 0;

template <class T>
struct LimitedAllocator {
  using value_type = T;
  using size_type = size_t;
  using difference_type = ptrdiff_t;
  template <class U> struct rebind { using other = LimitedAllocator<U>; };

  size_t limit;
  explicit LimitedAllocator(size_t maximum = static_cast<size_t>(-1)) noexcept : limit(maximum) {}
  template <class U> LimitedAllocator(const LimitedAllocator<U>& other) noexcept : limit(other.limit) {}

  T* allocate(size_t count) {
    if (count > limit)
      throw 99;
    ++AllocationStats<T>::allocations;
    if (count > AllocationStats<T>::largest_request)
      AllocationStats<T>::largest_request = count;
    return std::allocator<T>().allocate(count);
  }
  void deallocate(T* pointer, size_t count) noexcept {
    ++AllocationStats<T>::deallocations;
    std::allocator<T>().deallocate(pointer, count);
  }
  size_t max_size() const noexcept { return limit; }
};
template <class T, class U>
bool operator==(const LimitedAllocator<T>& a, const LimitedAllocator<U>& b) noexcept { return a.limit == b.limit; }
template <class T, class U>
bool operator!=(const LimitedAllocator<T>& a, const LimitedAllocator<U>& b) noexcept { return !(a == b); }

using LimitedString = std::basic_string<char, std::char_traits<char>, LimitedAllocator<char>>;

static int test_string_boundaries() {
  // The previous call has returned, so all strings and their allocations are gone.
  CHECK(AllocationStats<char>::allocations == AllocationStats<char>::deallocations);
  AllocationStats<char>::allocations = 0;
  AllocationStats<char>::deallocations = 0;
  AllocationStats<char>::largest_request = 0;

  char input[128];
  for (size_t i = 0; i < sizeof(input); ++i)
    input[i] = 'x';

  LimitedString zero_probe{LimitedAllocator<char>{0}};
  const size_t sso_capacity = zero_probe.capacity();
  CHECK(zero_probe.max_size() >= sso_capacity);
  LimitedString short_zero{input, sso_capacity, LimitedAllocator<char>{0}};
  CHECK(short_zero.size() == sso_capacity);
  CHECK(AllocationStats<char>::allocations == 0);

  bool rejected = false;
  try {
    LimitedString too_long{input, sso_capacity + 1, LimitedAllocator<char>{0}};
    (void)too_long;
  } catch (const std::length_error&) {
    rejected = true;
  } catch (...) {
    return fail("SSO overflow must throw length_error before allocation", __LINE__);
  }
  CHECK(rejected);
  CHECK(AllocationStats<char>::allocations == 0);

  LimitedString heap_probe{LimitedAllocator<char>{32}};
  const size_t heap_limit = heap_probe.max_size();
  CHECK(heap_limit > sso_capacity);
  CHECK(heap_limit <= 32);
  LimitedString heap_value{input, heap_limit, LimitedAllocator<char>{32}};
  CHECK(heap_value.size() == heap_limit);
  CHECK(AllocationStats<char>::allocations == 1);
  CHECK(AllocationStats<char>::largest_request > 0);
  CHECK(AllocationStats<char>::largest_request <= 32);
  return 0;
}

struct SmallFunctor {
  int value;
  int operator()() const noexcept { return value; }
};
struct LargeFunctor {
  char padding[96];
  int value;
  int operator()() const noexcept { return value; }
};
struct alignas(64) OverAlignedFunctor {
  int value;
  int operator()() const noexcept { return value; }
};
struct ThrowingCopyFunctor {
  static bool throw_on_copy;
  int value;
  explicit ThrowingCopyFunctor(int v) noexcept : value(v) {}
  ThrowingCopyFunctor(const ThrowingCopyFunctor& other) noexcept(false) : value(other.value) {
    if (throw_on_copy)
      throw 17;
  }
  ThrowingCopyFunctor(ThrowingCopyFunctor&&) noexcept = default;
  int operator()() const noexcept { return value; }
};
bool ThrowingCopyFunctor::throw_on_copy = false;

template <class Functor>
static int test_function_copy_move_swap(const Functor& functor, int expected) {
  std::function<int()> first = functor;
  CHECK(first() == expected);
  std::function<int()> copied = first;
  CHECK(copied() == expected);
  std::function<int()> moved = std::move(copied);
  CHECK(!copied);
  CHECK(moved() == expected);
  first.swap(moved);
  CHECK(first() == expected);
  CHECK(moved() == expected);
  return 0;
}

static int test_function_paths() {
  SmallFunctor small{1};
  LargeFunctor large{};
  large.value = 2;
  OverAlignedFunctor over_aligned{3};
  ThrowingCopyFunctor throwing{4};

  CHECK(test_function_copy_move_swap(small, 1) == 0);
  CHECK(test_function_copy_move_swap(large, 2) == 0);
  CHECK(test_function_copy_move_swap(over_aligned, 3) == 0);
  CHECK(test_function_copy_move_swap(throwing, 4) == 0);

  std::function<int()> inline_value = SmallFunctor{5};
  std::function<int()> heap_value = large;
  heap_value.swap(inline_value);
  CHECK(heap_value() == 5);
  CHECK(inline_value() == 2);

  std::function<int()> throwing_value = throwing;
  ThrowingCopyFunctor::throw_on_copy = true;
  bool copy_threw = false;
  try {
    std::function<int()> failed_copy = throwing_value;
    (void)failed_copy;
  } catch (int value) {
    copy_threw = value == 17;
  }
  ThrowingCopyFunctor::throw_on_copy = false;
  CHECK(copy_threw);
  CHECK(throwing_value() == 4);
  std::function<int()> after_throw = throwing_value;
  CHECK(after_throw() == 4);
  return 0;
}

int main() {
  for (int i = 0; i < 128; ++i) {
    CHECK(test_string_boundaries() == 0);
    CHECK(test_function_paths() == 0);
  }
  CHECK(AllocationStats<char>::allocations == AllocationStats<char>::deallocations);
  return 0;
}
