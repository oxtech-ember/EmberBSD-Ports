/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Exercise the real pinned KiCad class. */
#include <sys/types.h>
#include <sys/wait.h>

#include <atomic>
#include <chrono>
#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <map>
#include <mutex>
#include <string>
#include <thread>
#include <unistd.h>

#include <kinng.h>
#include <nng/nng.h>
#include <nng/protocol/reqrep0/req.h>

static std::atomic<int> server_id{ -1 };
static std::atomic<unsigned> receives{ 0 }, receive_calls{ 0 }, closes{ 0 };
static std::atomic<bool> start_failed{ false }, listener_ready{ false };
static std::atomic<bool> inject_start_failure{ false };
static std::mutex allocations_mutex;
static std::map<void*, size_t> allocations;
static nng_socket owned_server = NNG_SOCKET_INITIALIZER;

extern "C" {
int __real_nng_rep0_open( nng_socket* );
int __real_nng_close( nng_socket );
int __real_nng_listener_start( nng_listener, int );
int __real_nng_recv( nng_socket, void*, size_t*, int );
void __real_nng_free( void*, size_t );

int __wrap_nng_rep0_open( nng_socket* socket )
{
    int result = __real_nng_rep0_open( socket );
    if( result == 0 )
    {
        owned_server = *socket;
        server_id.store( nng_socket_id( *socket ) );
    }
    return result;
}

int __wrap_nng_close( nng_socket socket )
{
    if( nng_socket_id( socket ) == server_id.load() )
        closes.fetch_add( 1 );
    return __real_nng_close( socket );
}

int __wrap_nng_listener_start( nng_listener listener, int flags )
{
    if( inject_start_failure.load() )
    {
        start_failed.store( true );
        return NNG_EADDRINUSE;
    }
    int result = __real_nng_listener_start( listener, flags );
    if( result == 0 )
        listener_ready.store( true );
    return result;
}

int __wrap_nng_recv( nng_socket socket, void* data, size_t* size, int flags )
{
    bool server = nng_socket_id( socket ) == server_id.load();
    if( server )
        receive_calls.fetch_add( 1 );
    int result = __real_nng_recv( socket, data, size, flags );
    if( server && result == 0 && ( flags & NNG_FLAG_ALLOC ) != 0 )
    {
        std::lock_guard<std::mutex> lock( allocations_mutex );
        allocations.emplace( *static_cast<void**>( data ), *size );
        receives.fetch_add( 1 );
    }
    return result;
}

void __wrap_nng_free( void* data, size_t size )
{
    {
        std::lock_guard<std::mutex> lock( allocations_mutex );
        allocations.erase( data );
    }
    __real_nng_free( data, size );
}
}

static bool wait_for( const std::function<bool()>& predicate )
{
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds( 2 );
    while( !predicate() )
    {
        if( std::chrono::steady_clock::now() >= deadline )
            return false;
        std::this_thread::sleep_for( std::chrono::milliseconds( 2 ) );
    }
    return true;
}

static bool okay( const char* operation, int error )
{
    if( error == 0 )
        return true;
    std::fprintf( stderr, "%s: %s\n", operation, nng_strerror( error ) );
    return false;
}

static void release_baseline_allocations()
{
    std::lock_guard<std::mutex> lock( allocations_mutex );
    for( const auto& allocation : allocations )
        __real_nng_free( allocation.first, allocation.second );
    allocations.clear();
}

