// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// Origin: EmberBSD (AI-assisted).
#include <tcb/span.hpp>

int main()
{
    int values[] = {4, 8, 15, 16};
    tcb::span<int> view(values);
    if (view.size() != 4 || view.front() != 4 || view.back() != 16)
        return 1;
    auto middle = view.subspan(1, 2);
    middle[0] = 23;
    if (middle.size() != 2 || values[1] != 23 || middle[1] != 15)
        return 2;
    tcb::span<int> empty;
    return empty.empty() && empty.size() == 0 ? 0 : 3;
}
