// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.

#ifndef IDENTIFIER_LINKAGE_FIXTURE_H_
#define IDENTIFIER_LINKAGE_FIXTURE_H_

#include <concepts>
#include <string_view>
#include <type_traits>

#include "ui/base/identifier/unique_identifier.h"

namespace identifier_linkage_test {

class Accessor {
 public:
  template <typename T>
  static ui::internal::UniqueIdentifier GetIdentifier(T value) {
    return value.GetIdentifier(base::PassKey<Accessor>());
  }
};

DECLARE_UNIQUE_IDENTIFIER_TYPE(NamespaceIdentifier, Accessor);

class Container {
 public:
  DECLARE_UNIQUE_IDENTIFIER_TYPE(NestedIdentifier, Accessor);
};

DECLARE_UNIQUE_IDENTIFIER_VALUE(NamespaceIdentifier, kNamespaceValue);
DECLARE_UNIQUE_IDENTIFIER_VALUE(Container::NestedIdentifier, kNestedValue);

template <typename T, const char* N, typename... F>
constexpr const char* ClassNameAddress(
    const ui::internal::UniqueIdentifierImpl<T, N, F...>&) {
  return N;
}

static_assert(sizeof(NamespaceIdentifier) == sizeof(void*));
static_assert(alignof(NamespaceIdentifier) == alignof(void*));
static_assert(sizeof(Container::NestedIdentifier) == sizeof(void*));
static_assert(alignof(Container::NestedIdentifier) == alignof(void*));
static_assert(std::is_trivially_copyable_v<NamespaceIdentifier>);
static_assert(ui::internal::IsUniqueIdentifierImpl<NamespaceIdentifier>);
static_assert(ui::internal::IsUniqueIdentifierImpl<Container::NestedIdentifier>);
static_assert(!std::same_as<NamespaceIdentifier, Container::NestedIdentifier>);
static_assert(!NamespaceIdentifier());
static_assert(kNamespaceValue == kNamespaceValue);
static_assert(std::string_view(ClassNameAddress(kNamespaceValue)) ==
              "NamespaceIdentifier");
static_assert(std::string_view(ClassNameAddress(kNestedValue)) ==
              "NestedIdentifier");

NamespaceIdentifier NamespaceValueFromOtherTranslationUnit();
Container::NestedIdentifier NestedValueFromOtherTranslationUnit();
const char* NamespaceNameFromOtherTranslationUnit();
const char* NestedNameFromOtherTranslationUnit();

}  // namespace identifier_linkage_test

#endif  // IDENTIFIER_LINKAGE_FIXTURE_H_
