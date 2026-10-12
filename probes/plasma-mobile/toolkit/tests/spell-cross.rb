#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), full recipe host/target interpreter regression.
require 'open3'
require 'shellwords'
abort 'Usage: spell-cross.rb PKGSRC MAKECONF NEW_OUTPUT' unless ARGV.size == 3
pkgsrc, config, work = ARGV.map { |p| File.expand_path(p) }
Dir.mkdir(work)
bmake = ENV.fetch('BMAKE', 'bmake')
%w[aspell hunspell].each do |recipe|
  query = lambda do |mode, variable, *extra|
    text, status = Open3.capture2e({'MAKECONF' => config}, bmake, '-C', "#{pkgsrc}/textproc/#{recipe}", "USE_CROSS_COMPILE=#{mode}", *extra, '-V', "${#{variable}}")
    abort text unless status.success?
    File.write("#{work}/#{recipe}-#{mode}-#{variable}#{extra.empty? ? '' : '-missing'}.txt", text)
    text.strip
  end
  tools = Shellwords.split(query.call('yes', 'USE_TOOLS'))
  abort 'Target Perl selected as host tool' if tools.include?('perl:run')
  abort 'Host Perl not selected' unless tools.include?('perl')
  host = query.call('yes', 'TOOLS_PATH.perl')
  abort 'Missing native Perl executable' unless File.executable?(host) && host.start_with?('/')
  abort 'Missing target runtime dependency' unless query.call('yes', 'DEPENDS').include?('perl>=5.44.0:../../lang/perl5')
  prefix = query.call('yes', 'PREFIX')
  abort 'Wrong installed interpreter' unless query.call('yes', 'REPLACE.target-perl.new') == prefix + '/bin/perl'
  abort 'Host interpreter rewrite still enabled' unless query.call('yes', 'REPLACE_PERL').empty?
  abort 'No target script selected' if query.call('yes', 'REPLACE_FILES.target-perl').empty?
  abort 'Native behavior lost' unless Shellwords.split(query.call('no', 'USE_TOOLS')).include?('perl:run')
  abort 'Missing host Perl accepted' unless query.call('yes', 'PKG_FAIL_REASON', 'EMBERBSD_CROSS_BUILD_PERL=/nonexistent/ember-host-perl').include?('Set EMBERBSD_CROSS_BUILD_PERL')
end
puts 'PASS: real native/cross recipes preserve target scripts, runtime dependencies and host Perl selection'
