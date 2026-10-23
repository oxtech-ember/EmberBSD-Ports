// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// This input must fail: the type did not grant access to ForeignAccessor.

#include "identifier-linkage-fixture.h"

class ForeignAccessor {
 public:
  static ui::internal::UniqueIdentifier GetIdentifier(
      identifier_linkage_test::NamespaceIdentifier value) {
    return value.GetIdentifier(base::PassKey<ForeignAccessor>());
  }
};
