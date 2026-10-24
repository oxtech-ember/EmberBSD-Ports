// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted GCC16 enum-validator regression).
#include "mojo/public/cpp/bindings/lib/validate_params.h"
constexpr const auto& invalid =
    mojo::internal::GetArrayOfEnumsValidator<0, false, nullptr>();
