/*
 * Native unit tests for encoder_quadrature.h (runs on host with g++; no Arduino libs).
 */

#include <cstdint>
#include <cstdio>
#include <cstdlib>

#include "../arduinoLuna/encoder_quadrature.h"

static int g_failures = 0;

static void check_fail(const char *file, int line, const char *expr) {
  fprintf(stderr, "FAIL %s:%d: %s\n", file, line, expr);
  ++g_failures;
}

#define CHECK(cond) \
  do { \
    if (!(cond)) check_fail(__FILE__, __LINE__, #cond); \
  } while (0)

static void test_full_cycle_clockwise() {
  int8_t phase = 0;
  long sum = 0;
  sum += encoder_quadrature_step(&phase, 1);
  CHECK(sum == 1);
  CHECK(phase == 1);
  sum += encoder_quadrature_step(&phase, 3);
  CHECK(sum == 2);
  CHECK(phase == 3);
  sum += encoder_quadrature_step(&phase, 2);
  CHECK(sum == 3);
  CHECK(phase == 2);
  sum += encoder_quadrature_step(&phase, 0);
  CHECK(sum == 4);
  CHECK(phase == 0);
}

static void test_full_cycle_counter_clockwise() {
  int8_t phase = 0;
  long sum = 0;
  sum += encoder_quadrature_step(&phase, 2);
  CHECK(sum == -1);
  CHECK(phase == 2);
  sum += encoder_quadrature_step(&phase, 3);
  CHECK(sum == -2);
  CHECK(phase == 3);
  sum += encoder_quadrature_step(&phase, 1);
  CHECK(sum == -3);
  CHECK(phase == 1);
  sum += encoder_quadrature_step(&phase, 0);
  CHECK(sum == -4);
  CHECK(phase == 0);
}

static void test_illegal_two_bit_jump_preserves_phase() {
  int8_t phase = 0;
  int8_t d = encoder_quadrature_step(&phase, 3);
  CHECK(d == 0);
  CHECK(phase == 0);
}

static void test_bounce_then_real_edge() {
  /* Illegal 0 -> 3 does not corrupt phase; next valid edge still counts correctly. */
  int8_t phase = 0;
  CHECK(encoder_quadrature_step(&phase, 3) == 0);
  CHECK(phase == 0);
  CHECK(encoder_quadrature_step(&phase, 1) == 1);
  CHECK(phase == 1);
}

static void test_repeat_same_phase_no_accumulation() {
  int8_t phase = 2;
  long sum = 0;
  for (int i = 0; i < 20; ++i) {
    sum += encoder_quadrature_step(&phase, 2);
  }
  CHECK(sum == 0);
  CHECK(phase == 2);
}

/*
 * Regression: bogus transitions must not advance phase.
 * Sequence used to advance phase even when delta was 0, letting later edges oscillate the count.
 */
static void test_illegal_transition_does_not_advance_phase_for_next_sample() {
  int8_t phase = 1;
  CHECK(encoder_quadrature_step(&phase, 2) == 0); /* illegal: 01 -> 10 */
  CHECK(phase == 1);
  CHECK(encoder_quadrature_step(&phase, 3) == 1); /* valid: 01 -> 11 */
  CHECK(phase == 3);
}

static void test_masked_high_bits_in_encoded() {
  int8_t phase = 0;
  CHECK(encoder_quadrature_step(&phase, static_cast<int8_t>(5)) == 1); /* 5 & 3 == 1 */
  CHECK(phase == 1);
}

int main() {
  test_full_cycle_clockwise();
  test_full_cycle_counter_clockwise();
  test_illegal_two_bit_jump_preserves_phase();
  test_bounce_then_real_edge();
  test_repeat_same_phase_no_accumulation();
  test_illegal_transition_does_not_advance_phase_for_next_sample();
  test_masked_high_bits_in_encoded();

  if (g_failures != 0) {
    fprintf(stderr, "%d assertion(s) failed.\n", g_failures);
    return EXIT_FAILURE;
  }
  puts("encoder_quadrature tests OK");
  return EXIT_SUCCESS;
}
