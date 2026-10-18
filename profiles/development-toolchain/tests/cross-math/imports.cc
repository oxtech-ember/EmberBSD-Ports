// SPDX-License-Identifier: BSD-2-Clause
// Independent required C++ math imports. Keep every relocation for link checks.
#if defined(MATH_STD_MODULE)
import std;
#elif defined(MATH_COMPAT_MODULE)
import std.compat;
#else
#include <cmath>
#endif
#ifdef GLOBAL_MATH_NAMES
#define MATH_NAME(n) ::n
#else
#define MATH_NAME(n) std::n
#endif

auto address_acosf = &MATH_NAME(acosf);
auto address_acosl = &MATH_NAME(acosl);
auto address_asinf = &MATH_NAME(asinf);
auto address_asinl = &MATH_NAME(asinl);
auto address_atan2f = &MATH_NAME(atan2f);
auto address_atan2l = &MATH_NAME(atan2l);
auto address_atanf = &MATH_NAME(atanf);
auto address_atanl = &MATH_NAME(atanl);
auto address_ceilf = &MATH_NAME(ceilf);
auto address_ceill = &MATH_NAME(ceill);
auto address_cosf = &MATH_NAME(cosf);
auto address_coshf = &MATH_NAME(coshf);
auto address_coshl = &MATH_NAME(coshl);
auto address_cosl = &MATH_NAME(cosl);
auto address_expf = &MATH_NAME(expf);
auto address_expl = &MATH_NAME(expl);
auto address_fabsf = &MATH_NAME(fabsf);
auto address_fabsl = &MATH_NAME(fabsl);
auto address_floorf = &MATH_NAME(floorf);
auto address_floorl = &MATH_NAME(floorl);
auto address_fmodf = &MATH_NAME(fmodf);
auto address_fmodl = &MATH_NAME(fmodl);
auto address_frexpl = &MATH_NAME(frexpl);
auto address_ldexpf = &MATH_NAME(ldexpf);
auto address_ldexpl = &MATH_NAME(ldexpl);
auto address_log10f = &MATH_NAME(log10f);
auto address_log10l = &MATH_NAME(log10l);
auto address_logf = &MATH_NAME(logf);
auto address_logl = &MATH_NAME(logl);
auto address_modff = &MATH_NAME(modff);
auto address_modfl = &MATH_NAME(modfl);
auto address_powf = &MATH_NAME(powf);
auto address_powl = &MATH_NAME(powl);
auto address_sinf = &MATH_NAME(sinf);
auto address_sinhf = &MATH_NAME(sinhf);
auto address_sinhl = &MATH_NAME(sinhl);
auto address_sinl = &MATH_NAME(sinl);
auto address_sqrtf = &MATH_NAME(sqrtf);
auto address_sqrtl = &MATH_NAME(sqrtl);
auto address_tanf = &MATH_NAME(tanf);
auto address_tanhf = &MATH_NAME(tanhf);
auto address_tanhl = &MATH_NAME(tanhl);
auto address_tanl = &MATH_NAME(tanl);

int main() { return 0; }
