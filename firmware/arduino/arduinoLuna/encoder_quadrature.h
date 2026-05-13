#ifndef UPMOON_ENCODER_QUADRATURE_H
#define UPMOON_ENCODER_QUADRATURE_H

/*
 * Quadrature decoder for wheel encoders (2-bit Gray code on pins A,B).
 * Phase must persist between samples (Arduino holds this in last_encoded_*).
 *
 * Invalid transitions (same phase, or both bits flipping at once) yield delta 0 and
 * leave *phase unchanged so bounce/noise cannot walk the decoder out of sync.
 */

#include <stdint.h>

#ifdef __cplusplus

static const int8_t kEncoderQuadratureLut[16] = {
    0, +1, -1, 0,    /* from phase 0 */
    -1, 0, 0, +1,    /* from phase 1 */
    +1, 0, 0, -1,    /* from phase 2 */
    0, -1, +1, 0     /* from phase 3 */
};

/** Returns -1, 0, or +1. Updates *phase only when a valid single-step edge occurs. */
static inline int8_t encoder_quadrature_step(int8_t *phase, int8_t encoded) {
  encoded &= 3;
  int8_t prev = *phase & 3;
  if (encoded == prev) {
    return 0;
  }
  uint8_t idx = (uint8_t)((prev << 2) | (uint8_t)encoded);
  int8_t delta = kEncoderQuadratureLut[idx];
  if (delta != 0) {
    *phase = encoded;
  }
  return delta;
}

#endif /* __cplusplus */

#endif /* UPMOON_ENCODER_QUADRATURE_H */
