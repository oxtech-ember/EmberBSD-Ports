// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.

#include "identifier-linkage-fixture.h"

namespace identifier_linkage_test {

DEFINE_UNIQUE_IDENTIFIER_VALUE(NamespaceIdentifier, kNamespaceValue);
DEFINE_UNIQUE_IDENTIFIER_VALUE(Container::NestedIdentifier, kNestedValue);

NamespaceIdentifier NamespaceValueFromOtherTranslationUnit() {
  return kNamespaceValue;
}

Container::NestedIdentifier NestedValueFromOtherTranslationUnit() {
  return kNestedValue;
}

const char* NamespaceNameFromOtherTranslationUnit() {
  return ClassNameAddress(kNamespaceValue);
}

const char* NestedNameFromOtherTranslationUnit() {
  return ClassNameAddress(kNestedValue);
}

}  // namespace identifier_linkage_test
