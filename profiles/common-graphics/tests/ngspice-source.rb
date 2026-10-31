#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual pkgsrc metadata and source preparation.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: ngspice-source.rb EXPORTED_PKGSRC MAKECONF ARCHIVE NEW_WORK' unless ARGV.length == 4
tree, makeconf, archive = ARGV.take(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[3])
abort 'Use absolute portable paths.' unless [tree, makeconf, archive, work].all? { |p| p.match?(%r{\A/[A-Za-z0-9_./-]+\z}) }
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
root = File.expand_path('../../..', __dir__)
probe = root + '/probes/kicad/ngspice'
pin = File.read(probe + '/sources.tsv').split
abort 'Wrong archive.' unless File.basename(archive) == pin[0] && Digest::SHA256.file(archive).hexdigest == pin[1]
patches = Dir.glob(tree + '/cad/ng-spice/patches/patch-*').sort
series = File.readlines(probe + '/patches/series', chomp: true)
abort 'Expected thirteen exported regular patches.' unless patches.length == 13 && series.length == 13 && patches.all? { |p| File.file?(p) && !File.symlink?(p) }
patches.zip(series).each do |exported, name|
  abort "Patch differs: #{exported}" unless File.binread(exported) == File.binread(probe + '/patches/' + name)
end
FileUtils.mkdir_p(work + '/package')
records = []
run = lambda do |name, argv|
  stdout, stderr, status = Open3.capture3({ 'LC_ALL' => 'C' }, *argv)
  File.write(work + '/' + name + '.stdout', stdout)
  File.write(work + '/' + name + '.stderr', stderr)
  records << { name: name, argv: argv, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(records) + "\n")
  abort "Failed #{name}; see logs." unless status.success?
  stdout
end
bmake = ENV.fetch('BMAKE', 'bmake')
metadata = {}
%w[ng-spice-shared ng-spice].each do |package|
  make = [bmake, '-C', tree + '/cad/' + package, "MAKECONF=#{makeconf}",
          "WRKDIR=#{work}/package", "WRKOBJDIR=#{work}/objects", "PACKAGES=#{work}/packages",
          "DISTDIR=#{File.dirname(archive)}", '_PKGSRC_BARRIER=yes']
  query = lambda do |name|
    run.call(package + '-' + name, make + ['show-var', "VARNAME=#{name}"]).strip
  end
  values = %w[PKGNAME PKG_FAIL_REASON WRKDIR WRKSRC ERROR_DIR CONFIGURE_ARGS CONFIGURE_ENV DEPENDS PATCHDIR DISTINFO_FILE MAKE_FLAGS OPSYS USE_CROSS_COMPILE PKGSRC_COMPILER].to_h { |name| [name, query.call(name)] }
  abort 'Package metadata failed.' unless values['PKG_FAIL_REASON'].empty? && values['PKGNAME'] == package + '-47nb1'
  if values['USE_CROSS_COMPILE'] == 'yes'
    target_system_flag = 'uname=' + values['OPSYS']
    abort 'XSPICE does not receive the target OS.' unless Shellwords.split(values['MAKE_FLAGS']).include?(target_system_flag)
  end
  %w[WRKDIR WRKSRC ERROR_DIR].each do |name|
    path = File.expand_path(values[name])
    abort "Non-private #{name}" unless path.start_with?(work + '/')
  end
  abort 'Wrong patch provider.' unless File.realpath(values['PATCHDIR']) == tree + '/cad/ng-spice/patches'
  abort 'Wrong archive metadata.' unless File.realpath(values['DISTINFO_FILE']) == tree + '/cad/ng-spice/distinfo'
  options = Shellwords.split(values['CONFIGURE_ARGS'])
  # Clang has no LLVM OpenMP runtime of its own version in Ports.
  openmp = values['PKGSRC_COMPILER'].split.include?('clang') ? '--disable-openmp' : '--enable-openmp'
  abort 'Configure enables OpenMP without a runtime.' if openmp == '--disable-openmp' && options.include?('--enable-openmp')
  %W[--enable-cider --enable-xspice --enable-osdi --enable-klu #{openmp} --with-fftw3=yes --enable-shared --disable-static].each do |option|
    abort "Missing #{option}" unless options.include?(option)
  end
  if package == 'ng-spice'
    %w[--with-readline=yes --with-editline=no --without-x --with-ngshared=no].each do |option|
      abort "Missing CLI option #{option}" unless options.include?(option)
    end
    abort 'Missing matching common provider.' unless Shellwords.split(values['DEPENDS']).include?('ng-spice-shared-47nb1:../../cad/ng-spice-shared')
  else
    abort 'Shared interface absent.' unless options.include?('--with-ngshared=yes')
    run.call('archive-checksum', make + ['checksum'])
    run.call('extract-source', ['tar', '-xzf', archive, '-C', work + '/package'])
    run.call('normal-pkgsrc-patch', make + ['do-pkgsrc-patch'])
  end
  metadata[package] = values
end
run.call('probe-preparation', ['sh', probe + '/prepare-source.sh', archive, work + '/probe-source'])
expected = work + '/probe-source'
actual = work + '/package/ngspice-47'
source_files = Dir.glob(expected + '/**/*', File::FNM_DOTMATCH).select { |p| File.file?(p) && !p.end_with?('/.ember-source-pin') }
source_files.each do |file|
  relative = file.delete_prefix(expected + '/')
  abort "Prepared source differs: #{relative}" unless File.file?(actual + '/' + relative) && File.binread(file) == File.binread(actual + '/' + relative)
end
inputs = patches + [tree + '/cad/ng-spice/Makefile', tree + '/cad/ng-spice/Makefile.common',
                   tree + '/cad/ng-spice/distinfo', tree + '/cad/ng-spice-shared/Makefile', archive, makeconf]
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Actual pkgsrc metadata/checksum/patch targets and full prepared-source comparison; no package build, installation or target execution.',
  inputs: inputs.to_h { |path| [path, Digest::SHA256.file(path).hexdigest] },
  metadata: metadata, compared_source_files: source_files.length
}) + "\n")
puts "PASS: both package interfaces, thirteen materialized patches and #{source_files.length} prepared source files match."
