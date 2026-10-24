# Mojo enum validator regression

Compile these inputs with the pinned Chromium production GCC16 target flags.
Keep the normal source, generated-header, and target-sysroot include paths.
Keep `-Werror=address` enabled.

`valid.cc` must fail on the baseline header and compile after the patch. Link
its object with the selected target runtime. Execute it on an ABI-matching
target; status zero checks the selected validator callback and its bounds.
The constexpr checks cover holder fields, nested-array identity, and the
function pointer.

Compile `null-factory.cc` and `null-holder.cc` separately. Both must fail on
the static assertion before and after the patch. Do not link these negative
inputs into the positive executable.

The header still rejects null validators. Explicit bool conversion only states
the intended compile-time predicate; it changes no storage or callback.
