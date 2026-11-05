#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""A provider addition may relocate the view without replacing existing links."""
import importlib.util
import json
from pathlib import Path
import tempfile

path = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron', path)
controller = importlib.util.module_from_spec(spec); spec.loader.exec_module(controller)
key = 'emberbsd_protobuf_native_prefix'
envkey = 'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'
with tempfile.TemporaryDirectory(prefix='electron-buildlink-relocation-') as temporary:
    work = Path(temporary).resolve()
    target = work / 'protobuf.h'; target.write_text('same selected provider')
    extra = work / 'jpeg.h'; extra.write_text('additional provider')
    calls, arguments, environments = [], [], []
    for index in range(2):
        context = work / ('host-buildlink-' + str(index))
        prefix = context / 'objects/devel/electron-host-context/work/.buildlink'
        (prefix / 'include').mkdir(parents=True)
        (prefix / 'include/protobuf.h').symlink_to(target)
        links = {'include/protobuf.h': str(target)}
        invocation = {'work': str(context), 'host_prefix': '/selected', 'binding_record': '/binding'}
        if index:
            (prefix / 'include/jpeg.h').symlink_to(extra)
            links['include/jpeg.h'] = str(extra)
            invocation['shared_image'] = 'yes'
        record = {'identity': {'links': links}, 'invocation': invocation}
        (context / 'selection.json').write_text(json.dumps(record))
        calls.append(record); arguments.append({key: str(prefix)}); environments.append({envkey: str(context)})
    def check():
        return controller.additive_host_buildlink_relocation(
            arguments[0], arguments[1], environments[0], environments[1], work)
    assert check() == {key}
    assert controller.additive_host_buildlink_relocation(arguments[0], arguments[0], {}, {}, work) == set()
    record_path = Path(environments[1][envkey]) / 'selection.json'
    original = record_path.read_text()
    font_record = json.loads(original)
    font_record['invocation']['shared_font'] = 'yes'
    font_record['invocation']['shared_codecs'] = 'yes'
    font_record['invocation']['shared_openh264'] = 'yes'
    font_record['invocation']['shared_pffft'] = 'yes'
    font_record['invocation']['shared_expat'] = 'yes'
    font_record['invocation']['shared_pdf_libraries'] = 'yes'
    record_path.write_text(json.dumps(font_record))
    assert check() == {key}
    record_path.write_text(original)
    for operation, expected in (
            (lambda record: record['identity']['links'].pop('include/protobuf.h'), 'removed or replaced'),
            (lambda record: record['invocation'].update(binding_record='/foreign'), 'unrelated input'),
            (lambda record: record['invocation'].update(shared_image='no'), 'selected provider')):
        record = json.loads(original); operation(record); record_path.write_text(json.dumps(record))
        try: check()
        except ValueError as error: assert expected in str(error), str(error)
        else: raise AssertionError('invalid relocation accepted')
    record_path.write_text(original)
    link = Path(arguments[1][key]) / 'include/protobuf.h'
    link.unlink(); link.symlink_to(extra)
    try: check()
    except ValueError as error: assert 'link differs' in str(error)
    else: raise AssertionError('foreign live link accepted')
print('PASS: additive buildlink relocation preserves previous providers and rejects foreign inputs')
