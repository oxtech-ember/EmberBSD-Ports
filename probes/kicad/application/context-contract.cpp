// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Exercise KiCad's actual libcontext ABI.
#include <libcontext.h>
#include <cstdio>
#include <cstdlib>
#ifdef EMBER_VALGRIND
#include <valgrind/valgrind.h>
#endif

namespace
{
libcontext::fcontext_t caller;
libcontext::fcontext_t worker;
constexpr std::size_t stackSize = 128 * 1024;

void fail()
{
    std::fputs( "libcontext contract failed\n", stderr );
    std::exit( 1 );
}

void exercise( intptr_t initial )
{
    double sum = 0.5;
    intptr_t next = initial;
    for( intptr_t count = 1; count <= 1000; ++count )
    {
        if( next != count )
            fail();
        sum += static_cast<double>( count );
        next = libcontext::jump_fcontext( &worker, caller, count * 3 );
        if( sum != 0.5 + static_cast<double>( count * ( count + 1 ) ) / 2.0 )
            fail();
    }
    if( next != 1001 || sum != 500500.5 )
        fail();
    libcontext::jump_fcontext( &worker, caller, 500500 );
    fail(); // A completed context must not resume.
}
}

int main()
{
    for( int cycle = 0; cycle < 3; ++cycle )
    {
        auto* stack = static_cast<unsigned char*>( std::calloc( stackSize, 1 ) );
        if( !stack )
            fail();
#ifdef EMBER_VALGRIND
        const unsigned stackId = VALGRIND_STACK_REGISTER( stack, stack + stackSize );
#endif
        worker = libcontext::make_fcontext( stack + stackSize, stackSize, exercise );
        for( intptr_t value = 1; value <= 1000; ++value )
        {
            if( libcontext::jump_fcontext( &caller, worker, value ) != value * 3 )
                fail();
        }
        if( libcontext::jump_fcontext( &caller, worker, 1001 ) != 500500 )
            fail();
        libcontext::release_fcontext( worker );
#ifdef EMBER_VALGRIND
        VALGRIND_STACK_DEREGISTER( stackId );
#endif
        std::free( stack );
        worker = nullptr;
        caller = nullptr;
    }
    std::puts( "PASS: 3 context lifecycles, 3003 round trips, integer and FP state" );
    return 0;
}
