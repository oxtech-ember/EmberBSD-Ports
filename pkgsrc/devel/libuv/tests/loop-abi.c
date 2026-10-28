#ifdef NDEBUG
#error This test requires active assertions
#endif

#include <assert.h>
#include <uv.h>

_Static_assert(UV_LOOP_BLOCK_SIGNAL == 0, "block signal ABI changed");
_Static_assert(UV_METRICS_IDLE_TIME == 1, "metrics ABI changed");
_Static_assert(UV_LOOP_USE_IO_URING_SQPOLL == 2, "io_uring ABI changed");
_Static_assert(UV_LOOP_INTERRUPT_ON_IO_CHANGE == 3, "interrupt ABI changed");

static void
on_timer(uv_timer_t *timer)
{
  uv_close((uv_handle_t *) timer, NULL);
}

int
main(void)
{
  uv_loop_t loop;
  uv_timer_t timer;

  assert(uv_loop_init(&loop) == 0);
  assert(uv_loop_configure(&loop, UV_LOOP_INTERRUPT_ON_IO_CHANGE) == 0);
  uv_loop_interrupt_suspend(&loop);
  uv_loop_interrupt_suspend(&loop);
  assert(uv_timer_init(&loop, &timer) == 0);
  assert(uv_timer_start(&timer, on_timer, 0, 0) == 0);
  uv_loop_interrupt_resume(&loop);
  uv_loop_interrupt_resume(&loop);
  assert(uv_run(&loop, UV_RUN_DEFAULT) == 0);
  assert(uv_loop_close(&loop) == 0);
  return 0;
}
