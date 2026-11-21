# Source provenance

This recipe pins the generated PCI ID snapshot at version `2026.11.21` to
upstream commit `bc2920f3fc38e42d0aecc8ce4b17d1ed034dbd70`. The immutable
GitHub source archive has SHA256
`78b062cdc25ca7dca9953a510dc582d1697fa71e76d2a7aa839ad571f849e098`.

The [PCI ID Repository](https://pci-ids.ucw.cz/) generates daily snapshots and
allows distribution under GPL version 2 or later or the 3-clause BSD license.
The [pciutils/pciids repository](https://github.com/pciutils/pciids) records
these generated snapshots. This package installs the upstream `pci.ids` file
without editing its data. `files/SOURCE` records the source notice next to the
recipe.
