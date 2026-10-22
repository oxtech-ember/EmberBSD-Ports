// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted E12 libc++ compatibility regression).
#include <functional>
#include <new>
#include <type_traits>
#include <utility>

struct SmallTarget {
  int value;
  void operator()() const noexcept {}
};

struct LargeTarget {
  char bytes[72];
  void operator()() const noexcept {}
};

struct OverAlignedTarget {
  alignas(32) char bytes[32];
  void operator()() const noexcept {}
};

struct ThrowingCopyTarget {
  ThrowingCopyTarget() noexcept = default;
  ThrowingCopyTarget(const ThrowingCopyTarget&) noexcept(false) {}
  void operator()() const noexcept {}
};

struct MemberTarget {
  void call() const noexcept {}
};

static_assert(sizeof(SmallTarget) <= 3 * sizeof(void*), "small target fixture");
static_assert(sizeof(void*) == 8, "NetBSD/aarch64 target fixture");
static_assert(sizeof(LargeTarget) + sizeof(void*) == 80,
              "large target plus function vptr fixture");
static_assert(alignof(OverAlignedTarget) == 32, "over-aligned target fixture");
static_assert(!std::is_nothrow_copy_constructible<ThrowingCopyTarget>::value,
              "throwing-copy target fixture");

void exercise_function_paths() {
  std::function<void()> small = SmallTarget{1};
  std::function<void()> small_copy = small;
  std::function<void()> small_move = std::move(small_copy);
  small.swap(small_move);

  std::function<void()> large = LargeTarget{};
  std::function<void()> large_copy = large;
  std::function<void()> large_move = std::move(large_copy);
  large.swap(large_move);

  std::function<void()> aligned = OverAlignedTarget{};
  std::function<void()> aligned_copy = aligned;
  aligned.swap(aligned_copy);

  std::function<void()> throwing = ThrowingCopyTarget{};
  std::function<void()> throwing_copy = throwing;
  throwing.swap(throwing_copy);

  MemberTarget member;
  std::function<void()> bound = std::bind(&MemberTarget::call, &member);
  std::function<void()> bound_copy = bound;
  bound.swap(bound_copy);

  small();
  large();
  aligned();
  throwing();
  bound();
}
