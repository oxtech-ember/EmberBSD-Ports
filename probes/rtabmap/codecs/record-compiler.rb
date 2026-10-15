# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Record actual compiler invocations.
require 'json'
source = ARGV.find { |argument| argument.end_with?('.c') && File.file?(argument) }
if ARGV.include?('-c') && source
  row = {'directory' => Dir.pwd, 'file' => File.expand_path(source), 'arguments' => ARGV}
  File.open(ENV.fetch('CODECS_COMPDB_LOG'), 'a') do |file|
    file.flock(File::LOCK_EX)
    file.puts(JSON.generate(row))
  end
end
exec(*ARGV)
