# Identifier linkage check

Compile the producer and consumer as separate translation units with the
production GCC16 target flags and the selected source/header overlay.
Keep `-Werror=subobject-linkage` enabled.
The baseline must fail on the namespace identifier declaration.
The patched producer and consumer must compile and link.
Run the executable on the target; it must exit with status zero.
Compile `identifier-linkage-denied.cc` separately; it must fail its PassKey
constraint. The ordinary source must not depend on this negative input.

The check covers namespace, nested-class, and anonymous-namespace identifier
types, one-pointer size and alignment, constexpr identity and names, strong
typing, allowed access, cross-translation-unit values and name addresses,
and denied access. Production UI translation units and upstream unit tests
remain separate acceptance checks.
