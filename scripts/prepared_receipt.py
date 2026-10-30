# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Write an SDK prepared-tree receipt, measuring the tree only once.

The source owners wrote the receipt, which hashes the whole prepared tree,
and then validated it at once, which hashed the tree again. The receipt
already holds the digest just measured, so the owners now check the written
receipt against the returned record. Import this module only after the
owner has selected its SDK.
"""
from pathlib import Path


def write(root, *, package, identity):
    """Write the receipt for ROOT and return the SDK record."""
    from emberbsd_sdk import jsonio, sourceprep
    from emberbsd_sdk.errors import SDKError
    record = sourceprep.write_prepared_tree_receipt(root, package=package, identity=identity)
    receipt = Path(root) / sourceprep.PREPARED_TREE_RECEIPT
    if receipt.read_bytes() != jsonio.json_bytes(record):
        raise SDKError('prepared source receipt differs from the measured record')
    return record
