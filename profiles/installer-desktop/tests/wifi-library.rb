# Origin: EmberBSD Wi-Fi library allocation and configuration regression, prepared with AI assistance.
# SPDX-License-Identifier: BSD-2-Clause
require 'tmpdir'
require 'open3'
abort 'Usage: ruby wifi-library.rb extracted-dhcpcd-ui-source' unless ARGV.size==1
root=File.expand_path(ARGV[0]);lib=root+'/src/libdhcpcd'
source=File.read(lib+'/dhcpcd.c')
constructor=source[/DHCPCD_CONNECTION \*\ndhcpcd_new\(void\)\n\{.*?^\}/m] or abort 'Constructor missing'
code=<<~C
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define IN_LIBDHCPCD
#include "dhcpcd.h"
static void *failed_calloc(size_t n,size_t s) {(void)n;(void)s;return NULL;}
#define calloc failed_calloc
#{constructor}
#undef calloc
int main(int argc,char **argv) {
 assert(argc==3);
 if(strcmp(argv[1],"allocation")==0) { assert(dhcpcd_new()==NULL);return 0; }
 DHCPCD_CONNECTION con={0};con.cffile=argv[2];
 if(strcmp(argv[1],"invalid-block")==0) { errno=0;assert(dhcpcd_config_blocks(&con,NULL)==NULL);assert(errno==EINVAL);return 0; }
 char **blocks=dhcpcd_config_blocks(&con,"interface");
 assert(blocks&&blocks[0]&&strcmp(blocks[0],"wm0")==0&&blocks[1]==NULL);
 free(blocks[0]);free(blocks);free(con.buf);return 0;
}
C
Dir.mktmpdir do |d|
 File.write(d+'/contract.c',code)
 File.write(d+'/dhcpcd.conf',"interface\ninterface wm0\n")
 out,err,st=Open3.capture3('cc','-fsanitize=address,undefined','-I'+lib,'-I'+root+'/src',d+'/contract.c',lib+'/config.c','-o',d+'/contract');abort out+err unless st.success?
 errors=[]
 %w[allocation blocks invalid-block].each do |mode|
  out,err,st=Open3.capture3(d+'/contract',mode,d+'/dhcpcd.conf');errors << mode+": "+(out+err).lines.first(3).join unless st.success?
 end
 abort errors.join("\n") unless errors.empty?
end
puts 'Wi-Fi library: allocation failure, incomplete interface block and invalid list argument pass ASan/UBSan'
