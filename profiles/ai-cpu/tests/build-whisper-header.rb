# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Reuse the real upstream unit-test commands.
require 'json'
require 'shellwords'
require 'open3'

abort 'Usage: build-whisper-header.rb CROSS_OR_NATIVE_OUTPUT' unless ARGV.length == 1
output = File.realpath(ARGV[0])
build = "#{output}/build"
database = JSON.parse(File.read("#{build}/compile_commands.json"))
entry = database.find { |row| row.fetch('file').end_with?('/tests/test-whisper-buffer-loader.cpp') }
abort 'Build the upstream buffer-loader test first' unless entry
compile = entry['arguments'] || Shellwords.split(entry.fetch('command'))
compile = compile.dup
old_object = compile.fetch(compile.index('-o') + 1)
compile[compile.index('-o') + 1] = "#{output}/whisper-header.o"
compile[compile.index(entry.fetch('file'))] = File.join(__dir__, 'whisper-header.cpp')
commands, error, status = Open3.capture3(ENV.fetch('NINJA', 'ninja'), '-t', 'commands', 'test-whisper-buffer-loader', chdir: build)
abort error unless status.success?
link = Shellwords.split(commands.lines.last)
abort 'Unexpected upstream link wrapper' unless link.first(2) == [':', '&&'] && link.last(2) == ['&&', ':']
link = link[2...-2]
abort 'Upstream test object missing' unless link.include?(old_object)
link[link.index(old_object)] = "#{output}/whisper-header.o"
link[link.index('-o') + 1] = "#{output}/whisper-header"
File.write("#{output}/header-test-commands.txt", [compile, link].map { |args| Shellwords.join(args) }.join("\n") + "\n")
[compile, link].each do |args|
  abort 'Header-test build failed' unless system(*args, chdir: entry.fetch('directory'))
end
