#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the actual optional-file function.
require 'fileutils'
require 'json'
abort 'Usage: process-name-causal.rb PRISTINE_SOURCE PATCHED_SOURCE NEW_OUTPUT' unless ARGV.size == 3
pristine, patched, output = ARGV.map { |path| File.expand_path(path) }
abort 'Output already exists' if File.exist?(output) || File.symlink?(output)
FileUtils.mkdir_p(output)
cc = ENV.fetch('CC', 'cc')
receipts = []
[pristine, patched].zip(%w[baseline patched]).each do |source, variant|
  module_text = File.read(File.join(source, 'src/sharedspice.c'))
  start = module_text.index('char * get_calling_process_name(void) {')
  abort 'Missing actual function' unless start
  function = module_text[start..]
  # This function is the final definition in the pinned ngspice 47 module.
  abort 'Unexpected function layout' unless function.end_with?("}\n")
  harness = <<~C
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    #define HAVE__PROC_MEMINFO 1
    static FILE *missing_file(const char *path, const char *mode)
    {
        if (strcmp(path, "/proc/self/comm") || strcmp(mode, "r"))
            exit(2);
        return NULL;
    }
    #define fopen missing_file
    #define copy strdup
    #{function}
    int main(void)
    {
        if (get_calling_process_name() != NULL)
            return 1;
        puts("PASS: missing optional process-name file returns NULL");
        return 0;
    }
  C
  test_source = File.join(output, variant + '.c')
  program = File.join(output, variant)
  File.write(test_source, harness)
  command = [cc, '-O2', '-g', '-std=gnu11', '-Wall', '-Wextra',
             '-Werror=return-type', test_source, '-o', program]
  log = File.join(output, variant + '-build.log')
  ok = File.open(log, 'w') { |io| system(*command, out: io, err: io) }
  receipts << {command: command, status: $?.exitstatus}
  if variant == 'baseline'
    abort 'Baseline did not expose missing return' if ok || !File.read(log).include?('return-type')
  else
    abort 'Patched function did not compile' unless ok
    command = ['valgrind', '--tool=memcheck', '--leak-check=full',
               '--show-leak-kinds=all', '--errors-for-leak-kinds=all',
               '--error-exitcode=99', "--log-file=#{output}/memcheck.log", program]
    ok = File.open(File.join(output, 'run.log'), 'w') { |io| system(*command, out: io, err: io) }
    receipts << {command: command, status: $?.exitstatus}
    abort 'Patched runtime failed' unless ok
  end
end
File.write(File.join(output, 'commands.json'), JSON.pretty_generate(receipts))
puts 'PASS: missing-return causal compiler check and patched Memcheck'
