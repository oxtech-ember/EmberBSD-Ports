# Topology regression

Compile `topology.cpp` with the selected C++20 toolchain, this provider's
headers, and the common hwloc library. Run with no argument for the real
topology, and with `pu:4` and `core:2 pu:2` for the synthetic topologies.
The synthetic cases require four PUs and respectively four or two cores; the
real case requires at least one usable PU. No hardware configuration is changed.
