// Copyright (c) 2026 EmberBSD contributors
// SPDX-License-Identifier: BSD-2-Clause
#if __has_feature(cxx_rvalue_references)
int feature_probe = 1;
#else
#error target Clang must report C++ rvalue-reference support
#endif
