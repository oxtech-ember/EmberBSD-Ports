// SPDX-License-Identifier: BSD-2-Clause
// AI-assisted actual LLVM EHHeaderParser source fixture.
#include <sys/mman.h>
#include <unistd.h>
#include <initializer_list>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"failed line %d\n",__LINE__); std::abort(); } } while (0)
#define _LIBUNWIND_LOG(...) ((void)0)
#define _LIBUNWIND_DEBUG_LOG(...) ((void)0)
#define _LIBUNWIND_ABORT(...) std::abort()
#define DW_EH_PE_ptr 0x00
#define DW_EH_PE_uleb128 0x01
#define DW_EH_PE_sleb128 0x09

#define DW_EH_PE_udata2 0x02
#define DW_EH_PE_udata4 0x03
#define DW_EH_PE_udata8 0x04
#define DW_EH_PE_sdata2 0x0a
#define DW_EH_PE_sdata4 0x0b
#define DW_EH_PE_sdata8 0x0c
#define DW_EH_PE_absptr 0x00
#define DW_EH_PE_pcrel 0x10
#define DW_EH_PE_datarel 0x30
#define DW_EH_PE_indirect 0x80
#define DW_EH_PE_omit 0xff
namespace libunwind {
struct FakeSpace {
 using pint_t=uintptr_t; uintptr_t begin,end; unsigned reads=0;
 uint8_t get8(uintptr_t p) {CHECK(p>=begin && p<end); ++reads; return *(uint8_t*)p;}
 uintptr_t getEncodedP(uintptr_t &p,uintptr_t e,uint8_t enc,uintptr_t base) {
  unsigned f=enc&15;
  if(f==1 || f==9) { uint64_t v=0; unsigned shift=0; for(;;) {CHECK(p<e); unsigned x=*(uint8_t*)p++; v|=uint64_t(x&127)<<shift; shift+=7; if(!(x&128)) { if(f==9 && shift<64 && (x&64)) v |= (~uint64_t(0) << shift); break; }} return v; }
  size_t n=f==2||f==10?2:f==3||f==11?4:f==4||f==12?8:sizeof(uintptr_t);
  CHECK(p>=begin && p<=e && n<=e-p && e<=end); int64_t v=0; std::memcpy(&v,(void*)p,n); if(n==2 && f==10)v=(int16_t)v; if(n==4 && f==11)v=(int32_t)v; uintptr_t at=p; p+=n; ++reads;
  uintptr_t result=(enc&0x70)==0 ? uintptr_t(v) : uintptr_t(v)+((enc&0x70)==0x10?at:base);
  if(enc&0x80) {CHECK(result>=begin && result+sizeof(uintptr_t)<=end); std::memcpy(&result,(void*)result,sizeof(result));} return result;
 }
};
template<class A> struct CFI_Parser {
 struct FDE_Info {uintptr_t pcStart,pcEnd;}; struct CIE_Info {};
 static const char *decodeFDE(A &,uintptr_t f,FDE_Info *out,CIE_Info *) { if(f==1){out->pcStart=100;out->pcEnd=110;} else if(f==2){out->pcStart=120;out->pcEnd=130;} else return "bad"; return nullptr; }
};
#include "unwind-index-body.inc"
}
struct Reg { using link_hardened_reg_arg_t=uintptr_t; };
static void put32(unsigned char *p,uint32_t v){std::memcpy(p,&v,4);}
int main() {
 size_t page=static_cast<size_t>(sysconf(_SC_PAGESIZE));
 void *mapping=mmap(nullptr,2*page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0); CHECK(mapping!=MAP_FAILED); CHECK(mprotect(static_cast<char*>(mapping)+page,page,PROT_NONE)==0);
 unsigned char *data=static_cast<unsigned char*>(mapping)+page-32; std::memset(data,0,32); data[0]=1;data[1]=0x1b;data[2]=3;data[3]=3; put32(data+4,0); put32(data+8,2); put32(data+12,100); put32(data+16,1); put32(data+20,120); put32(data+24,2);
 libunwind::FakeSpace a{uintptr_t(data),uintptr_t(data)+32}; using P=libunwind::EHHeaderParser<libunwind::FakeSpace>; libunwind::CFI_Parser<libunwind::FakeSpace>::FDE_Info f{}; libunwind::CFI_Parser<libunwind::FakeSpace>::CIE_Info c{};
 for(auto pc:{uintptr_t(100),uintptr_t(109),uintptr_t(120),uintptr_t(129)}) {bool present=false; CHECK(P::findFDE<Reg>(a,pc,uintptr_t(data),28,&f,&c,present)); CHECK(present);}
 for(auto pc:{uintptr_t(99),uintptr_t(110),uintptr_t(130)}) {bool present=false; CHECK(!P::findFDE<Reg>(a,pc,uintptr_t(data),28,&f,&c,present)); CHECK(present);}
 for(unsigned len=0;len<12;len++){bool present=false; CHECK(!P::findFDE<Reg>(a,100,uintptr_t(data),len,&f,&c,present)); CHECK(present);}
 put32(data+8,99); {bool present=false; CHECK(!P::findFDE<Reg>(a,100,uintptr_t(data),28,&f,&c,present)); CHECK(present);}
 data[2]=0xff;data[3]=0xff; {bool present=true; CHECK(!P::findFDE<Reg>(a,100,uintptr_t(data),8,&f,&c,present)); CHECK(!present);}
 // Every fixed width supported by LLVM's table parser is bounded before lookup.
 for(unsigned format : {2u,3u,4u,10u,11u,12u}) {
  unsigned width=(format==2||format==10)?2:(format==3||format==11)?4:8;
  std::memset(data+12,0,16); data[2]=3; data[3]=format; put32(data+8,1); data[12]=100; data[12+width]=1;
  bool present=false; CHECK(P::findFDE<Reg>(a,105,uintptr_t(data),12+2*width,&f,&c,present)); CHECK(present);
  present=false; CHECK(!P::findFDE<Reg>(a,105,uintptr_t(data),11+2*width,&f,&c,present)); CHECK(present);
 }
 data[2]=3;data[3]=1; put32(data+8,1); {bool present=false; CHECK(!P::findFDE<Reg>(a,105,uintptr_t(data),28,&f,&c,present)); CHECK(present);}
 // Count LEB decoding and bounded unterminated count.
 std::memset(data,0,32); data[0]=1;data[1]=0x1b;data[2]=1;data[3]=3; data[8]=1;put32(data+9,100);put32(data+13,1);
 {bool present=false; CHECK(P::findFDE<Reg>(a,105,uintptr_t(data),17,&f,&c,present)); CHECK(present);}
 data[8]=0x80; {bool present=false; CHECK(!P::findFDE<Reg>(a,105,uintptr_t(data),9,&f,&c,present)); CHECK(present);}
 for(unsigned i=8;i<17;i++) data[i]=0x80; data[17]=2; {bool present=false; CHECK(!P::findFDE<Reg>(a,105,uintptr_t(data),18,&f,&c,present)); CHECK(present);}
 // Signed LEB preserves negative and valid overlong representations.
 std::memset(data,0,32); data[0]=1; data[1]=9; data[2]=0xff; data[3]=0xff;
 data[4]=0x7f; {typename P::EHHeaderInfo info{}; CHECK(P::decodeEHHdr(a,uintptr_t(data),uintptr_t(data)+5,info)); CHECK(info.eh_frame_ptr==uintptr_t(-1));}
 for(unsigned i=4;i<13;i++) data[i]=0xff; data[13]=0x7f;
 {typename P::EHHeaderInfo info{}; CHECK(P::decodeEHHdr(a,uintptr_t(data),uintptr_t(data)+14,info)); CHECK(info.eh_frame_ptr==uintptr_t(-1));}
 data[13]=1; {typename P::EHHeaderInfo info{}; CHECK(!P::decodeEHHdr(a,uintptr_t(data),uintptr_t(data)+14,info));}
 // Indirect header frame pointer and indirect table operands retain upstream semantics.
 std::memset(data,0,32); data[0]=1;data[1]=0x9b;data[2]=3;data[3]=0x83; put32(data+4,16);put32(data+8,1);put32(data+12,0);put32(data+16,0); uintptr_t indirect=1; std::memcpy(data+20,&indirect,sizeof(indirect));
 {typename P::EHHeaderInfo info{}; CHECK(P::decodeEHHdr(a,uintptr_t(data),uintptr_t(data)+32,info)); CHECK(info.eh_frame_ptr==1);}
 // Table entries indirect through two pointer slots.
 unsigned char indirectTable[64]={1,0x1b,3,0xb3}; put32(indirectTable+8,1); put32(indirectTable+12,24); put32(indirectTable+16,32); uintptr_t start=100,entry=1; std::memcpy(indirectTable+24,&start,sizeof(start));std::memcpy(indirectTable+32,&entry,sizeof(entry)); a.begin=uintptr_t(indirectTable);a.end=a.begin+sizeof(indirectTable);
 {bool present=false; CHECK(P::findFDE<Reg>(a,105,uintptr_t(indirectTable),40,&f,&c,present));CHECK(present);}
 a.begin=uintptr_t(data);a.end=a.begin+32;
 // Omitted table is absent even if count is nonzero.
 data[1]=0x1b; data[3]=0xff; put32(data+8,1); {bool present=true; CHECK(!P::findFDE<Reg>(a,105,uintptr_t(data),12,&f,&c,present)); CHECK(!present);}
 data[2]=0xff; data[3]=3; {bool present=true; CHECK(!P::findFDE<Reg>(a,105,uintptr_t(data),8,&f,&c,present)); CHECK(!present);}
 data[2]=3; data[3]=3; for(unsigned len=0;len<12;len++) { unsigned char *tail=static_cast<unsigned char*>(mapping)+page-len; if(len) std::memcpy(tail,data,len); bool present=false; a.begin=uintptr_t(tail); a.end=uintptr_t(tail)+len; CHECK(!P::findFDE<Reg>(a,105,uintptr_t(tail),len,&f,&c,present)); CHECK(present); }
 CHECK(munmap(mapping,2*page)==0); puts("PASS: indexed hits/misses, truncated bounds and absent table");
}
