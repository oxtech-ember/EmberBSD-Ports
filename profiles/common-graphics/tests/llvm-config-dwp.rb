#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD. Actual sealed metadata/package regression for the DWP rebind.
require 'digest'
require 'fileutils'
require 'open3'
abort 'usage: llvm-config-dwp.rb SEALED_TOOL LLVM_NB1_PACKAGE NEW_WORK' unless ARGV.size == 3
source, package, work = ARGV.map { |p| File.expand_path(p) }
abort 'work exists' if File.exist?(work)
FileUtils.mkdir_p(work)
script = File.expand_path('../cross/rebind-llvm-config-dwp.rb', __dir__)
manifest = File.read(source + '/inputs.sha256')
anchor = Digest::SHA256.hexdigest(manifest)
def run(log, expected, *args)
  out, err, result = Open3.capture3(*args)
  File.write(log, out + err)
  abort "unexpected result: #{log}" unless result.success? == expected
  out + err
end
ruby = RbConfig.ruby
run(work+'/valid.log', true, ruby, script, source, anchor, package, work+'/valid')
output = run(work+'/query.log', true, work+'/valid/bin/llvm-config', '--version', '--host-target', '--link-shared', '--libs', 'core', 'orcjit', 'native')
abort 'wrong target metadata' unless output.include?('23.1.2') && output.include?('aarch64-unknown-netbsd') && output.include?('-lLLVM-23')
run(work+'/anchor.log', false, ruby, script, source, '0'*64, package, work+'/bad-anchor')
File.write(work+'/bad-package', 'not the accepted LLVM package')
run(work+'/package.log', false, ruby, script, source, anchor, work+'/bad-package', work+'/bad-pkg')
%w[missing metadata executable].each do |mode|
  input = work+'/'+mode
  FileUtils.cp_r(source, input)
  case mode
  when 'missing'
    text = manifest.lines.reject { |s| s.end_with?("  metadata/BuildVariables.inc\n") }.join
    File.write(input+'/inputs.sha256', text)
  when 'metadata' then File.open(input+'/metadata/BuildVariables.inc','a') { |f| f.puts '#define DRIFT 1' }
  when 'executable' then File.open(input+'/bin/llvm-config.real','a') { |f| f.write('drift') }
  end
  new_anchor = Digest::SHA256.file(input+'/inputs.sha256').hexdigest
  run(work+'/'+mode+'.log', false, ruby, script, input, new_anchor, package, work+'/bad-'+mode)
end
File.open(work+'/valid/metadata/BuildVariables.inc','a') { |f| f.puts '#define DRIFT 1' }
run(work+'/runtime-drift.log', false, work+'/valid/bin/llvm-config', '--version')
puts 'PASS: real metadata queries and six rejected anchor/package/input/runtime changes'
