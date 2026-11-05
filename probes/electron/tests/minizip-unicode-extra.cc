// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>
#include "unzip.h"
#include "unicode_zip_extra.h"
#pragma clang diagnostic ignored "-Wunsafe-buffer-usage"
int main(int argc, char** argv) {
  assert(argc == 5);
  unzFile f = unzOpen64(argv[1]); assert(f); assert(unzGoToFirstFile(f)==UNZ_OK);
  unz_file_info64 info{}; char raw[65536]{};
  assert(unzGetCurrentFileInfo64(f,&info,raw,65535,nullptr,0,nullptr,0)==UNZ_OK);
  std::vector<char> extra(info.size_file_extra);
  assert(unzGetCurrentFileInfo64(f,nullptr,nullptr,0,extra.data(),extra.size(),nullptr,0)==UNZ_OK);
  std::string effective;
  bool ok=zip::UnicodeZipPath(std::string_view(raw,info.size_filename),std::string_view(extra.data(),extra.size()),&effective);
  assert(ok == (std::string(argv[4])=="ok"));
  if(ok) {
    std::string expected_raw = std::string(argv[2]) == "MAXNAME" ? std::string(65535, 'a') :
        std::string(argv[2]) == "NULNAME" ? std::string("aa\0bb", 5) : std::string(argv[2]);
    assert(std::string(raw,info.size_filename)==expected_raw); assert(effective==argv[3]);
  }
  assert(unzClose(f)==UNZ_OK);
}
