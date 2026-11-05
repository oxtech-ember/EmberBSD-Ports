#!/usr/bin/env python3
import pathlib, subprocess, sys, tempfile
src=pathlib.Path(sys.argv[1]).read_text()
start=src.index('int32_t DeviceInfoV4l2::CreateCapabilityMap(')
end=src.index('\n\n',src.index('\n}', start)+2)
fn=src[start:end]
preamble=r'''
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <cassert>
#include <sstream>
#define RTC_LOG(x) std::ostringstream()
#define O_RDONLY 0
#define VIDIOC_QUERYCAP 1
#define V4L2_CAP_VIDEO_CAPTURE 1
#define kVideoCaptureUniqueNameLength 256
struct v4l2_capability { unsigned capabilities; unsigned char bus_info[32],card[32]; };
static int mode,opened,closed,queries;
int fake_open(const char *p,int) { int n=-1; sscanf(p,"/dev/video%d",&n); if(n>0)return -1; opened++;return 7; }
int fake_close(int fd) { assert(fd==7);closed++;return 0; }
int fake_ioctl(int fd,int, v4l2_capability *c) { assert(fd==7);queries++; memset(c,0,sizeof(*c)); if(mode==1)return -1; c->capabilities=mode==0?0:1; strcpy((char*)c->bus_info,mode==2?"other":"wanted");return 0; }
#define open fake_open
#define close fake_close
#define ioctl fake_ioctl
unsigned EffectiveCapabilities(const v4l2_capability& c){return c.capabilities;}
struct DeviceInfoV4l2 { std::vector<int> _captureCapabilities; int _lastUsedDeviceNameLength=0;char *_lastUsedDeviceName=nullptr; bool IsDeviceNameMatches(const char*,const char*){return false;} int FillCapabilities(int){return 7;} int32_t CreateCapabilityMap(const char*); ~DeviceInfoV4l2(){free(_lastUsedDeviceName);} };
'''
post=r'''
int main(){for(mode=0;mode<4;mode++){DeviceInfoV4l2 d; for(int i=0;i<3;i++){int result=d.CreateCapabilityMap("wanted");assert(result==(mode==3?7:-1));}assert(opened==closed);assert(queries==opened);} }
'''
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d); (p/'test.cpp').write_text(preamble+fn+post)
 subprocess.run([sys.argv[2],'-std=c++17','-g','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
