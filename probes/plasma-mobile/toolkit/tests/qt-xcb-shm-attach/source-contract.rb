#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted actual-source Qt XCB SHM contract runner.
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: source-contract.rb QXCB_BACKINGSTORE_CPP NEW_OUTPUT' unless ARGV.length == 2
source_path, output = ARGV.map { |path| File.expand_path(path) }
abort "Missing Qt source: #{source_path}" unless File.file?(source_path)
abort "Output already exists: #{output}" if File.exist?(output)

def extract_method(source)
  signature = 'bool QXcbBackingStoreImage::createSystemVShmSegment('
  start = source.index(signature)
  abort 'Missing QXcbBackingStoreImage::createSystemVShmSegment' unless start
  opening = source.index('{', start)
  abort 'Missing method body' unless opening

  depth = 0
  state = :code
  index = opening
  while index < source.length
    char = source[index]
    next_char = source[index + 1]
    case state
    when :code
      if char == '/' && next_char == '/'
        state = :line_comment
        index += 1
      elsif char == '/' && next_char == '*'
        state = :block_comment
        index += 1
      elsif char == '"'
        state = :string
      elsif char == "'"
        state = :character
      elsif char == '{'
        depth += 1
      elsif char == '}'
        depth -= 1
        return source[start..index] if depth.zero?
      end
    when :line_comment
      state = :code if char == "\n"
    when :block_comment
      if char == '*' && next_char == '/'
        state = :code
        index += 1
      end
    when :string, :character
      if char == '\\'
        index += 1
      elsif (state == :string && char == '"') || (state == :character && char == "'")
        state = :code
      end
    end
    index += 1
  end
  abort 'Unterminated QXcbBackingStoreImage::createSystemVShmSegment body'
end

Dir.mkdir(output)
template = File.read(File.join(__dir__, 'contract.cpp'))
marker = '// __QT_XCB_SHM_HELPER__'
abort 'Expected one helper marker in contract.cpp' unless template.scan(marker).length == 1
generated = File.join(output, 'contract.cpp')
File.write(generated, template.sub(marker, extract_method(File.read(source_path))))

cxx = Shellwords.split(ENV.fetch('CXX', 'c++'))
abort 'CXX must select one compiler command' if cxx.empty?
binary = File.join(output, 'contract')
command = cxx + %w[-std=c++17 -g -O1 -Wall -Wextra -Werror
                   -fsanitize=address,undefined -fno-omit-frame-pointer]
command += [generated, '-o', binary]
stdout, stderr, status = Open3.capture3(*command)
File.write(File.join(output, 'build.log'), stdout + stderr)
File.write(File.join(output, 'command.json'), JSON.pretty_generate(command) + "\n")
abort stdout + stderr unless status.success?

cases = %w[
  success-retained-info
  success-null-info-test-run
  shmget-failure
  shmat-failure-cleanup-and-errno
  xcb-attach-failure-cleanup
]
failed = []
cases.each do |name|
  stdout, stderr, status = Open3.capture3(
    { 'ASAN_OPTIONS' => 'detect_leaks=1:halt_on_error=1',
      'UBSAN_OPTIONS' => 'halt_on_error=1:print_stacktrace=1' },
    binary, name
  )
  File.write(File.join(output, "#{name}.log"), stdout + stderr)
  if status.success?
    puts "PASS #{name}"
  else
    failed << name
    warn "FAIL #{name}: exit #{status.exitstatus}"
    warn (stdout + stderr).lines.first(6).join
  end
end
abort "Contract failed: #{failed.join(', ')}" unless failed.empty?
