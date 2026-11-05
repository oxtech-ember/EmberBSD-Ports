import pathlib, subprocess, sys, tempfile
s=pathlib.Path(sys.argv[1]).read_text(); a=s.index('bool VideoCaptureModuleV4L2::AllocateVideoBuffers()'); b=s.index('bool VideoCaptureModuleV4L2::CaptureStarted()',a); methods=s[a:b]
pre=r'''
#include <cassert>
#include <cerrno>
#include <cstring>
#include <new>
#include <sstream>
#include <vector>
#define RTC_CHECK_RUNS_SERIALIZED(x) ((void)0)
#define RTC_LOG(x) std::ostringstream()
#define PROT_READ 1
#define PROT_WRITE 2
#define MAP_SHARED 1
#define MAP_FAILED ((void*)-1)
#define VIDIOC_REQBUFS 1
#define VIDIOC_QUERYBUF 2
#define VIDIOC_QBUF 3
#define VIDIOC_STREAMOFF 4
#define V4L2_MEMORY_MMAP 1
#define kNoOfV4L2Bufffers 3
enum v4l2_buf_type { V4L2_BUF_TYPE_VIDEO_CAPTURE=1 };
struct v4l2_requestbuffers {int type,memory; unsigned count;};
struct v4l2_buffer {int type,memory; unsigned index,length; struct {int offset;} m;};
struct VideoCaptureCapability {};
struct Buffer { void *start; unsigned length; };
int failop, failindex, maps,unmaps,closes,events; bool stopped;
int ioctl(int,int op,void *ptr){if(op==VIDIOC_REQBUFS){if(failop==op)return -1;((v4l2_requestbuffers*)ptr)->count=3;return 0;} if(op==VIDIOC_STREAMOFF){events++; if(failop==op)return -1;stopped=true;return 0;}auto b=(v4l2_buffer*)ptr; if(op==failop && int(b->index)==failindex)return -1;b->length=1;b->m.offset=b->index;return 0;}
void *mmap(void*,unsigned,int,int,int,int off){if(failop==5 && off==failindex)return MAP_FAILED;maps++;return new char[1];}
int munmap(void*p,unsigned){assert(stopped);events++;unmaps++;delete[] (char*)p;return 0;}
int close(int){events++;closes++;stopped=true;return 0;}
struct VideoCaptureModuleV4L2 {int _deviceFd=7,_buffersMapped=0;bool _streaming=false,_captureStarted=false;Buffer *_pool=nullptr;VideoCaptureCapability _requestedCapability,configured_capability_;bool AllocateVideoBuffers();bool DeAllocateVideoBuffers();void ReleaseDevice();};
'''
post=r'''
int main(){for(int op=1;op<=5;op++){for(int idx=0;idx<3;idx++){maps=unmaps=closes=events=0;stopped=true;failop=op;failindex=idx;VideoCaptureModuleV4L2 v;bool ok=v.AllocateVideoBuffers();if(op==1||op==2||op==3||op==5)assert(!ok);if(op==4){assert(ok);v._streaming=true;stopped=false;}v.ReleaseDevice();v.ReleaseDevice();assert(maps==unmaps);assert(closes==1);assert(v._pool==nullptr && v._buffersMapped==0 && v._deviceFd==-1);}}}
'''
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);(p/'test.cpp').write_text(pre+methods+post);subprocess.run([sys.argv[2],'-std=c++17','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
