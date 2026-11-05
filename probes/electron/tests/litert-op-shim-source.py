#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check restored shim retains its pinned TensorFlow donor and narrow TSL adaptation."""
import argparse, subprocess, tempfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--donor-shim',type=Path,required=True);p.add_argument('--patch-tool',type=Path,required=True)
a=p.parse_args(); owner=Path(__file__).resolve().parents[3]; patch=owner/'pkgsrc/devel/litert/patches/patch-tflite_op_shim_compat'
names=('op_kernel.h','shape.h','shape.cc','status_macros.h','tensor_view.h','tflite_op_shim.h','tflite_op_shim.cc','tflite_tensor_view.h','tflite_tensor_view.cc')
with tempfile.TemporaryDirectory(prefix='litert-op-shim-') as td:
 root=Path(td);(root/'tflite/kernels').mkdir(parents=True)
 subprocess.run([str(a.patch_tool),'-p0','-F0','-i',str(patch)],cwd=root,check=True,capture_output=True)
 restored=root/'tflite/kernels/shim'; assert {x.name for x in restored.iterdir()}==set(names)
 for name in names:
  old=(a.donor_shim/name).read_text();new=(restored/name).read_text()
  if name=='tensor_view.h':
   old=old.replace('#include "tensorflow/core/platform/logging.h"\n#include "tensorflow/core/platform/tstring.h"', '''// EmberBSD: use the shared TSL implementation directly.  TensorFlow Text's
// public shim API still spells this same type tensorflow::tstring.
#include "tsl/platform/logging.h"
#include "tsl/platform/tstring.h"

namespace tensorflow {
using tstring = ::tsl::tstring;
}  // namespace tensorflow''')
  assert old==new, 'unexpected donor modification: '+name
print('PASS: exact pinned TensorFlow shim with only the TSL type adaptation')
