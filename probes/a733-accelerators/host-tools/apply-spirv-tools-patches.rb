#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# EmberBSD, AI-assisted. Apply only the reviewed SPIRV-Tools source delta.
require 'digest'
require 'open3'

abort 'usage: apply-spirv-tools-patches.rb SOURCE' unless ARGV.length == 1
source = File.realpath(ARGV[0])
patch = File.join(__dir__, 'spirv-tools-2026.4-function-order.patch')
file = File.join(source, 'source/link/linker.cpp')
pin = 'ef96ed763b43b59b33b31b362f09a02b729fa1c9'
original = 'e28e267843867c9818303022b1ba8e33b6c9eb5a710d20d92b687d0b7ddc9620'
patched = '74ee3b81eea4054aec67d0870171a31483834b8d5d39c9778b20b28f8e99855f'
git = lambda do |*args|
  text, status = Open3.capture2e('git', '-C', source, *args)
  abort text unless status.success?
  text
end
abort 'Wrong SPIRV-Tools revision' unless git.call('rev-parse', 'HEAD').strip == pin
status = git.call('status', '--porcelain')
case Digest::SHA256.file(file).hexdigest
when original
  abort 'SPIRV-Tools source is not clean' unless status.empty?
  git.call('apply', '--check', patch)
  git.call('apply', patch)
when patched
  abort 'Unrelated SPIRV-Tools source changes' unless status == " M source/link/linker.cpp\n"
else
  abort 'Unexpected linker source hash'
end
abort 'Patched linker hash mismatch' unless Digest::SHA256.file(file).hexdigest == patched
puts "SPIRV-Tools #{pin}: stable function order; patch SHA256 #{Digest::SHA256.file(patch).hexdigest}"
