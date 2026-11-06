# KiCad document models

This is the common KiUtils 1.4.8 provider, with no runtime dependency beyond
Python. The schematic junction patch preserves both diameter and color through
the public parse/serialize API; the focused regression also covers either field
order and the default zero diameter.

The released parser reads the wires, junctions, labels, symbol transforms,
embedded library pins and project instance paths used by KiCad 10.0.8 samples.
It is not a lossless KiCad 10 document editor: newer `rule_area`, `table`, `group`
and embedded-font data are not represented by this release. Consumers must
report unsupported data rather than treating an incomplete view as a complete
design or serializing it over the original. Electrical nets and ERC should come
from KiCad's own exporter/checker, not a second resolver based on this model.

The source and GPL-3.0 license are from
[KiUtils](https://github.com/mvnmgrx/kiutils). Use the ordinary Ports test target
for the focused pure-Python regression; it does not prove a full schematic
analysis workflow or target package installation.
