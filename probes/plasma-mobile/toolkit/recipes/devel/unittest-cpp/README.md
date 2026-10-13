# UnitTest++ 2.0.0

Version 2.0.0 remains the latest official release as checked on 2026-10-13:
<https://github.com/unittest-cpp/unittest-cpp/releases/tag/v2.0.0>.
It is the upstream test dependency of current Enchant.

The recipe derives from pkgsrc fff4deb639a1a640476203c80f752fb77b6cb14b.
Keep the MIT license and pkgsrc's portable-shell configure patch.
The upstream `check` target remains. A cross build needs target execution
for runtime acceptance; do not report cross compilation as a test pass.
