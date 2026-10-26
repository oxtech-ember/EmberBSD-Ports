// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// Exercise the real GN template and its CoreFoundation traits in plain C++.
#include <cstdio>
#include <type_traits>
#include <utility>

#include "base/mac/scoped_cftyperef.h"

#if defined(GN_SCOPED_UNRETAINED) || defined(GN_SCOPED_NOT_RETAINED)
#error GN ownership annotation macros leaked outside their header
#endif

struct Reference {
  int count = 1;
};

struct Traits {
  static inline int retains = 0;
  static inline int releases = 0;
  static inline bool invalid = false;
  static Reference* InvalidValue() { return nullptr; }
  static Reference* Retain(Reference* object) {
    if (object->count <= 0) invalid = true;
    ++retains;
    ++object->count;
    return object;
  }
  static void Release(Reference* object) {
    if (object->count <= 0) invalid = true;
    ++releases;
    --object->count;
  }
};

#define EXPECT(value) do { if (!(value)) return __LINE__; } while (false)

int main() {
  using Ref = base::ScopedTypeRef<Reference*, Traits>;
  static_assert(std::is_same_v<Ref::element_type, Reference*>);
  Reference one, two, three;
  {
    Ref first(&one);
    EXPECT(first.get() == &one && one.count == 1 && Traits::retains == 0);
    Ref copied(first);
    EXPECT(one.count == 2 && Traits::retains == 1);
    Ref retained(&one, base::scoped_policy::RETAIN);
    EXPECT(one.count == 3 && Traits::retains == 2);
    Ref moved(std::move(retained));
    EXPECT(retained.get() == nullptr && moved == &one && one.count == 3);
    first = first;
    EXPECT(one.count == 3 && Traits::retains == 3 && Traits::releases == 1);
    copied.reset(&two, base::scoped_policy::RETAIN);
    EXPECT(one.count == 2 && two.count == 2);
    EXPECT(Traits::retains == 4 && Traits::releases == 2);
    Reference* raw = moved.release();
    EXPECT(raw == &one && moved.get() == nullptr && one.count == 2);
    EXPECT(Traits::releases == 2);
    Traits::Release(raw);
    Ref other(&two);
    first.swap(other);
    EXPECT(first == &two && other == &one && first != &one);
    EXPECT(static_cast<Reference*>(first) == &two);
    EXPECT(Traits::retains == 4 && Traits::releases == 3);
    first.reset();
    other.reset();
    copied.reset();
    EXPECT(one.count == 0 && two.count == 0);
    EXPECT(Traits::retains == 4 && Traits::releases == 6);
    Ref empty;
    Ref empty_copy(empty);
    EXPECT(empty_copy.get() == nullptr);
    Reference** out = empty.InitializeInto();
    *out = &three;
    EXPECT(empty.get() == &three && three.count == 1);
  }
  EXPECT(three.count == 0 && Traits::retains == 4 && Traits::releases == 7);
  EXPECT(!Traits::invalid);

  // Use the upstream CF specialization, not a replacement for CFRetain/CFRelease.
  base::ScopedCFTypeRef<CFStringRef> text(CFStringCreateWithCString(
      kCFAllocatorDefault, "g16", kCFStringEncodingUTF8));
  EXPECT(text.get() != nullptr);
  base::ScopedCFTypeRef<CFStringRef> copy(text);
  text.reset();
  EXPECT(CFGetTypeID(copy.get()) == CFStringGetTypeID());
  EXPECT(CFStringGetLength(copy.get()) == 3);
  char result[4] = {};
  EXPECT(CFStringGetCString(copy.get(), result, sizeof(result), kCFStringEncodingUTF8));
  EXPECT(result[0] == 'g' && result[1] == '1' && result[2] == '6' && result[3] == 0);
  CFStringRef transferred = copy.release();
  EXPECT(copy.get() == nullptr && CFStringGetLength(transferred) == 3);
  CFRelease(transferred);
  std::puts("gn-scoped-typeref: PASS");
  return 0;
}
