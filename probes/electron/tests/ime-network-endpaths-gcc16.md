# IME and network GCC16 end paths

The AI-assisted patch adds twelve fatal exits after exhaustive switches in
eight production translation units. It adds direct includes where required.
Every preexisting source line remains unchanged. No switch gains a default
label, so compiler checks for new enum members remain enabled.

IME action and mode mappings retain all named values. The inbound mode
conversion has a closed wire contract: the schema has no Extensible annotation,
the actual generated data sets `kIsExtensible=false`, and only values 0..8
validate. Generated mode reads use infallible native conversion. Incoming
dispatch and manual Deserialize validate the payload before conversion. The
neighboring inbound action and type converters already use fatal terminals.
No accepted unknown input becomes an abort. The source proof uses the exact
schema, actual generated enum headers, validation templates and dispatch code;
it does not claim inspection of an absent generated struct-validation body.
Five typed static assertions check this closed conversion contract.

The other terminals preserve outbound proxy results, DataElement cloning,
local-network result strings/errors, header matching, No-Vary-Search messages
and transport address-space selection. Existing unknown-value fallbacks remain.
The data-pipe terminal stays inside the original 64-bit branch; ChromeOS and
32-bit unconditional allocation choices remain unchanged.

All eight original GCC16 production inputs fail and all eight patched inputs
compile with unchanged target flags. All sixteen paired Clang Static Analyzer
calls complete with identical inherited findings. All sixteen Cppcheck inputs
stop at the same dependency parser limit; this is incomplete analysis.
No compiler diagnostics are disabled. Other architecture branches have source
review, not compilation. No target GTest, IME, network or browser runtime
acceptance is established by these focused checks.
