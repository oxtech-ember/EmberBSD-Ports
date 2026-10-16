#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Test the actual bootstrap copy block.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: linker-relocation.rb BOOTSTRAP aarch64|amd64 NEW_RECEIPT' unless ARGV.length == 3
tools, target, work = ARGV
triplet, emulation, assembly, as_flags = case target
when 'amd64'
  ['x86_64--netbsd', 'elf_i386', ".text\n.globl _start\n_start: nop\n", ['--32']]
when 'aarch64'
  ['aarch64--netbsd', 'aarch64elf', ".text\n.globl _start\n_start: ret\n", []]
else
  abort 'Unsupported target'
end
tools, work = [tools, work].map { |path| File.expand_path(path) }
abort 'Use a new receipt directory' if File.exist?(work)
source = File.expand_path('../build.sh', __dir__)
text = File.read(source)
start = text.index('# A relocated linker') || text.index('mkdir -p "$prefix/$triplet/bin"')
finish = text.index('cd "$work/build"', start)
abort 'Bootstrap copy block missing' unless start && finish
block = text[start...finish]
FileUtils.mkdir_p(work)
prefix = File.join(work, 'relocated')
FileUtils.mkdir_p(File.join(prefix, 'bin'))
File.write(File.join(work, 'copy-block.sh'), block)
run = lambda do |name, command, expected = true|
  out, err, status = Open3.capture3(*command)
  File.write(File.join(work, name + '.log'), out + err)
  abort "#{name}: unexpected exit #{status.exitstatus}" unless status.success? == expected
  out + err
end
script = 'tools=$1; prefix=$2; triplet=$3; work=$4; ' + block
run.call('copy', ['sh', '-c', script, 'copy', tools, prefix, triplet, work])
# This emulation selects an external script in the real amd64 bootstrap ld.
run.call('default-script', ["#{prefix}/bin/#{triplet}-ld", '-m', emulation, '--verbose'])
paths = Dir[File.join(tools, triplet, 'lib/ldscripts/*')].sort
abort 'No source scripts' if paths.empty?
hashes = paths.to_h do |original|
  copy = File.join(prefix, triplet, 'lib/ldscripts', File.basename(original))
  expected = Digest::SHA256.file(original).hexdigest
  abort "Changed linker script #{copy}" unless Digest::SHA256.file(copy).hexdigest == expected
  [original, expected]
end
File.write(File.join(work, 'start.s'), assembly)
run.call('assemble', ["#{prefix}/bin/#{triplet}-as", *as_flags, '-o', File.join(work, 'start.o'), File.join(work, 'start.s')])
run.call('link', ["#{prefix}/bin/#{triplet}-ld", '-m', emulation, '-e', '_start', '-o', File.join(work, 'standalone'), File.join(work, 'start.o')])
elf = run.call('elf', ["#{prefix}/bin/#{triplet}-readelf", '-h', '-l', '-d', File.join(work, 'standalone')])
abort 'Unexpected target dependencies' if elf.match?(/\b(?:INTERP|NEEDED|RPATH|RUNPATH)\b/)
File.write(File.join(work, 'receipt.json'), JSON.pretty_generate({
  target: target, scope: 'real bootstrap relocation and standalone link; no target execution',
  source_sha256: Digest::SHA256.file(source).hexdigest, scripts: hashes,
  output_sha256: Digest::SHA256.file(File.join(work, 'standalone')).hexdigest
}) + "\n")
puts "PASS: #{hashes.length} unchanged linker scripts and real #{emulation} standalone link"
