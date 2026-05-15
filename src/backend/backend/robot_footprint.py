"""Nominal UPM robot footprint in ``base_link`` (+x forward, +y left).

Operator field dimensions: 0.68 m along travel (+x), 1.44 m laterally (+y).
Keep ``description/robot_properties.xacro`` numerically aligned when these change.

**Field arena** (competition / lab): 10 m × 5 m. Used as the default square map extent
for ``global_mapper`` (long axis + small margin).

**Wheel encoders** (``/sensor/encoder/*``, ``calibrated_rotary`` / dig distance): for ~10 m
arena traverses, aim for **~1–2 cm** linear resolution from quadrature counts (rule of
thumb: **≥ ~200 counts per wheel revolution** on ~0.38 m tire circumference; more if you
want sub‑cm repeatability). Keep ``dig_sequence`` ``encoder_tolerance`` to a few raw ticks.

**Separate rotary** on a dig axis: target **≤ 0.5–1°** effective angle per count after
gear reduction (coarser is often fine for dump sequencing if you only need end stops).
"""

from __future__ import annotations

import math

ROBOT_LENGTH_X_M = 0.68
ROBOT_WIDTH_Y_M = 1.44

# Field boundary (map plane axes; align ``map`` origin with your localization convention).
ARENA_LENGTH_M = 10.0
ARENA_WIDTH_M = 5.0

# Square occupancy grid edge length covering the long arena axis with a little margin.
FIELD_ARENA_GRID_EXTENT_M = max(ARENA_LENGTH_M, ARENA_WIDTH_M) * 1.05

# Conservative disc at base origin for circular cost inflation / Nav2 ``robot_radius``.
GLOBAL_ROBOT_CLEARANCE_RADIUS_M = 0.5 * math.hypot(ROBOT_LENGTH_X_M, ROBOT_WIDTH_Y_M)
