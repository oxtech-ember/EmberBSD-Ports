# Shared dprint-node

This package builds the Node N-API formatter from the upstream dprint-node
source at `f21bd38ae8e3239ffe07c941c938349eebdb2c5e`. The matching
TypeScript formatter source is selected at
`98525274ee276fb61709c77f791b212a48c59dd6`. Its SWC view is updated through
the common Cargo patch registry, and the formatter consumer patch retains the
real borrowed function-body and accessor data. The build uses the selected
Ports Rust, C compiler and Node runtime. It does not install npm prebuilt
addons or invoke npm install.

The package smoke test checks source-preserving formatting, comments,
accessor recovery, JSX, repeated formatting and N-API numeric conversion.
Run the same test with the target Node on cross-built packages; a host test is
not target execution.
