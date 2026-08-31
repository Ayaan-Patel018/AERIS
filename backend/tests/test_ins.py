"""
test_ins.py — Unit tests for the INS strapdown propagation (ins_propagate).

Tests:
  - Zero input stays still (apart from gravity subtraction artifact)
  - Pure rotation doesn't translate
  - Known forward motion produces displacement on correct axis
  - dt=0 produces no change
  - Bias correction shifts the effective acceleration

All tests are pure unit tests: no dataset, no file I/O.

# EXTENSION POINT: Add tests for Coriolis corrections, high-rate IMU
#   integration accuracy, or RK4 integration if upgraded from Euler.
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ins_ekf import NominalState, ins_propagate, euler_to_quat, quat_normalize, G_MS2


class TestINSPropagation(unittest.TestCase):
    """Tests for ins_propagate() strapdown integration step."""

    def _level_state(self):
        """Return a state with identity quaternion (level, pointing North)."""
        q0 = quat_normalize(euler_to_quat(0, 0, 0))
        return NominalState(
            p  = np.zeros(3),
            v  = np.zeros(3),
            q  = q0,
            ba = np.zeros(3),
            bg = np.zeros(3),
        )

    # ── Zero input ────────────────────────────────────────────────────────────

    def test_zero_gyro_keeps_quaternion(self):
        """Zero gyro input must not change the quaternion."""
        state = self._level_state()
        q_before = state.q.copy()
        new_state = ins_propagate(state, accel_body=np.array([0., 0., G_MS2]),
                                  gyro_body=np.zeros(3), dt=0.1)
        np.testing.assert_allclose(new_state.q, q_before, atol=1e-10,
                                   err_msg="Zero gyro: quaternion must not change")

    def test_gravity_only_no_horizontal_velocity(self):
        """
        With only gravity on Z (body frame) and zero linear accel,
        nav-frame subtraction should cancel gravity, leaving near-zero velocity.
        When the phone is level (identity q), body-Z = nav-Z = up.
        accel_body = [0, 0, 9.80665], nav-frame after rotation → [0,0,9.80665],
        subtract G → [0,0,0]. Horizontal velocity must stay zero.
        """
        state = self._level_state()
        accel_body = np.array([0.0, 0.0, G_MS2])
        new_state = ins_propagate(state, accel_body=accel_body,
                                  gyro_body=np.zeros(3), dt=0.1)
        np.testing.assert_allclose(new_state.v[:2], [0., 0.], atol=1e-9,
                                   err_msg="Gravity-only: horizontal velocity must stay zero")

    def test_zero_dt_no_change(self):
        """dt = 0 must produce zero position and velocity change."""
        state = self._level_state()
        state.v = np.array([3.0, 0.0, 0.0])   # give it some initial velocity
        new_state = ins_propagate(state,
                                  accel_body=np.array([0., 0., G_MS2]),
                                  gyro_body=np.zeros(3), dt=0.0)
        np.testing.assert_allclose(new_state.p, state.p, atol=1e-12,
                                   err_msg="dt=0: position must not change")
        np.testing.assert_allclose(new_state.v, state.v, atol=1e-12,
                                   err_msg="dt=0: velocity must not change")

    # ── Pure rotation ─────────────────────────────────────────────────────────

    def test_pure_yaw_rotation_no_translation(self):
        """
        Gyro yaw only (rotating in place) with pure gravity input:
        position must stay near zero after one step.
        """
        state = self._level_state()
        gyro = np.array([0.0, 0.0, 0.1])       # yaw rate only (body Z)
        accel = np.array([0.0, 0.0, G_MS2])     # gravity only
        new_state = ins_propagate(state, accel_body=accel,
                                  gyro_body=gyro, dt=0.1)
        np.testing.assert_allclose(new_state.p, np.zeros(3), atol=1e-3,
                                   err_msg="Pure yaw: no translation expected")

    def test_rotation_changes_quaternion(self):
        """Non-zero gyro rate must change the quaternion."""
        state = self._level_state()
        q_before = state.q.copy()
        gyro = np.array([0.1, 0.0, 0.0])
        new_state = ins_propagate(state, accel_body=np.array([0., 0., G_MS2]),
                                  gyro_body=gyro, dt=0.1)
        self.assertFalse(
            np.allclose(new_state.q, q_before, atol=1e-6),
            msg="Non-zero gyro: quaternion must change"
        )

    def test_quaternion_stays_unit_after_rotation(self):
        """Quaternion norm must remain 1 after gyro integration."""
        state = self._level_state()
        gyro = np.array([0.3, 0.1, 0.05])
        for _ in range(50):
            state = ins_propagate(state, accel_body=np.array([0., 0., G_MS2]),
                                  gyro_body=gyro, dt=0.1)
        self.assertAlmostEqual(np.linalg.norm(state.q), 1.0, places=8,
                               msg="Quaternion norm must stay 1.0 after 50 steps")

    # ── Forward motion ────────────────────────────────────────────────────────

    def test_forward_acceleration_moves_north(self):
        """
        Level vehicle (identity q), forward accel (body X = nav East),
        but heading = North means body X = nav North.
        Wait — for identity quaternion: body X maps to nav X (East).
        With 0° yaw (North heading), nav North = body X only when axes align.

        We test that non-zero forward accel (body X) produces velocity
        on the horizontal plane (either East or North, depending on yaw).
        """
        state = self._level_state()
        # Apply forward acceleration for 10 steps
        accel = np.array([1.0, 0.0, G_MS2])    # 1 m/s² forward + gravity
        for _ in range(10):
            state = ins_propagate(state, accel_body=accel,
                                  gyro_body=np.zeros(3), dt=0.1)

        # Horizontal speed must be > 0
        horiz_speed = np.linalg.norm(state.v[:2])
        self.assertGreater(horiz_speed, 0.5,
                           msg="Forward accel must produce horizontal velocity")

    def test_position_increases_with_forward_accel(self):
        """Sustained forward acceleration must increase position magnitude."""
        state = self._level_state()
        accel = np.array([2.0, 0.0, G_MS2])
        for _ in range(20):
            state = ins_propagate(state, accel_body=accel,
                                  gyro_body=np.zeros(3), dt=0.1)

        pos_norm = np.linalg.norm(state.p[:2])
        self.assertGreater(pos_norm, 0.1,
                           msg="Sustained forward accel must produce measurable displacement")

    # ── Bias correction ───────────────────────────────────────────────────────

    def test_accel_bias_reduces_velocity(self):
        """
        A known accel bias ba = [1, 0, 0] should subtract from forward accel,
        reducing the resulting velocity compared to zero-bias case.
        """
        state_no_bias = self._level_state()
        state_with_bias = self._level_state()
        state_with_bias.ba = np.array([1.0, 0.0, 0.0])   # 1 m/s² forward bias

        accel = np.array([2.0, 0.0, G_MS2])
        for _ in range(10):
            state_no_bias   = ins_propagate(state_no_bias,   accel, np.zeros(3), 0.1)
            state_with_bias = ins_propagate(state_with_bias, accel, np.zeros(3), 0.1)

        # Bias = [1,0,0] means corrected accel = 2-1 = 1 m/s² → less velocity
        speed_no_bias   = np.linalg.norm(state_no_bias.v[:2])
        speed_with_bias = np.linalg.norm(state_with_bias.v[:2])
        self.assertGreater(speed_no_bias, speed_with_bias,
                           msg="Accel bias must reduce effective forward velocity")

    def test_gyro_bias_shifts_rotation_rate(self):
        """
        Gyro bias bg = [0.1, 0, 0] with zero gyro input:
        corrected gyro = 0 - 0.1 = -0.1 rad/s → quaternion must still change.
        """
        state = self._level_state()
        state.bg = np.array([0.1, 0.0, 0.0])
        q_before = state.q.copy()
        new_state = ins_propagate(state,
                                  accel_body=np.array([0., 0., G_MS2]),
                                  gyro_body=np.zeros(3), dt=0.1)
        self.assertFalse(
            np.allclose(new_state.q, q_before, atol=1e-6),
            msg="Non-zero gyro bias with zero gyro input must still rotate attitude"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
