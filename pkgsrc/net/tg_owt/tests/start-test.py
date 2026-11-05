import pathlib,re,subprocess,sys,tempfile
s=pathlib.Path(sys.argv[1]).read_text(); ctor=s[s.index('VideoCaptureModuleV4L2::VideoCaptureModuleV4L2()'):s.index('int32_t VideoCaptureModuleV4L2::Init(')]; dtor=s[s.index('VideoCaptureModuleV4L2::~VideoCaptureModuleV4L2()'):s.index('bool VideoCaptureModuleV4L2::CaptureStarted()')]; methods=ctor+dtor
prefix=pathlib.Path(__file__).resolve().with_name('buffer-test.py').read_text().split("pre=r'''",1)[1].split("'''",1)[0]
prefix=prefix[:prefix.index('struct VideoCaptureCapability')]
fmts=sorted(set(re.findall(r'V4L2_PIX_FMT_[A-Z0-9]+',methods))); prefix+='\n'+''.join('#define %s %d\n'%(n,i+1) for i,n in enumerate(fmts))
prefix+=r'''
#include <utility>
#include <cstdint>
#include <cstdio>
#include <string>
#define RTC_DCHECK_RUN_ON(x) ((void)0)
#define RTC_DCHECK_NOTREACHED() assert(false)
#define O_RDWR 1
#define O_NONBLOCK 2
#define VIDIOC_ENUM_FMT 6
#define VIDIOC_S_FMT 7
#define VIDIOC_G_PARM 8
#define VIDIOC_S_PARM 9
#define VIDIOC_STREAMON 10
#define V4L2_CAP_TIMEPERFRAME 1
struct v4l2_fmtdesc {unsigned index; int type;unsigned pixelformat; char description[32];};
struct v4l2_format {int type; struct {struct {int sizeimage,width,height;unsigned pixelformat;} pix;} fmt;};
struct v4l2_streamparm {int type; struct {struct {int capability;struct{int numerator,denominator;} timeperframe;} capture;} parm;};
enum class VideoType{kYUY2,kI420,kYV12,kUYVY,kNV12,kRGB24,kBGR24,kRGB565,kARGB,kBGRA,kABGR,kMJPEG};
struct VideoCaptureCapability {int width=640,height=480,maxFPS=30;VideoType videoType=VideoType::kI420;bool operator==(const VideoCaptureCapability&o)const{return width==o.width;}};
struct Buffer {void*start;unsigned length;}; struct Mutex{}; struct MutexLock {MutexLock(Mutex*){}};
struct VideoCaptureImpl{VideoCaptureCapability _requestedCapability;};
namespace cricket {const char* GetFourccName(unsigned){return "fmt";}}
namespace rtc {enum class ThreadPriority{kHigh}; struct ThreadAttributes{ThreadAttributes& SetPriority(ThreadPriority){return *this;}};struct PlatformThread{bool active=false;bool empty(){return !active;}void Finalize(){active=false;}template<class F>static PlatformThread SpawnJoinable(F,const char*,ThreadAttributes){return {true};}};}
namespace absl {template<class F>struct Cleanup {F fn;bool active=true;~Cleanup(){if(active)fn();}void Cancel()&&{active=false;}};template<class F>Cleanup<F> MakeCleanup(F f){return {f};}}
int failop,failindex,maps,unmaps,closes,opens;bool stopped;
int open(const char*,int,...){if(failop==11)return -1;opens++;return 7;}
int ioctl(int,int op,void *p){if(op==VIDIOC_ENUM_FMT){auto f=(v4l2_fmtdesc*)p;if(failop==op||f->index)return -1;f->pixelformat=V4L2_PIX_FMT_YUV420;return 0;}if(op==VIDIOC_REQBUFS){if(failop==op)return -1;((v4l2_requestbuffers*)p)->count=3;return 0;}if(op==VIDIOC_STREAMOFF){if(failop==op)return -1;stopped=true;return 0;}if(op==VIDIOC_G_PARM)return -1;if(op==VIDIOC_S_FMT||op==VIDIOC_STREAMON){if(failop==op)return -1;if(op==VIDIOC_STREAMON)stopped=false;return 0;}auto b=(v4l2_buffer*)p;if(op==failop && int(b->index)==failindex)return -1;b->length=1;b->m.offset=b->index;return 0;}
void*mmap(void*,unsigned,int,int,int,int off){if(failop==5 && off==failindex)return MAP_FAILED;maps++;return new char[1];}int munmap(void*p,unsigned){assert(stopped);unmaps++;delete[] (char*)p;return 0;}int close(int){closes++;stopped=true;return 0;}
struct VideoCaptureModuleV4L2:VideoCaptureImpl{rtc::PlatformThread _captureThread;Mutex capture_lock_;bool quit_;int _deviceId,_deviceFd,_buffersMapped,_buffersAllocatedByDevice;VideoCaptureCapability configured_capability_;bool _streaming,_captureStarted;Buffer*_pool;VideoCaptureModuleV4L2();~VideoCaptureModuleV4L2();int32_t StartCapture(const VideoCaptureCapability&);int32_t StopCapture();bool AllocateVideoBuffers();bool DeAllocateVideoBuffers();void ReleaseDevice();bool CaptureProcess(){return false;}};
'''
post=r'''
int main(){int ops[]={11,6,7,1,2,3,5,10};for(int op:ops)for(int idx=0;idx<3;idx++){maps=unmaps=closes=opens=0;stopped=true;failop=op;failindex=idx;{VideoCaptureModuleV4L2 v;assert(!v._streaming&&!v.quit_);VideoCaptureCapability c;assert(v.StartCapture(c)==-1);assert(opens==closes && maps==unmaps);failop=0;assert(v.StartCapture(c)==0);assert(v.StopCapture()==0);assert(v.StopCapture()==0);}assert(opens==closes && maps==unmaps);}}
'''
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);(p/'test.cpp').write_text(prefix+methods+post);subprocess.run([sys.argv[2],'-std=c++17','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
