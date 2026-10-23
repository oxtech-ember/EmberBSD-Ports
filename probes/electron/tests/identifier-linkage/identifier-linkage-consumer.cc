// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.

#include "identifier-linkage-fixture.h"

namespace {

DECLARE_UNIQUE_IDENTIFIER_TYPE(LocalIdentifier);
DEFINE_LOCAL_UNIQUE_IDENTIFIER_VALUE(LocalIdentifier, kLocalValue);
static_assert(kLocalValue);

}  // namespace

int main() {
  using namespace identifier_linkage_test;
  if (NamespaceIdentifier() || !kNamespaceValue || !kNestedValue) {
    return 1;
  }
  if (NamespaceValueFromOtherTranslationUnit() != kNamespaceValue ||
      NestedValueFromOtherTranslationUnit() != kNestedValue) {
    return 2;
  }
  if (NamespaceNameFromOtherTranslationUnit() != ClassNameAddress(kNamespaceValue) ||
      NestedNameFromOtherTranslationUnit() != ClassNameAddress(kNestedValue)) {
    return 3;
  }
  if (!Accessor::GetIdentifier(kNamespaceValue) ||
      !Accessor::GetIdentifier(kNestedValue)) {
    return 4;
  }
  return 0;
}
