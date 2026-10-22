# Source provenance

This recipe pins the generated PCI ID snapshot at version `2026.10.22` to
upstream commit `86e7077e4b7947be28d4de891c69f7ae64da0286`. The immutable
GitHub source archive has SHA256
`0935bb070fcb0a199e0a918e977e233e57a463f0e518733f3377bee8ab120f72`.

The [PCI ID Repository](https://pci-ids.ucw.cz/) generates daily snapshots and
allows distribution under GPL version 2 or later or the 3-clause BSD license.
The [pciutils/pciids repository](https://github.com/pciutils/pciids) records
these generated snapshots. This package installs the upstream `pci.ids` file
without editing its data. `files/SOURCE` records the source notice next to the
recipe.
