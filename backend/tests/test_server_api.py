"""
test_server_api.py — End-to-end integration tests for FastAPI backend server & InESEKF pipeline
"""

import pytest
import numpy as np
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import app
from ins_ekf import InESEKF, ESEKF, NominalState, quat_to_rot

try:
    from fastapi.testclient import TestClient
    TEST_CLIENT_AVAILABLE = True
except ImportError:
    TEST_CLIENT_AVAILABLE = False


@pytest.mark.skipif(not TEST_CLIENT_AVAILABLE, reason="fastapi.testclient (httpx) not installed")
class TestServerEndpoints:
    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        res = self.client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "IO-VNBD S3b" in data["dataset"]
        assert data["s_rows"] > 1000
        assert data["v_rows"] > 1000

    def test_run_scenario_endpoint(self):
        payload = {
            "outage_start": 200.0,
            "outage_end": 260.0,
            "use_rts": True
        }
        res = self.client.post("/run", json=payload)
        assert res.status_code == 200
        data = res.json()

        # Check all 4 layers are present
        assert "ground_truth" in data
        assert "gnss_only" in data
        assert "fused_output" in data
        assert "smoothed_output" in data

        gt = data["ground_truth"]
        gnss = data["gnss_only"]
        fused = data["fused_output"]
        smoothed = data["smoothed_output"]

        assert len(gt) > 1000
        assert len(gnss) == len(gt)
        assert len(fused) == len(gt)
        assert len(smoothed) == len(gt)

        # Check point schema
        pt0 = fused[0]
        assert "x" in pt0 and "y" in pt0 and "t" in pt0
        assert "lat" in pt0 and "lon" in pt0
        assert "status" in pt0
        assert "uncertainty" in pt0
        assert "velocity" in pt0
        assert "heading" in pt0
        assert "cov_xx" in pt0 and "cov_yy" in pt0 and "cov_xy" in pt0

        # Check covariance ellipse properties
        cov_xx = np.array([p["cov_xx"] for p in fused])
        cov_yy = np.array([p["cov_yy"] for p in fused])
        cov_xy = np.array([p["cov_xy"] for p in fused])

        assert np.all(cov_xx >= 0)
        assert np.all(cov_yy >= 0)
        assert np.all(np.isfinite(cov_xy))

        # Check that outage points exist and have status 'outage'
        statuses = [p["status"] for p in fused]
        assert "outage" in statuses or "unavailable" in statuses

        # Check uncertainty grows during outage
        total_dur = data["total_duration"]
        times_s = np.array([p["t"] * total_dur for p in fused])
        outage_mask = (times_s >= 200.0) & (times_s <= 260.0)
        healthy_mask = (times_s < 190.0) & (times_s > 10.0)

        unc_outage_mean = np.mean([fused[i]["uncertainty"] for i in np.where(outage_mask)[0]])
        unc_healthy_mean = np.mean([fused[i]["uncertainty"] for i in np.where(healthy_mask)[0]])
        assert unc_outage_mean > unc_healthy_mean, "Uncertainty must grow during GNSS outage"


class TestInESEKFMath:
    def test_left_invariant_jacobian_structure(self):
        """Verify InESEKF computes navigation-frame skew Jacobians correctly."""
        inekf = InESEKF(dt=0.1)
        state = NominalState(
            p=np.zeros(3),
            v=np.array([5.0, 0.0, 0.0]),
            q=np.array([1.0, 0.0, 0.0, 0.0]), # identity rotation
            ba=np.zeros(3),
            bg=np.zeros(3)
        )
        accel = np.array([0.0, 0.0, 9.81])
        gyro = np.array([0.0, 0.0, 0.1])

        inekf.predict(state, accel, gyro)
        F = inekf.last_F

        assert F.shape == (15, 15)
        # Check nav-frame position-attitude coupling F[0:3, 6:9] == -[v x] dt
        expected_v_skew = np.array([
            [0.0, 0.0, 0.0],
            [0.0, 0.0, -5.0],
            [0.0, 5.0, 0.0]
        ]) * 0.1
        np.testing.assert_allclose(F[0:3, 6:9], -expected_v_skew, atol=1e-5)

        # Check covariance positive definiteness
        eigenvals = np.linalg.eigvalsh(inekf.P)
        assert np.all(eigenvals > 0), "Covariance P must remain positive definite"
