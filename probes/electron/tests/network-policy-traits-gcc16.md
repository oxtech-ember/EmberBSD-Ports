# Network policy and traits GCC16 checks

The AI-assisted patch adds 28 fatal exits after exhaustive switches in ten
production translation units and one companion header. CSP, Permissions Policy,
client hint delegation, COEP, DIP, COOP, CORS, cookie and outbound DNS mappings
retain their existing cases, sentinels and fallback branches. No compiler
diagnostic or `EnumTraits::FromMojom` function changes.

The two local inbound DNS helpers preserve the closed Tristate and optional
secure-mode vocabulary. Their schema has no `Extensible` annotation. Actual
generated enum headers set `kIsExtensible=false` and reject unknown integers.
The production struct generator validates enum fields; incoming dispatch and
manual deserialization validate the payload before native conversion. The
recorded source proof uses the exact schema, generated enum headers, generator
and dispatch sources. It does not claim inspection of a generated struct
implementation absent from the immutable input set.

The device-session event union reader gains a final `return false`. Its four
valid alternatives keep their existing reads and assignments. A direct reader
call with an unknown tag now fails without changing the output. The closed
union wire validator already rejects unknown tags. Two outbound conversions
in the companion header gain fatal terminals. That header's generated owner
already publicly exports `//base`; no GN dependency change is required.

Replay all ten original production commands with the complete GCC16 target
configuration. All ten baselines fail and all ten patched commands compile.
The final companion-header consumer and device-session unit test also change
from failure to success. The expanded host-resolver unit compiles on both sides.
Three new upstream tests cover two unknown union tags and four invalid DNS enum
values. They compile with the bundled GTest configurations. Their linked suites
have not run; runtime wire rejection remains unverified.

All 28 paired Clang Static Analyzer calls complete with unchanged signatures.
Inherited forwarding-reference diagnostics and one generated-header dead store
remain. All 28 Cppcheck inputs stop at the same dependency parser error; this
is incomplete analysis.

The [small generated-vocabulary fixture](dns-closed-enums.cc) uses actual
production generated enum headers. Compile and link it with the host-resolver
production target configuration and common GCC16 runtime. It checks thirteen
independent integer expectations and four typed/closed-enum static assertions.
Its GCC16 AMD64 executable passes on physical NetBSD 11. This fixture checks
the vocabulary; it does not execute complete wire deserialization or establish
Electron or Blanc acceptance.