static int exchange_case( const std::string& url, bool stop_without_reply )
{
    const std::string request( "request\0bytes", 13 );
    const std::string reply( "reply\0bytes", 11 );
    nng_socket client = NNG_SOCKET_INITIALIZER;
    bool client_open = false;
    int result = 0;
    {
        KINNG_REQUEST_SERVER server( url );
        if( !wait_for( [] { return listener_ready.load(); } ) )
        {
            std::fputs( "No real listener ready before client dial\n", stderr );
            result = 1;
        }
        client_open = result == 0 && nng_req0_open( &client ) == 0;
        if( !client_open ||
            !okay( "REQ recv deadline", nng_socket_set_ms( client, NNG_OPT_RECVTIMEO, 1000 ) ) ||
            !okay( "REQ send deadline", nng_socket_set_ms( client, NNG_OPT_SENDTIMEO, 1000 ) ) ||
            !okay( "REQ dial", nng_dial( client, url.c_str(), nullptr, NNG_FLAG_NONBLOCK ) ) )
            result = 1;
        for( unsigned i = 0; result == 0 && i < ( stop_without_reply ? 1U : 16U ); ++i )
        {
            if( !okay( "request send", nng_send( client, const_cast<char*>( request.data() ),
                                                request.size(), 0 ) ) )
            {
                result = 1;
                break;
            }
            if( stop_without_reply )
            {
                if( !wait_for( [] { return receives.load() == 1; } ) )
                {
                    std::fputs( "No real server receive before Stop\n", stderr );
                    result = 1;
                    break;
                }
                std::puts( "STOP_ENTERED_AFTER_REAL_RECEIVE" );
                std::fflush( stdout );
                server.Stop();
                std::puts( "STOP_RETURNED_WITHOUT_REPLY" );
                break;
            }
            server.Reply( reply );
            void* data = nullptr;
            size_t size = 0;
            if( !okay( "reply receive", nng_recv( client, &data, &size, NNG_FLAG_ALLOC ) ) )
            {
                result = 1;
                break;
            }
            bool equal = size == reply.size() && std::memcmp( data, reply.data(), size ) == 0;
            nng_free( data, size );
            if( !equal )
                result = 1;
        }
        server.Stop();
    }
    if( client_open && !okay( "REQ close", nng_close( client ) ) )
        result = 1;
    size_t outstanding;
    {
        std::lock_guard<std::mutex> lock( allocations_mutex );
        outstanding = allocations.size();
    }
    std::printf( "real_server_allocations=%u outstanding=%zu closes=%u\n",
                 receives.load(), outstanding, closes.load() );
    if( outstanding != 0 || closes.load() != 1 ||
        receives.load() != ( stop_without_reply ? 1U : 16U ) )
        result = 1;
    /* Preserve the ownership witness, then release baseline leaks for teardown. */
    release_baseline_allocations();
    nng_fini();
    return result;
}

static int listener_error_case( const std::string& url, bool start_error )
{
    inject_start_failure.store( start_error );
    {
        KINNG_REQUEST_SERVER server( start_error ? url : "unknown-kinng-test://invalid" );
        if( !wait_for( [start_error] {
                return start_error ? start_failed.load() &&
                    ( receive_calls.load() != 0 || closes.load() != 0 ) : server_id.load() != -1;
            } ) )
            return 2;
        server.Stop();
    }
    unsigned closed = closes.load();
    unsigned called = receive_calls.load();
    std::printf( "listener_%s closes=%u receive_calls=%u\n",
                 start_error ? "start" : "create", closed, called );
    if( closed == 0 )
        __real_nng_close( owned_server );
    nng_fini();
    return closed == 1 && called == 0 ? 0 : 1;
}

static int stop_subprocess( const std::string& url )
{
    std::fflush( nullptr );
    pid_t child = fork();
    if( child < 0 )
        return 2;
    if( child == 0 )
    {
        int result = exchange_case( url, true );
        std::fflush( nullptr );
        _exit( result );
    }
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds( 3 );
    int status = 0;
    for( ;; )
    {
        pid_t waited = waitpid( child, &status, WNOHANG );
        if( waited == child )
            return WIFEXITED( status ) ? WEXITSTATUS( status ) : 2;
        if( waited < 0 )
        {
            if( errno == EINTR )
                continue;
            return 2;
        }
        if( std::chrono::steady_clock::now() >= deadline )
        {
            /* Only this exact owned subprocess can reach this branch. */
            kill( child, SIGKILL );
            if( waitpid( child, &status, 0 ) != child )
                return 2;
            std::puts( "STOP_SUBPROCESS_DEADLINE" );
            return 124;
        }
        std::this_thread::sleep_for( std::chrono::milliseconds( 2 ) );
    }
}

int main( int argc, char** argv )
{
    if( argc != 2 )
        return 2;
    alarm( 12 );
    char directory[] = "kinng.XXXXXX";
    char cwd[1024];
    if( !getcwd( cwd, sizeof( cwd ) ) || !mkdtemp( directory ) )
        return 2;
    std::string path = std::string( cwd ) + "/" + directory + "/socket";
    std::string url = "ipc://" + path;
    int result = 2;
    if( path.size() < 100 && std::strcmp( nng_version(), "1.12.3" ) == 0 )
    {
        if( std::strcmp( argv[1], "ownership" ) == 0 )
            result = exchange_case( url, false );
        else if( std::strcmp( argv[1], "stop" ) == 0 )
            result = stop_subprocess( url );
        else if( std::strcmp( argv[1], "create-error" ) == 0 )
            result = listener_error_case( url, false );
        else if( std::strcmp( argv[1], "start-error" ) == 0 )
            result = listener_error_case( url, true );
    }
    if( unlink( path.c_str() ) != 0 && errno != ENOENT )
        result = 2;
    if( rmdir( directory ) != 0 )
        result = 2;
    alarm( 0 );
    return result;
}
