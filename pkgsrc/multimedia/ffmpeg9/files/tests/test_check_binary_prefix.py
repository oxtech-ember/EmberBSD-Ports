#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import os,subprocess,tempfile,unittest,importlib.util
from unittest.mock import patch
from pathlib import Path
HOST=Path(os.environ['FFMPEG_TEST_HOST_PREFIX']); AR=HOST/'bin/llvm-ar'; READOBJ=HOST/'bin/llvm-readobj'; PY=Path(os.environ['FFMPEG_TEST_PYTHON']); SCAN=Path(__file__).with_name('check_binary_prefix.py')
CONFIG=Path(os.environ['FFMPEG_TEST_CONFIG_H']); SOURCE=Path(os.environ['FFMPEG_TEST_VERSION_O']); PREFIX=os.environ['FFMPEG_TEST_PRODUCER_PREFIX']
class ArchiveCases(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.payload=self.root/'payload';self.payload.mkdir(); (self.root/'version.o').write_bytes(SOURCE.read_bytes()); self.archive=self.payload/'lib.a';subprocess.run([AR,'cr',self.archive,self.root/'version.o'],check=True)
 def scan(self):return subprocess.run([PY,SCAN,'--payload',self.payload,'--config-h',CONFIG,'--producer-prefix',PREFIX,'--llvm-ar',AR,'--llvm-readobj',READOBJ],capture_output=True,text=True)
 def test_known(self): self.assertEqual(self.scan().returncode,0)
 def test_duplicate_version(self):
  subprocess.run([AR,'q',self.archive,self.root/'version.o'],check=True);self.assertEqual(self.scan().returncode,0)
 def test_other_member(self):
  (self.root/'extra.o').write_bytes(b'\x00'+PREFIX.encode()+b'/evil\x00');subprocess.run([AR,'q',self.archive,self.root/'extra.o'],check=True);self.assertNotEqual(self.scan().returncode,0)
 def test_near_match_in_cstring(self):
  import ast
  line=next(v for v in CONFIG.read_text().splitlines() if v.startswith('#define FFMPEG_CONFIGURATION '))
  config=ast.literal_eval(line.split(' ',2)[2]).encode()
  body=(self.root/'version.o').read_bytes(); assert config in body
  (self.root/'version.o').write_bytes(body.replace(config,b'X'+config[1:],1))
  subprocess.run([AR,'r',self.archive,self.root/'version.o'],check=True)
  self.assertNotEqual(self.scan().returncode,0)
 def test_unknown_binary_with_config(self):
  import ast
  line=next(v for v in CONFIG.read_text().splitlines() if v.startswith('#define FFMPEG_CONFIGURATION '))
  config=ast.literal_eval(line.split(' ',2)[2]).encode()
  (self.payload/'unknown').write_bytes(b'\0'+config+b'\0')
  self.assertNotEqual(self.scan().returncode,0)
 def test_prefix_outside_cstring(self):
  (self.payload/'unexpected').write_bytes(b'\xcf\xfa\xed\xfe'+PREFIX.encode()+b'\0')
  self.assertNotEqual(self.scan().returncode,0)
 def test_overlapping_sections(self):
  spec=importlib.util.spec_from_file_location('ffmpeg_scanner',SCAN); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  section='  Section {\n    Offset: 0\n    Size: 0x4\n    Type: CStringLiterals (0x2)\n  }'
  with patch.object(module,'run',return_value=section+'\n'+section):
   with self.assertRaisesRegex(ValueError,'overlapping'):
    module.macho_ranges(Path('mock'),b'abc\0',b'abc',READOBJ)
 def test_cstring_overlaps_regular(self):
  spec=importlib.util.spec_from_file_location('ffmpeg_scanner',SCAN); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  c='  Section {\n    Offset: 0\n    Size: 0x4\n    Type: CStringLiterals (0x2)\n  }'
  r='  Section {\n    Offset: 2\n    Size: 0x2\n    Type: Regular (0x0)\n  }'
  with patch.object(module,'run',return_value=c+'\n'+r):
   with self.assertRaisesRegex(ValueError,'overlapping'):
    module.macho_ranges(Path('mock'),b'abc\0',b'abc',READOBJ)
 def test_extra_metadata(self):
  with self.archive.open('ab') as f:f.write(PREFIX.encode()+b'/evil\x00')
  self.assertNotEqual(self.scan().returncode,0)
if __name__=='__main__':unittest.main()
