#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check real input and diagnostic formatting.
require 'open3'
require 'json'

abort 'Usage: input-format.rb UPSTREAM_C PATCHED_C INPUT_HEADER UPSTREAM_MISC_H PATCHED_MISC_H NEW_RESULTS' unless ARGV.size == 6
before, after, header, before_misc, after_misc, work = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(work)
native = ENV.fetch('HOST_CC', '/usr/bin/cc')
target = ENV.fetch('TARGET_CC')
sysroot = ENV.fetch('TARGET_SYSROOT')
seat = File.read(header)[/struct xwl_seat \{.*?^\};/m]
raise 'The real seat identifier is not uint32_t' unless seat && seat.match?(/^\s+uint32_t id;$/)
commands = []
[before, after].each_with_index do |input, index|
  version = index.zero? ? 'upstream' : 'patched'
  source = File.read(input)
  body = source[/add_device\(struct xwl_seat \*xwl_seat,.*?^\}/m]
  raise 'Missing real add_device function' unless body
  statements = body.scan(/^\s*snprintf\(name, sizeof name, .*xwl_seat->id\);$/)
  declaration = body[/char name\[\d+\];/]
  raise 'Ambiguous seat formatting' unless statements.size == 1 && declaration
  tablet = source[/tablet_tool_button_state\(.*?^\}/m]
  raise 'The real tablet identifier is not uint32_t' unless tablet && tablet.match?(/uint32_t button,/)
  tablet_calls = tablet.scan(/^\s*ErrorF\("unknown tablet button number .*button\);$/)
  raise 'Ambiguous tablet formatting' unless tablet_calls.size == 1
  misc = File.read(index.zero? ? before_misc : after_misc).gsub(/\\\n/, '')
  line_calls = misc.scan(/ErrorFSigSafe\("BUG: %s:.*?__FILE__, __LINE__, __func__\);/m)
  raise 'Ambiguous source-line formatting' unless line_calls.size == 1
  %w[seat tablet source-line].each do |kind|
    name = version + '-' + kind
    expression, expected, local, checks = case kind
    when 'seat'
      [statements.first.strip,
       '{"test:0", "test:1", "test:2147483647", "test:2147483648", "test:4294967295"}',
       "const char *driver = \"test\";\nstruct seat_fixture seat;\nconst struct seat_fixture *xwl_seat = &seat;\n#{declaration}",
       'seat.id = ids[i];']
    when 'tablet'
      [tablet_calls.first.strip,
       '{"unknown tablet button number 0\\n", "unknown tablet button number 1\\n", "unknown tablet button number 2147483647\\n", "unknown tablet button number 2147483648\\n", "unknown tablet button number 4294967295\\n"}',
       'char name[80];', 'uint32_t button = ids[i];']
    else
      [line_calls.first.strip, '{"BUG: format-fixture:42 in main()\\n"}', 'char name[80];', '']
    end
    body = if kind == 'source-line'
      <<~C
        /* Verify the real predefined macro type with the selected compiler. */
        typedef char line_type_is_int[__builtin_types_compatible_p(__typeof__(__LINE__), int) ? 1 : -1];
        (void)sizeof(line_type_is_int);
        #line 42 "format-fixture"
        #{expression}
        if (strcmp(name, expected[0]) != 0) {
            return 1;
        }
      C
    else
      <<~C
        static const uint32_t ids[] = {0, 1, INT32_MAX, UINT32_C(2147483648), UINT32_MAX};
        for (unsigned i = 0; i < sizeof(ids) / sizeof(ids[0]); ++i) {
            #{checks}
            #{expression}
            if (strcmp(name, expected[i]) != 0)
                return 1;
        }
      C
    end
    harness = <<~C
      #include <inttypes.h>
      #include <stdint.h>
      #include <stdio.h>
      #include <string.h>
      #define ErrorF(...) snprintf(name, sizeof name, __VA_ARGS__)
      #define ErrorFSigSafe(...) snprintf(name, sizeof name, __VA_ARGS__)
      /* Preserve real argument types. Only bounded local formatting executes. */
      #{kind == 'seat' ? 'struct seat_fixture { uint32_t id; };' : ''}
      int
      main(void)
      {
          static const char *expected[] = #{expected};
          #{local}
          #{body}
          return 0;
      }
    C
    file = File.join(work, name + '.c')
    File.write(file, harness)
    executable = File.join(work, name)
    command = [native, '-std=c99', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', file, '-o', executable]
    commands << {directory: work, file: file, arguments: command}
    out, err, status = Open3.capture3(*command)
    File.write(executable + '-compile.log', out + err)
    raise "Native compile failed: #{name}: #{err}" unless status.success?
    out, err, status = Open3.capture3({'ASAN_OPTIONS'=>'halt_on_error=1', 'UBSAN_OPTIONS'=>'halt_on_error=1'}, executable)
    File.write(executable + '-run.log', out + err)
    expected_status = index.zero? && kind != 'source-line' ? 1 : 0
    raise "Unexpected formatting result: #{name}" unless status.exitstatus == expected_status && err.empty?
    cross = [target, '--sysroot=' + sysroot, '-std=c99', '-Wall', '-Wextra', '-Wformat=2', '-Wformat-signedness', '-Werror=format', '-Werror=format-signedness', '-c', file, '-o', File.join(work, name + '.o')]
    out, err, status = Open3.capture3(*cross)
    File.write(executable + '-target-compile.log', cross.inspect + "\n" + out + err)
    if index.zero?
      raise "Original target mismatch was not rejected: #{name}" unless !status.success? && err.include?('-Werror=format=')
    else
      raise "Patched target compile failed: #{err}" unless status.success?
    end
    puts "PASS: #{name} has expected formatting and target compiler status"
  end
end
File.write(File.join(work, 'compile_commands.json'), JSON.pretty_generate(commands))
