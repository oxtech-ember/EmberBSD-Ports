#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise semantic refresh of an owner-generated host buildlink candidate."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/host-buildlink.py'
spec = importlib.util.spec_from_file_location('host', owner)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp).resolve()
    source = root / 'pkgsrc'; (source / 'mk').mkdir(parents=True)
    license_file = source / 'mk/license.mk'; license_file.write_text('new license token\n')
    recipe = source / 'devel/provider/buildlink3.mk'; recipe.parent.mkdir(parents=True)
    recipe.write_text('same recipe')
    package = root / 'pkgdb/provider/+CONTENTS'; package.parent.mkdir(parents=True)
    package.write_text('provider-1\n')
    target = root / 'prefix/lib/provider'; target.parent.mkdir(parents=True); target.write_text('same')
    script = source / 'devel/electron44/files/host-buildlink.py'
    script.parent.mkdir(parents=True); script.write_text('new owner')
    works = [root / 'old', root / 'candidate']
    identities = []
    for work in works:
        view = work / 'objects/devel/electron-host-context/work/.buildlink'
        view.mkdir(parents=True)
        (view / 'provider').symlink_to(target)
        conf = work / 'make.conf'; conf.write_text(f'WRKOBJDIR= {work}/objects\nPACKAGES= {work}/packages\n')
        identities.append({'inputs': {str(p): digest(p) for p in (license_file, recipe, package, target, script, conf)},
                           'links': {'provider': str(target)}})
    invocations = [{'work': str(w), 'host_prefix': str(root / 'prefix')} for w in works]
    saved = {'identity': {**identities[0], 'inputs': dict(identities[0]['inputs'])}, 'invocation': invocations[0]}
    saved['identity']['inputs'][str(license_file)] = 'old-license-hash'
    before = (works[0] / 'make.conf').stat()
    result = host.refresh_selection(saved, identities[0], identities[1], invocations[0], invocations[1],
                                    works[0], works[1], source, script)
    assert result['identity'] == identities[0]
    # An exported recipe can replace a symlink to the same old owner tree.
    old_root = root / 'old-export'
    old_script = old_root / 'devel/electron44/files/host-buildlink.py'
    old_script.parent.mkdir(parents=True); old_script.write_bytes(script.read_bytes())
    old_recipe = old_root / 'devel/provider/buildlink3.mk'; old_recipe.parent.mkdir(parents=True)
    old_recipe.write_bytes(recipe.read_bytes())
    moved = {'identity': {**saved['identity'], 'inputs': dict(saved['identity']['inputs'])},
             'invocation': saved['invocation']}
    moved['identity']['inputs'][str(old_script)] = moved['identity']['inputs'].pop(str(script))
    moved['identity']['inputs'][str(old_recipe)] = moved['identity']['inputs'].pop(str(recipe))
    host.refresh_selection(moved, identities[0], identities[1], invocations[0], invocations[1],
                           works[0], works[1], source, script)
    moved['identity']['inputs'][str(recipe)] = moved['identity']['inputs'][str(old_recipe)]
    host.refresh_selection(moved, identities[0], identities[1], invocations[0], invocations[1],
                           works[0], works[1], source, script)
    for bad in ('recipe', 'collision', 'foreign'):
        broken = {'identity': {**moved['identity'], 'inputs': dict(moved['identity']['inputs'])},
                  'invocation': moved['invocation']}
        if bad == 'recipe':
            broken['identity']['inputs'][str(old_recipe)] = 'changed-recipe'
        elif bad == 'collision':
            broken['identity']['inputs'][str(recipe)] = 'different-collision'
        else:
            broken['identity']['inputs'][str(old_script) + '.foreign'] = broken['identity']['inputs'].pop(str(old_script))
        try:
            host.refresh_selection(broken, identities[0], identities[1], invocations[0], invocations[1],
                                   works[0], works[1], source, script)
        except ValueError:
            pass
        else:
            raise AssertionError('accepted changed ' + bad)
    # Production may still execute the owner from its checkout, while recipes
    # previously resolved there have moved into the physical shared export.
    live_script = root / 'active-owner/devel/electron44/files/host-buildlink.py'
    live_script.parent.mkdir(parents=True); live_script.write_bytes(script.read_bytes())
    live = []
    for identity in identities:
        item = {**identity, 'inputs': dict(identity['inputs'])}
        item['inputs'][str(live_script)] = item['inputs'].pop(str(script))
        live.append(item)
    host.refresh_selection(moved, live[0], live[1], invocations[0], invocations[1],
                           works[0], works[1], source, live_script)
    # An older work tree may retain a link into its original owner checkout
    # even after the executing owner moved to the selected export.
    old_make = old_script.parent / 'host-buildlink/Makefile'
    old_make.parent.mkdir(parents=True, exist_ok=True)
    old_make.write_text('same host consumer')
    selected_make = script.parent / 'host-buildlink/Makefile'
    selected_make.parent.mkdir(parents=True, exist_ok=True)
    selected_make.write_bytes(old_make.read_bytes())
    saved_mixed = {**moved, 'identity': {**moved['identity'], 'inputs': dict(moved['identity']['inputs'])}}
    saved_mixed['identity']['inputs'][str(old_make)] = digest(old_make)
    current_mixed = {**live[0], 'inputs': dict(live[0]['inputs'])}
    current_mixed['inputs'][str(old_make)] = digest(old_make)
    candidate_mixed = {**live[1], 'inputs': dict(live[1]['inputs'])}
    candidate_mixed['inputs'][str(selected_make)] = digest(selected_make)
    host.refresh_selection(saved_mixed, current_mixed, candidate_mixed,
                           invocations[0], invocations[1], works[0], works[1], source, live_script)
    # The recorded owner script is already in the export, but the old
    # generated consumer still resolves its Makefile in a different checkout.
    # This is independent from the older owner-script relocation above.
    for work, makefile in zip(works, (old_make, selected_make)):
        consumer = work / 'pkgsrc/devel/electron-host-context'
        consumer.mkdir(parents=True)
        (consumer / 'Makefile').symlink_to(makefile)
        assert (consumer / 'Makefile').resolve(strict=True) == makefile.resolve(strict=True)
    split_saved = {'identity': {**identities[0], 'inputs': dict(identities[0]['inputs'])},
                   'invocation': invocations[0]}
    split_saved['identity']['inputs'][str(old_make)] = digest(old_make)
    split_current = {**identities[0], 'inputs': dict(identities[0]['inputs'])}
    split_current['inputs'][str(old_make)] = digest(old_make)
    split_candidate = {**identities[1], 'inputs': dict(identities[1]['inputs'])}
    split_candidate['inputs'][str(selected_make)] = digest(selected_make)
    host.refresh_selection(split_saved, split_current, split_candidate,
                           invocations[0], invocations[1], works[0], works[1], source, script)
    for name in ('old-consumer', 'candidate-consumer', 'selected-artifact'):
        changed_current = {**split_current, 'inputs': dict(split_current['inputs'])}
        changed_candidate = {**split_candidate, 'inputs': dict(split_candidate['inputs'])}
        if name == 'old-consumer':
            changed_current['inputs'][str(old_make)] = 'different-old-consumer'
        elif name == 'candidate-consumer':
            changed_candidate['inputs'][str(selected_make)] = 'different-candidate-consumer'
        else:
            changed_current['inputs'][str(target)] = 'different-selected-artifact'
        try:
            host.refresh_selection(split_saved, changed_current, changed_candidate,
                                   invocations[0], invocations[1], works[0], works[1], source, script)
        except ValueError:
            pass
        else:
            raise AssertionError('accepted changed ' + name)
    # Equal bytes are insufficient if the candidate consumer resolves to an
    # unrelated file rather than the selected owner's declared Makefile.
    foreign_make = root / 'foreign/Makefile'
    foreign_make.parent.mkdir()
    foreign_make.write_bytes(selected_make.read_bytes())
    candidate_link = works[1] / 'pkgsrc/devel/electron-host-context/Makefile'
    foreign_candidate = {**split_candidate, 'inputs': dict(split_candidate['inputs'])}
    foreign_candidate['inputs'].pop(str(selected_make))
    foreign_candidate['inputs'][str(foreign_make)] = digest(foreign_make)
    candidate_link.unlink()
    candidate_link.symlink_to(foreign_make)
    try:
        try:
            host.refresh_selection(split_saved, split_current, foreign_candidate,
                                   invocations[0], invocations[1], works[0], works[1], source, script)
        except ValueError:
            pass
        else:
            raise AssertionError('accepted foreign candidate consumer with identical bytes')
    finally:
        candidate_link.unlink()
        candidate_link.symlink_to(selected_make)
    after = (works[0] / 'make.conf').stat()
    assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)
    changed = {**identities[0], 'inputs': dict(identities[0]['inputs'])}
    changed['inputs'][str(package)] = 'different-package-hash'
    try:
        host.refresh_selection(saved, changed, identities[1], invocations[0], invocations[1],
                               works[0], works[1], source, script)
    except ValueError:
        pass
    else:
        raise AssertionError('accepted changed selected package')
    for broken in ('binding', 'link'):
        candidate = {**identities[1], 'inputs': dict(identities[1]['inputs']), 'links': dict(identities[1]['links'])}
        candidate_invocation = dict(invocations[1])
        if broken == 'binding':
            candidate_invocation['host_prefix'] = str(root / 'other-prefix')
        else:
            candidate['links']['provider'] = str(root / 'other-target')
        try:
            host.refresh_selection(saved, identities[0], candidate, invocations[0], candidate_invocation,
                                   works[0], works[1], source, script)
        except ValueError:
            pass
        else:
            raise AssertionError('accepted changed ' + broken)
print('PASS: license-only refresh and changed provider/binding/link rejection')
