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
import re


def write(root, *, package, identity, previous_root=None):
    """Write the receipt for ROOT and return the SDK record."""
    from emberbsd_sdk import jsonio, sourceprep
    from emberbsd_sdk.errors import SDKError
    if previous_root is None:
        record = sourceprep.write_prepared_tree_receipt(root, package=package, identity=identity)
    else:
        if getattr(sourceprep, 'PREPARED_TREE_REUSE_API', None) != 1:
            raise SDKError('selected SDK lacks prepared tree reuse API')
        record = sourceprep.write_prepared_tree_receipt(
            root, package=package, identity=identity, previous_root=previous_root)
    receipt = Path(root) / sourceprep.PREPARED_TREE_RECEIPT
    if receipt.read_bytes() != jsonio.json_bytes(record):
        raise SDKError('prepared source receipt differs from the measured record')
    return record


def refresh(root, *, identity, verify):
    """Rebind a verified payload while the caller holds exclusive use of it."""
    from emberbsd_sdk import jsonio, sourceprep
    from emberbsd_sdk.errors import SDKError
    before = identity()
    record = verify()
    if before != identity():
        raise SDKError('pkgsrc inputs changed during refresh')
    receipt = Path(root) / sourceprep.PREPARED_TREE_RECEIPT
    if jsonio.read_json(str(receipt)) != record:
        raise SDKError('prepared source receipt changed during refresh')
    updated = dict(record, identity={'effective': before[1], 'owner_sha256': before[0]['owner_sha256']})
    jsonio.write_json(str(receipt), updated, exclusive=False)
    return updated


def require_current_identity(identity, package):
    """Reject retired receipts; derived source trees can be prepared again."""
    from emberbsd_sdk.errors import SDKError
    if not isinstance(identity, dict) or set(identity) != {'effective', 'owner_sha256'}:
        raise SDKError('retired prepared-source identity; prepare the source again')
    effective = identity['effective']
    if (not isinstance(effective, dict) or
            set(effective) != {'api', 'package', 'effective_package_sha256', 'upstream'} or
            type(effective['api']) is not int or effective['api'] != 3 or
            effective['package'] != package or
            not isinstance(effective['effective_package_sha256'], str) or
            not re.fullmatch('[0-9a-f]{64}', effective['effective_package_sha256']) or
            not isinstance(effective['upstream'], str) or
            not re.fullmatch('[0-9a-f]{40}', effective['upstream']) or
            not isinstance(identity['owner_sha256'], str) or
            not re.fullmatch('[0-9a-f]{64}', identity['owner_sha256'])):
        raise SDKError('retired or invalid prepared-source identity; prepare the source again')
