#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed helper interpreter contract.
require 'open3'
abort 'Usage: llvm-python315-payload.rb CLANG_STAGE LLD_STAGE LIT_STAGE HOST_PYTHON' unless ARGV.size == 4
clang, lld, lit, python = ARGV.map { |path| File.expand_path(path) }
failures = []
expected = %w[bin/analyze-build bin/git-clang-format bin/hmaptool bin/intercept-build bin/scan-build-py bin/scan-view libexec/analyze-c++ libexec/analyze-cc libexec/intercept-c++ libexec/intercept-cc share/clang/clang-format-diff.py share/scan-view/Reporter.py share/scan-view/startfile.py]
expected.each do |rel|
  failures << "Wrong Python interpreter: #{rel}" unless File.open(File.join(clang, rel), &:readline) == "#!/usr/pkg/bin/python3.15\n"
end
%w[bin/lit bin/llvm-lit].each do |rel|
  failures << "Wrong lit interpreter: #{rel}" unless File.open(File.join(lit, rel), &:readline) == "#!/usr/pkg/bin/python3.15\n"
end
[clang, lld, lit].each do |stage|
  plist = File.read(File.join(stage, '+CONTENTS'))
  failures << "Old runtime dependency: #{stage}" if plist.match?(/^@pkgdep (python314|py314-)/)
end
failures << 'Clang has no explicit Python runtime' unless File.read(File.join(clang, '+CONTENTS')).match?(/^@pkgdep python315>=3\.15\.0$/)
failures << 'lit allows two ABI providers' unless File.read(File.join(lit, '+CONTENTS')).include?("@pkgcfl py[0-9]*-llvm-lit-[0-9]*\n")
abort failures.join("\n") unless failures.empty?
# Compile every installed Python module, not only the executable first lines.
modules = Dir.glob(File.join(clang, '{lib/libscanbuild,lib/libear,share/scan-view,share/clang}', '**', '*.py'))
output, status = Open3.capture2e(python, '-m', 'py_compile', *(expected.map { |rel| File.join(clang, rel) } + modules).uniq)
abort output unless status.success?
puts "PASS: 13 Clang entry points, two lit launchers, #{modules.size} installed modules and runtime metadata."
