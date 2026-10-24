# Event and Lottie GCC16 checks

The AI-assisted patch adds three fatal exits after exhaustive switches in
event string formatting and Lottie progress. All strings and all six animation
states keep their existing results, timer checks and nullopt behavior.
The Lottie source includes its direct `base/notreached.h` dependency.

The non-default pre-target-handler insertion uses `emplace(begin, prioritized)`.
`prioritized` is the same local lvalue, so emplace uses the same implicit copy
constructor. It contains a non-owning pointer and a priority enum. It has no
ownership or destructor side effect and cannot alias the vector's storage.
Default handlers still append. Other handlers still insert at the beginning.
The later stable sort and across-target priority ordering are unchanged.
This avoids the const-reference insertion path's impossible local-pointer alias
adjustment diagnosed by GCC16, without changing compiler diagnostic flags.

Replay the complete production GCC16 commands for `ui/events/event.cc`,
`ui/events/event_target.cc` and `ui/lottie/animation.cc`. All three baselines
fail and all three patched inputs compile. All six paired Clang Static Analyzer
commands complete with unchanged signatures: two inherited findings in events,
none in event_target, and three in animation. All six Cppcheck inputs stop at
unchanged dependency parser errors; this is incomplete analysis.

Existing EventTarget addition/removal, simple/complex/across-target ordering and
Lottie progress/state tests were inspected. They were not executed. These
source, compile and analysis checks do not establish UI or browser acceptance.
