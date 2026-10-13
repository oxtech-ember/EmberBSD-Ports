#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted real-terminal editline consumer check.
require 'pty'
require 'timeout'

abort 'Usage: dash-editline.rb DASH' unless ARGV.length == 1
transcript = +''
PTY.spawn({'ENV' => '/dev/null', 'PS1' => 'dash-test> ', 'TERM' => 'xterm'},
          File.expand_path(ARGV[0]), '-i') do |reader, writer, pid|
  writer.sync = true
  read_prompt = lambda do
    output = +''
    Timeout.timeout(10) do
      output << reader.readpartial(4096) until output.end_with?('dash-test> ')
    end
    transcript << output
    output
  end
  begin
    read_prompt.call
    writer.write("set -o emacs\n")
    read_prompt.call
    # Ctrl-W removes the last word in the edit buffer before execution.
    writer.write("echo EDITING_BAD\x17EDITING_OK\n")
    output = read_prompt.call
    abort "Editing failed: #{output.inspect}" unless output.match?(/\r?\nEDITING_OK\r?\n/)
    writer.write("\e[A\n")
    output = read_prompt.call
    abort "History failed: #{output.inspect}" unless output.match?(/\r?\nEDITING_OK\r?\n/)
    writer.write("fc -s EDITING_OK=HISTORY_OK\n")
    output = read_prompt.call
    abort "History substitution failed: #{output.inspect}" unless output.match?(/\r?\nHISTORY_OK\r?\n/)
    writer.write("exit 0\n")
    _, status = Process.wait2(pid)
    abort 'Interactive dash failed' unless status.success?
    puts 'PASS: dash interactive libedit word editing and history in a PTY.'
  rescue Timeout::Error, EOFError, Errno::EIO => error
    warn transcript
    abort "Interactive check failed: #{error}"
  ensure
    begin
      Process.kill('TERM', pid)
      Process.wait(pid)
    rescue Errno::ESRCH, Errno::ECHILD
      # Child already reaped above.
    end
  end
end
