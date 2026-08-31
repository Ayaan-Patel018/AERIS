"""
test_math.py — Unit tests for pure mathematical utility functions in ins_ekf.py.

Tests:
  - latlon_to_enu       : coordinate conversion
  - quat_mult           : Hamilton product
  - quat_normalize      : unit quaternion enforcement
  - quat_to_rot         : quaternion → rotation matrix
  - euler_to_quat       : Euler → quaternion
  - rot_to_euler        : rotation matrix → Euler
  - skew                : skew-symmetric matrix

All tests are pure unit tests: no dataset, no file I/O.

# EXTENSION POINT: Add tests for new math utilities here
#   (e.g., spherical interpolation, ECEF conversions if added later).
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ins_ekf import (
    latlon_to_enu, quat_mult, quat_normalize, quat_to_rot,
    euler_to_quat, rot_to_euler, skew, DEG2RAD, RAD2DEG
)


class TestLatLonToEnu(unittest.TestCase):
    """Flat-Earth lat/lon → ENU conversion."""

    def test_origin_maps_to_zero(self):
        """Converting the origin to itself must return [0, 0, 0]."""
        result = latlon_to_enu(52.3696, -1.2993, 52.3696, -1.2993)
        np.testing.assert_allclose(result, [0.0, 0.0, 0.0], atol=1e-6)

    def test_one_degree_latitude_approx_111195m(self):
        """1° of latitude ≈ 111,195 m (flat-Earth approximation, valid < 50 km)."""
        result = latlon_to_enu(53.3696, -1.2993, 52.3696, -1.2993)
        # North component (result[1]) should be ≈ 111,195 m
        self.assertAlmostEqual(result[1], 111_195.0, delta=500.0,
                               msg="1° lat should give ~111195 m North")

    def test_east_west_direction(self):
        """Moving East (lon+) should give positive ENU East component."""
        result = latlon_to_enu(52.3696, -1.2993 + 0.01, 52.3696, -1.2993)
        self.assertGreater(result[0], 0.0,
                           msg="Eastward displacement should give positive East")
        self.assertAlmostEqual(result[1], 0.0, delta=1.0,
                               msg="Pure East move: North component should be ~0")

    def test_up_component_always_zero(self):
        """Up component is always 0 (2-D driving assumption)."""
        result = latlon_to_enu(52.38, -1.28, 52.3696, -1.2993)
        self.assertEqual(result[2], 0.0)

    def test_symmetry(self):
        """Displacement A→B should be the negative of B→A."""
        r1 = latlon_to_enu(52.38, -1.28, 52.3696, -1.2993)
        r2 = latlon_to_enu(52.3696, -1.2993, 52.38, -1.28)
        np.testing.assert_allclose(r1, -r2, atol=1.0)


class TestQuaternionMath(unittest.TestCase):
    """Quaternion algebra: mult, normalize, to_rot, from/to euler."""

    def test_mult_identity_right(self):
        """q * identity quaternion = q."""
        q = np.array([0.9239795, 0.3826834, 0.0, 0.0])  # 45° roll
        identity = np.array([1.0, 0.0, 0.0, 0.0])
        result = quat_mult(q, identity)
        np.testing.assert_allclose(result, q, atol=1e-7)

    def test_mult_identity_left(self):
        """identity * q = q."""
        q = np.array([0.9239795, 0.0, 0.3826834, 0.0])  # 45° pitch
        identity = np.array([1.0, 0.0, 0.0, 0.0])
        result = quat_mult(identity, q)
        np.testing.assert_allclose(result, q, atol=1e-7)

    def test_normalize_unit_vector(self):
        """Normalized quaternion must have unit norm."""
        q = np.array([2.0, 1.0, 0.5, 0.1])
        qn = quat_normalize(q)
        self.assertAlmostEqual(np.linalg.norm(qn), 1.0, places=12)

    def test_normalize_already_unit(self):
        """Already-unit quaternion is unchanged by normalization."""
        q = np.array([1.0, 0.0, 0.0, 0.0])
        qn = quat_normalize(q)
        np.testing.assert_allclose(qn, q, atol=1e-12)

    def test_quat_to_rot_orthogonal(self):
        """Rotation matrix from unit quaternion must satisfy R @ R.T = I."""
        q = quat_normalize(np.array([1.0, 0.2, 0.1, 0.05]))
        R = quat_to_rot(q)
        np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-10,
                                   err_msg="R @ R.T must equal I (orthogonality)")

    def test_quat_to_rot_determinant_plus_one(self):
        """Rotation matrix determinant must be +1 (proper rotation, not reflection)."""
        q = quat_normalize(np.array([0.7, 0.5, 0.3, 0.1]))
        R = quat_to_rot(q)
        self.assertAlmostEqual(np.linalg.det(R), 1.0, places=10)

    def test_identity_quat_gives_identity_rot(self):
        """Identity quaternion [1,0,0,0] → identity rotation matrix."""
        q = np.array([1.0, 0.0, 0.0, 0.0])
        R = quat_to_rot(q)
        np.testing.assert_allclose(R, np.eye(3), atol=1e-12)

    def test_euler_to_quat_to_euler_roundtrip(self):
        """euler → quat → rot → euler must recover original angles (< 90° range)."""
        for roll, pitch, yaw in [(30, 10, 45), (0, 0, 180), (-20, 5, -90)]:
            q = euler_to_quat(roll, pitch, yaw)
            q = quat_normalize(q)
            R = quat_to_rot(q)
            r_out, p_out, y_out = rot_to_euler(R)
            self.assertAlmostEqual(roll,  r_out, delta=0.01,
                                   msg=f"Roll roundtrip failed for ({roll},{pitch},{yaw})")
            self.assertAlmostEqual(pitch, p_out, delta=0.01,
                                   msg=f"Pitch roundtrip failed for ({roll},{pitch},{yaw})")
            self.assertAlmostEqual(yaw,   y_out, delta=0.01,
                                   msg=f"Yaw roundtrip failed for ({roll},{pitch},{yaw})")

    def test_yaw_rotation_moves_east(self):
        """90° yaw produces a rotation: the resulting matrix must differ from identity."""
        q = euler_to_quat(0, 0, 90)   # 90° yaw
        R = quat_to_rot(q)
        # The rotation must differ from identity (yaw has happened)
        self.assertFalse(np.allclose(R, np.eye(3), atol=0.1),
                         msg="90° yaw must produce a rotation matrix that differs from identity")


class TestSkewMatrix(unittest.TestCase):
    """Skew-symmetric matrix utility."""

    def test_antisymmetric(self):
        """S.T must equal -S (defining property of skew-symmetric)."""
        v = np.array([1.0, 2.0, 3.0])
        S = skew(v)
        np.testing.assert_allclose(S.T, -S, atol=1e-12)

    def test_diagonal_zeros(self):
        """Diagonal of a skew-symmetric matrix is always zero."""
        v = np.array([4.0, -1.0, 7.0])
        S = skew(v)
        np.testing.assert_allclose(np.diag(S), [0.0, 0.0, 0.0], atol=1e-12)

    def test_cross_product_equivalence(self):
        """skew(a) @ b must equal np.cross(a, b)."""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([4.0, -1.0, 0.5])
        np.testing.assert_allclose(skew(a) @ b, np.cross(a, b), atol=1e-12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
