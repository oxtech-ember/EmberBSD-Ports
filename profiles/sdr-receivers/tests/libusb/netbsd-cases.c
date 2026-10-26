/* SPDX-License-Identifier: BSD-2-Clause */
static struct device_priv dp;
static struct handle_priv hp;
static struct libusb_device dev={&dp};
static struct libusb_device_handle handle={&dev,&hp};
static struct usbi_transfer tr;
static unsigned char buffer[128];
#define CHECK(x) do { if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1;} } while(0)
static int transfer(int type,int ep) { memset(&tr,0,sizeof(tr));tr.transfer.dev_handle=&handle;tr.transfer.type=type;tr.transfer.endpoint=ep;tr.transfer.buffer=buffer;tr.transfer.length=sizeof(buffer);tr.transfer.timeout=50;return _sync_gen_transfer(&tr); }
int main(int argc,char **argv) {
 if(argc!=2)return 2;
 const char *name=argv[1]; strcpy(dp.devnode,"/dev/ugen1.00");
 unsetenv("LIBUSB_NETBSD_BULK_READAHEAD");
 if(!strncmp(name,"invalid:",8)) {setenv("LIBUSB_NETBSD_BULK_READAHEAD",name+8,1);CHECK(netbsd_open(&handle)==LIBUSB_ERROR_INVALID_PARAM);CHECK(opens==0);return 0;}
 if(strcmp(name,"default"))setenv("LIBUSB_NETBSD_BULK_READAHEAD","82",1);
 CHECK(netbsd_open(&handle)==0);
 if(!strcmp(name,"default")){CHECK(transfer(2,0x82)==0);CHECK(options==0&&enables==0&&reads==1);return 0;}
 if(!strcmp(name,"selected")){CHECK(transfer(2,0x82)==0);CHECK(options==1&&enables==1&&reads==1&&!wrong_option);return 0;}
 if(!strcmp(name,"unselected")){CHECK(transfer(2,0x81)==0);CHECK(options==0&&enables==0);return 0;}
 if(!strcmp(name,"out")){CHECK(transfer(2,0x02)==0);CHECK(options==0&&enables==0&&writes==1);return 0;}
 if(!strcmp(name,"interrupt")){CHECK(transfer(3,0x82)==0);CHECK(options==0&&enables==0);return 0;}
 if(!strcmp(name,"iso")){CHECK(transfer(1,0x82)==0);CHECK(options==0&&enables==0);return 0;}
 if(!strcmp(name,"cached-out")){CHECK(transfer(2,0x02)==0);int oldopens=opens;CHECK(transfer(2,0x82)==0);CHECK(opens==oldopens&&options==1&&enables==1);return 0;}
 if(!strcmp(name,"once")){CHECK(transfer(2,0x82)==0);CHECK(transfer(2,0x82)==0);CHECK(options==1&&enables==1&&reads==2);return 0;}
 if(!strcmp(name,"open-fail")){fail_open=1;CHECK(transfer(2,0x82)==LIBUSB_ERROR_ACCESS);CHECK(options==0&&reads==0);fail_open=0;CHECK(transfer(2,0x82)==0);CHECK(options==1&&enables==1);return 0;}
 if(!strcmp(name,"option-fail")){fail_opt=1;CHECK(transfer(2,0x82)==LIBUSB_ERROR_IO);CHECK(closes==1&&reads==0&&enables==0);fail_opt=0;CHECK(transfer(2,0x82)==0);CHECK(options==2&&enables==1);return 0;}
 if(!strcmp(name,"enable-fail")){fail_enable=1;CHECK(transfer(2,0x82)==LIBUSB_ERROR_NO_MEM);CHECK(closes==1&&reads==0);fail_enable=0;CHECK(transfer(2,0x82)==0);CHECK(options==2&&enables==2);return 0;}
 if(!strcmp(name,"release")){CHECK(transfer(2,0x82)==0);CHECK(netbsd_release_interface(&handle,0)==0);int oldopens=opens;CHECK(transfer(2,0x82)==0);CHECK(opens==oldopens+1&&options==2&&enables==2);return 0;}
 if(!strcmp(name,"close")){CHECK(transfer(2,0x82)==0);netbsd_close(&handle);CHECK(closes==2);CHECK(hp.endpoints[2]==-1&&dp.fd==-1);return 0;}
 if(!strcmp(name,"release-claim")){CHECK(transfer(2,0x82)==0);CHECK(netbsd_release_interface(&handle,0)==0);CHECK(netbsd_claim_interface(&handle,0)==0);CHECK(transfer(2,0x82)==0);CHECK(closes==1&&options==2&&enables==2);return 0;}
 if(!strcmp(name,"release-close")){CHECK(transfer(2,0x82)==0);CHECK(netbsd_release_interface(&handle,0)==0);netbsd_close(&handle);CHECK(closes==2);return 0;}
 if(!strcmp(name,"double-release")){CHECK(transfer(2,0x82)==0);CHECK(netbsd_release_interface(&handle,0)==0);CHECK(netbsd_release_interface(&handle,0)==0);CHECK(closes==1);return 0;}
 if(!strcmp(name,"claim-live")){CHECK(transfer(2,0x82)==0);CHECK(netbsd_claim_interface(&handle,0)==0);CHECK(closes==1);CHECK(transfer(2,0x82)==0);CHECK(options==2&&enables==2);return 0;}
 if(!strcmp(name,"close-empty")){netbsd_close(&handle);CHECK(closes==1);return 0;}
 if(!strcmp(name,"mask-snapshot")){setenv("LIBUSB_NETBSD_BULK_READAHEAD","81",1);CHECK(transfer(2,0x82)==0);CHECK(options==1&&enables==1);return 0;}
 if(!strcmp(name,"multiple")){netbsd_close(&handle);setenv("LIBUSB_NETBSD_BULK_READAHEAD","81,82,8F",1);CHECK(netbsd_open(&handle)==0);CHECK(transfer(2,0x81)==0);CHECK(transfer(2,0x82)==0);CHECK(transfer(2,0x8f)==0);CHECK(options==3&&enables==3);return 0;}
 return 2;
}
