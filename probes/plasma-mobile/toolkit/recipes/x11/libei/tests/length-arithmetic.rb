#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the actual protocol length helper.
require 'open3'
require 'json'

abort 'Usage: length-arithmetic.rb UPSTREAM_C PATCHED_C NEW_OUTPUT' unless ARGV.size == 3
before, after, work = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(work)
compiler = ENV.fetch('HOST_CC', '/usr/bin/cc')
commands = []
[before, after].each_with_index do |input, index|
  name = index.zero? ? 'upstream' : 'patched'
  source = File.read(input)
  helper = source[/static inline uint32_t\nbrei_string_proto_length\(uint32_t slen\)\n\{.*?\n\}/m]
  raise "Cannot find the real helper in #{input}" unless helper
  # These cases call only integer arithmetic. They do not allocate buffers,
  # open sockets, construct protocol messages or invoke a service.
  consumer = <<~C
    #include <assert.h>
    #include <stdint.h>
    #{helper}
    int main(void) {
        static const uint32_t lengths[] = {0, 1, 4, 5, UINT32_MAX - 7, UINT32_MAX - 6, UINT32_MAX};
        static const uint32_t expected[] = {4, 8, 8, 12, UINT32_MAX - 3, 0, 0};
        for (unsigned i = 0; i < sizeof(lengths) / sizeof(lengths[0]); ++i)
            if (brei_string_proto_length(lengths[i]) != expected[i]) return 1;
        return 0;
    }
  C
  file = File.join(work, name + '.c')
  File.write(file, consumer)
  executable = File.join(work, name)
  command = [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', file, '-o', executable]
  commands << {directory:work, file:file, arguments:command}
  out, err, status = Open3.capture3(*command)
  File.write(executable + '-compile.log', out + err)
  raise "Compile failed: #{name}" unless status.success?
  out, err, status = Open3.capture3({'ASAN_OPTIONS'=>'halt_on_error=1', 'UBSAN_OPTIONS'=>'halt_on_error=1'}, executable)
  File.write(executable + '-run.log', out + err)
  expected_status = index.zero? ? 1 : 0
  raise "Unexpected result: #{name}: #{status.inspect}" unless status.exitstatus == expected_status && err.empty?
  puts "PASS: #{name} returns expected status #{expected_status}"
end
File.write(File.join(work, 'compile_commands.json'), JSON.pretty_generate(commands))
