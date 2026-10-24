// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted GCC16 enum-validator regression).
#include "mojo/public/cpp/bindings/lib/validate_params.h"
namespace {
bool Validate(int32_t value, mojo::internal::ValidationContext*) {
  return value >= 0 && value <= 2;
}
constexpr const auto& params =
    mojo::internal::GetArrayOfEnumsValidator<3, false, Validate>();
static_assert(params.expected_num_elements == 3);
static_assert(!params.element_is_nullable);
static_assert(params.validate_enum_func == Validate);
static_assert(params.key_validate_params == nullptr);
static_assert(params.element_validate_params == nullptr);
constexpr const auto& nested = mojo::internal::GetArrayValidator<
    0, true, &mojo::internal::GetArrayOfEnumsValidator<3, false, Validate>()>();
static_assert(nested.element_validate_params == &params);
}
int main() {
  return params.validate_enum_func(0, nullptr) &&
                 params.validate_enum_func(2, nullptr) &&
                 !params.validate_enum_func(-1, nullptr) &&
                 !params.validate_enum_func(3, nullptr)
             ? 0
             : 1;
}
