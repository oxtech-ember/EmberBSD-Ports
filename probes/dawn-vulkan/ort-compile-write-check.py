#!/usr/bin/env python3
"""Exercise ORT CPU model output callback error propagation and retry.

A callback error tests stream-status propagation, not independent protobuf
SerializeToOstream failures. Requires the installed ORT API 31 and a model.
"""
import argparse
import ctypes as c
import importlib.util
import os
import re

p = argparse.ArgumentParser()
p.add_argument('--model', required=True)
p.add_argument('--prefix', default='/usr/pkg')
a = p.parse_args()
spec = importlib.util.spec_from_file_location('onnx_diagnostic', os.path.join(os.path.dirname(__file__), 'onnx-runtime-diagnostic.py'))
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
P, PP = c.c_void_p, c.POINTER(c.c_void_p)
with open(os.path.join(a.prefix, 'include/onnxruntime/onnxruntime_c_api.h')) as f:
    header = f.read()
if not re.search(r'#define\s+ORT_API_VERSION\s+31\b', header):
    raise RuntimeError('expected ORT API 31 header')
lib = c.CDLL(os.path.join(a.prefix, 'lib/libonnxruntime.so.1'))
lib.OrtGetApiBase.restype = PP
base = lib.OrtGetApiBase()
api_address = c.CFUNCTYPE(P, c.c_uint)(base[0])(31)
if not api_address:
    raise RuntimeError('runtime does not support ORT API 31')
def table_functions(address, names):
    table = c.cast(address, PP)
    def get(name, ret, *args):
        return c.CFUNCTYPE(ret, *args)(table[names.index(name)])
    return get
api = table_functions(api_address, diagnostic.api_names(header, 'OrtApi'))
compile_address = api('GetCompileApi', P)()
if not compile_address:
    raise RuntimeError('ORT compile API unavailable')
compile_api = table_functions(compile_address, diagnostic.api_names(header, 'OrtCompileApi'))
error = api('GetErrorMessage', c.c_char_p, P)
release_status = api('ReleaseStatus', None, P)
create_status = api('CreateStatus', P, c.c_int, c.c_char_p)
def check(status):
    if status:
        message = error(status).decode(errors='replace')
        release_status(status)
        raise RuntimeError(message)
state = {'fail': True, 'bytes': 0}
@c.CFUNCTYPE(P, P, P, c.c_size_t)
def write(_state, _data, size):
    state['bytes'] += size
    return create_status(1, b'intentional output callback failure') if state['fail'] else None
env, session, options = P(), P(), P()
try:
    check(api('CreateEnv', P, c.c_int, c.c_char_p, PP)(2, b'compile-write-check', c.byref(env)))
    check(api('CreateSessionOptions', P, PP)(c.byref(session)))
    check(compile_api('CreateModelCompilationOptionsFromSessionOptions', P, P, P, PP)(env, session, c.byref(options)))
    check(compile_api('ModelCompilationOptions_SetInputModelPath', P, P, c.c_char_p)(options, os.fsencode(a.model)))
    check(compile_api('ModelCompilationOptions_SetOutputModelWriteFunc', P, P, type(write), P)(options, write, None))
    run = compile_api('CompileModel', P, P, P)
    status = run(env, options)
    message = error(status).decode(errors='replace') if status else ''
    if status:
        release_status(status)
    if 'intentional output callback failure' not in message or not state['bytes']:
        raise RuntimeError('callback failure not propagated: ' + message)
    state.update(fail=False, bytes=0)
    check(run(env, options))
    if not state['bytes']:
        raise RuntimeError('successful callback received no bytes')
    print('callback failure propagated; retry wrote %d bytes' % state['bytes'])
finally:
    if options.value: compile_api('ReleaseModelCompilationOptions', None, P)(options)
    if session.value: api('ReleaseSessionOptions', None, P)(session)
    if env.value: api('ReleaseEnv', None, P)(env)
