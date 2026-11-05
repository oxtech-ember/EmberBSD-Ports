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
    root = Path(temp)
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
