"""
test_ekf.py — Unit tests for the 15-state Error-State EKF mechanics.

Tests:
  - Covariance grows after predict (no update)
  - Covariance shrinks after measurement update
  - P stays symmetric and positive semi-definite after many predict/update cycles
  - inject_corrections resets dx to zero
  - GNSS position update pulls dx[0:3] toward observation
  - GNSS velocity update pulls dx[3:6] toward observation
  - NHC update reduces lateral/vertical velocity correction
  - ZUPT update pulls all velocity corrections toward zero
  - Adaptive GNSS noise: degraded/unavailable Q > healthy Q

All tests are pure unit tests: no dataset, no file I/O.

# EXTENSION POINT: Add tests for AI velocity update (update_ai_velocity)
#   when that measurement type is integrated in Phase 3/4.
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ins_ekf import (
    ESEKF, NominalState, NominalState, ins_propagate,
    euler_to_quat, quat_normalize, latlon_to_enu, G_MS2
)


def _make_ekf(dt: float = 0.1) -> ESEKF:
    return ESEKF(dt=dt)


def _level_state() -> NominalState:
    q0 = quat_normalize(euler_to_quat(0, 0, 0))
    return NominalState(p=np.zeros(3), v=np.zeros(3), q=q0,
                        ba=np.zeros(3), bg=np.zeros(3))


class TestEKFCovariance(unittest.TestCase):
    """Covariance (P) must grow after predict and shrink after updates."""

    def test_predict_increases_covariance_trace(self):
        """P trace must be strictly larger after predict than before."""
        ekf = _make_ekf()
        state = _level_state()
        P_trace_before = np.trace(ekf.P)

        ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))

        P_trace_after = np.trace(ekf.P)
        self.assertGreater(P_trace_after, P_trace_before,
                           msg="Predict must increase covariance trace (uncertainty grows)")

    def test_gnss_update_decreases_position_covariance(self):
        """GNSS position update must reduce position covariance (P[0:3, 0:3] trace)."""
        ekf = _make_ekf()
        state = _level_state()

        # First predict to give P some magnitude
        for _ in range(5):
            ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))

        P_pos_before = np.trace(ekf.P[0:3, 0:3])
        ekf.update_gnss_position(state, gps_enu=np.zeros(3), quality="healthy")
        P_pos_after = np.trace(ekf.P[0:3, 0:3])

        self.assertLess(P_pos_after, P_pos_before,
                        msg="GNSS position update must reduce position covariance")

    def test_nhc_update_decreases_velocity_covariance(self):
        """NHC update must reduce velocity-related covariance."""
        ekf = _make_ekf()
        state = _level_state()

        for _ in range(5):
            ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))

        P_vel_before = np.trace(ekf.P[3:6, 3:6])
        ekf.update_nhc(state)
        P_vel_after = np.trace(ekf.P[3:6, 3:6])

        self.assertLess(P_vel_after, P_vel_before,
                        msg="NHC update must reduce velocity covariance")

    def test_zupt_update_decreases_velocity_covariance(self):
        """ZUPT update must reduce velocity covariance."""
        ekf = _make_ekf()
        state = _level_state()

        for _ in range(5):
            ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))

        P_vel_before = np.trace(ekf.P[3:6, 3:6])
        ekf.update_zupt(state)
        P_vel_after = np.trace(ekf.P[3:6, 3:6])

        self.assertLess(P_vel_after, P_vel_before,
                        msg="ZUPT update must reduce velocity covariance")


class TestEKFSymmetryAndPSD(unittest.TestCase):
    """P must remain symmetric and positive semi-definite throughout."""

    def _run_cycles(self, n_predict=10, do_gnss=True, do_nhc=True):
        ekf = _make_ekf()
        state = _level_state()
        for i in range(n_predict):
            ekf.predict(state, accel_body=np.array([0.1, 0., G_MS2]),
                        gyro_body=np.array([0.01, 0., 0.]))
            if do_gnss and i % 3 == 0:
                ekf.update_gnss_position(state, gps_enu=np.random.randn(3) * 2.0)
                ekf.update_gnss_velocity(state, gps_vel_enu=np.random.randn(3) * 0.5)
            if do_nhc:
                ekf.update_nhc(state)
            state = ekf.inject_corrections(state)
        return ekf

    def test_p_remains_symmetric(self):
        """P must satisfy P == P.T (within floating point) after many cycles."""
        ekf = self._run_cycles(n_predict=20)
        np.testing.assert_allclose(ekf.P, ekf.P.T, atol=1e-10,
                                   err_msg="P must remain symmetric after predict/update cycles")

    def test_p_remains_positive_semi_definite(self):
        """All eigenvalues of P must be non-negative (PSD property)."""
        ekf = self._run_cycles(n_predict=20)
        eigenvalues = np.linalg.eigvalsh(ekf.P)
        min_eig = eigenvalues.min()
        self.assertGreaterEqual(min_eig, -1e-9,
                                msg=f"P has negative eigenvalue {min_eig:.2e} — not PSD")

    def test_p_diagonal_non_negative(self):
        """All diagonal entries of P (variances) must be ≥ 0."""
        ekf = self._run_cycles(n_predict=20)
        diag = np.diag(ekf.P)
        self.assertTrue(np.all(diag >= 0.0),
                        msg=f"P diagonal has negative entry: {diag}")


class TestEKFErrorState(unittest.TestCase):
    """dx (error state) must behave correctly."""

    def test_inject_resets_dx_to_zero(self):
        """inject_corrections must zero dx after applying corrections."""
        ekf = _make_ekf()
        state = _level_state()

        # Give dx some non-zero content via a predict
        for _ in range(3):
            ekf.predict(state, accel_body=np.array([0.5, 0., G_MS2]),
                        gyro_body=np.zeros(3))
        ekf.update_gnss_position(state, gps_enu=np.array([5.0, 3.0, 0.0]))

        # After inject, dx must be zero
        ekf.inject_corrections(state)
        np.testing.assert_allclose(ekf.dx, np.zeros(15), atol=1e-12,
                                   err_msg="dx must be zero after inject_corrections")

    def test_gnss_position_update_sets_position_correction(self):
        """GNSS position update must move position error state dx[0:3]."""
        ekf = _make_ekf()
        state = _level_state()

        # Predict first to grow P (so Kalman gain is significant)
        for _ in range(5):
            ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))

        dx_pos_before = ekf.dx[0:3].copy()
        gps_enu = np.array([10.0, 5.0, 0.0])   # GPS says we're 10 m East, 5 m North
        ekf.update_gnss_position(state, gps_enu=gps_enu)

        # dx[0:3] should now be non-zero (correction applied)
        self.assertFalse(
            np.allclose(ekf.dx[0:3], dx_pos_before, atol=1e-8),
            msg="GNSS position update must change position error state dx[0:3]"
        )

    def test_gnss_velocity_update_sets_velocity_correction(self):
        """GNSS velocity update must move velocity error state dx[3:6]."""
        ekf = _make_ekf()
        state = _level_state()
        state.v = np.array([0.0, 0.0, 0.0])

        for _ in range(5):
            ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))

        dx_vel_before = ekf.dx[3:6].copy()
        gps_vel = np.array([5.0, 3.0, 0.0])   # GPS says velocity is [5, 3, 0] m/s
        ekf.update_gnss_velocity(state, gps_vel_enu=gps_vel)

        self.assertFalse(
            np.allclose(ekf.dx[3:6], dx_vel_before, atol=1e-8),
            msg="GNSS velocity update must change velocity error state dx[3:6]"
        )

    def test_zupt_zeroes_velocity_correction(self):
        """
        ZUPT applied when state.v is large:
        the velocity correction in dx[3:6] should point toward zero velocity.
        """
        ekf = _make_ekf()
        state = _level_state()
        state.v = np.array([2.0, 1.0, 0.0])   # vehicle moving

        for _ in range(5):
            ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))

        ekf.update_zupt(state)
        # The correction should reduce the nominal velocity when injected
        # dx[3:6] innovation = -state.v → dx correction should be negative (toward 0)
        # The correction magnitude must be non-trivial
        self.assertGreater(
            np.linalg.norm(ekf.dx[3:6]), 1e-4,
            msg="ZUPT must produce non-zero velocity correction when vehicle is moving"
        )


class TestAdaptiveGNSSNoise(unittest.TestCase):
    """update_gnss_position noise scaling: degraded/unavailable → larger noise → less trust."""

    def test_healthy_trusts_gps_more_than_degraded(self):
        """
        After 'healthy' update, P[0:3,0:3] should be smaller than after
        'degraded' update (healthy noise = 1x, degraded = 3x).
        We test this by comparing two fresh EKFs with same predict but different quality.
        """
        def ekf_after_update(quality):
            ekf = _make_ekf()
            state = _level_state()
            for _ in range(5):
                ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))
            ekf.update_gnss_position(state, gps_enu=np.zeros(3), quality=quality)
            return np.trace(ekf.P[0:3, 0:3])

        trace_healthy  = ekf_after_update("healthy")
        trace_degraded = ekf_after_update("degraded")

        self.assertLess(trace_healthy, trace_degraded,
                        msg="'healthy' GPS update must leave less position uncertainty than 'degraded'")

    def test_degraded_trusts_gps_more_than_unavailable(self):
        """'degraded' should trust GPS more than 'unavailable' (3x vs 10x noise)."""
        def ekf_after_update(quality):
            ekf = _make_ekf()
            state = _level_state()
            for _ in range(5):
                ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))
            ekf.update_gnss_position(state, gps_enu=np.zeros(3), quality=quality)
            return np.trace(ekf.P[0:3, 0:3])

        trace_degraded    = ekf_after_update("degraded")
        trace_unavailable = ekf_after_update("unavailable")

        self.assertLess(trace_degraded, trace_unavailable,
                        msg="'degraded' GPS update must leave less uncertainty than 'unavailable'")


class TestNHCMechanics(unittest.TestCase):
    """NHC pseudo-measurement: lateral and vertical velocity constrained to zero."""

    def test_nhc_correction_on_lateral_velocity(self):
        """
        When vehicle has lateral velocity (v_body[1] != 0),
        NHC should produce a non-zero correction.
        """
        ekf = _make_ekf()
        state = _level_state()
        # Give the vehicle lateral velocity in nav frame
        # With identity q, nav Y = lateral → body Y
        state.v = np.array([0.0, 2.0, 0.0])  # 2 m/s lateral (body Y in nav)

        for _ in range(5):
            ekf.predict(state, accel_body=np.zeros(3), gyro_body=np.zeros(3))

        dx_before = ekf.dx.copy()
        ekf.update_nhc(state)

        self.assertFalse(
            np.allclose(ekf.dx, dx_before, atol=1e-8),
            msg="NHC must produce correction when lateral velocity is non-zero"
        )

    def test_nhc_no_effect_on_zero_lateral_velocity(self):
        """
        NHC innovation = 0 when lateral + vertical velocity is already zero.
        The correction should be near zero (only floating-point residuals).
        """
        ekf = _make_ekf()
        state = _level_state()
        state.v = np.array([5.0, 0.0, 0.0])  # only forward motion, no lateral

        # Use a fresh EKF with larger P to get non-trivial Kalman gain
        ekf.P = np.eye(15) * 10.0
        dx_before = ekf.dx.copy()
        ekf.update_nhc(state)

        # With identity q, body-Y and body-Z map to nav-Y and nav-Z.
        # state.v = [5, 0, 0] → v_body = R.T @ [5,0,0] = [5,0,0] (identity R)
        # v_body[1]=0, v_body[2]=0 → innovation = 0 → dx unchanged
        np.testing.assert_allclose(
            ekf.dx[3:6], dx_before[3:6], atol=1e-10,
            err_msg="NHC: zero lateral velocity → zero innovation → zero velocity correction"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
