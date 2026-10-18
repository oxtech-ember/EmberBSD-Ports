// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), system Imath half conversion contract.
// The command selects either the original or system half header with -include.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>

int
main()
{
	for (unsigned bits = 0; bits < 65536; ++bits) {
		half value;
		value.setBits(static_cast<unsigned short>(bits));
		const float actual = value;
		const unsigned sign = bits >> 15;
		const unsigned exponent = (bits >> 10) & 31;
		const unsigned fraction = bits & 1023;
		if (exponent == 31) {
			if (fraction != 0) {
				if (!std::isnan(actual))
					return 1;
			} else if (!std::isinf(actual) ||
			    std::signbit(actual) != static_cast<bool>(sign)) {
				return 2;
			}
			continue;
		}
		float expected = exponent == 0 ? std::ldexp(float(fraction), -24) :
		    std::ldexp(float(1024 + fraction), int(exponent) - 25);
		if (sign != 0)
			expected = -expected;
		if (actual != expected || std::signbit(actual) != std::signbit(expected))
			return 3;
		const half roundtrip(actual);
		if (roundtrip.bits() != bits)
			return 4;
	}
	std::puts("PASS: all 65536 half encodings and finite round trips");
	return 0;
}
