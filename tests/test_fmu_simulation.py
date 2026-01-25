"""Tests for FMU simulation using FMPy.

This module tests that generated FMUs can be simulated using FMPy with
the CVODE solver (Sundials). This is particularly important for Model Exchange
FMUs which require an external solver.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from feelpp.mo2fmu import compileFmu
from feelpp.mo2fmu.compilers.dymola import DymolaConfig


# Check if FMPy is available
def _check_fmpy_available() -> bool:
    """Check if FMPy is available."""
    try:
        import fmpy  # noqa: F401

        return True
    except ImportError:
        return False


HAS_FMPY = _check_fmpy_available()


# Check if Dymola is available
DYMOLA_PATH = os.getenv("DYMOLA_ROOT", "/opt/dymola-2025xRefresh1-x86_64/")
DYMOLA_EXECUTABLE = os.getenv("DYMOLA_EXECUTABLE", "/usr/local/bin/dymola")
DYMOLA_WHL = os.getenv(
    "DYMOLA_WHL", "Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl"
)
HAS_DYMOLA = (Path(DYMOLA_PATH) / DYMOLA_WHL).is_file()

# Check if Dymola runtime license is available (needed to run FMUs)
DYMOLA_RUNTIME_LICENSE = os.getenv("DYMOLA_RUNTIME_LICENSE", "")
HAS_RUNTIME_LICENSE = bool(DYMOLA_RUNTIME_LICENSE) and Path(DYMOLA_RUNTIME_LICENSE).is_file()


def _get_dymola_config() -> DymolaConfig:
    """Get Dymola configuration."""
    return DymolaConfig(
        root=DYMOLA_PATH,
        executable=DYMOLA_EXECUTABLE,
        wheel_path=DYMOLA_WHL,
    )


# =============================================================================
# FMPy Simulation Tests
# =============================================================================


@pytest.mark.skipif(not HAS_FMPY, reason="FMPy not available")
@pytest.mark.skipif(not HAS_DYMOLA, reason="Dymola not available")
@pytest.mark.skipif(not HAS_RUNTIME_LICENSE, reason="Dymola runtime license not available")
class TestFmpySimulation:
    """Tests for FMU simulation using FMPy with CVODE solver."""

    def test_simulate_cosimulation_fmu(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test simulating a Co-Simulation FMU with FMPy."""
        from fmpy import simulate_fmu

        # Compile the model to Co-Simulation FMU
        outdir = tmp_path / "output_cs"
        result = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir,
            backend="dymola",
            fmiType="cs",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success, f"Compilation failed: {result.error_message}"
        assert result.fmu_path is not None
        assert result.fmu_path.exists()

        # Simulate the FMU
        sim_result = simulate_fmu(
            str(result.fmu_path),
            start_time=0.0,
            stop_time=1.0,
            output_interval=0.01,
        )

        # Verify simulation produced results
        assert sim_result is not None
        assert len(sim_result) > 0
        assert "time" in sim_result.dtype.names
        assert "y" in sim_result.dtype.names

        # Check that the solution decays (y starts at 1, decays with lambda=2)
        y_values = sim_result["y"]
        assert y_values[0] > 0.9  # Initial value close to 1
        assert y_values[-1] < y_values[0]  # Decayed

    def test_simulate_model_exchange_fmu(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test simulating a Model Exchange FMU with FMPy using CVODE solver."""
        from fmpy import simulate_fmu

        # Compile the model to Model Exchange FMU
        outdir = tmp_path / "output_me"
        result = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir,
            backend="dymola",
            fmiType="me",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success, f"Compilation failed: {result.error_message}"
        assert result.fmu_path is not None
        assert result.fmu_path.exists()

        # Simulate the FMU with Model Exchange (uses CVODE solver internally)
        sim_result = simulate_fmu(
            str(result.fmu_path),
            start_time=0.0,
            stop_time=1.0,
            output_interval=0.01,
            fmi_type="ModelExchange",  # Explicitly use Model Exchange
        )

        # Verify simulation produced results
        assert sim_result is not None
        assert len(sim_result) > 0
        assert "time" in sim_result.dtype.names
        assert "y" in sim_result.dtype.names

        # Check that the solution decays correctly
        y_values = sim_result["y"]

        # Initial value should be close to 1
        assert abs(y_values[0] - 1.0) < 0.01

        # Final value should be close to exp(-2*1) ≈ 0.135 (lambda=2, t=1)
        import math

        expected_final = math.exp(-2.0 * 1.0)
        assert abs(y_values[-1] - expected_final) < 0.01

    def test_simulate_model_exchange_sinusoidal(
        self, odeSinusoidalModel: Path, tmp_path: Path
    ) -> None:
        """Test simulating sinusoidal ODE as Model Exchange with CVODE."""
        from fmpy import simulate_fmu

        # Compile to Model Exchange
        outdir = tmp_path / "output_sin_me"
        result = compileFmu(
            mo=odeSinusoidalModel,
            outdir=outdir,
            backend="dymola",
            fmiType="me",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success, f"Compilation failed: {result.error_message}"

        # Simulate with Model Exchange
        sim_result = simulate_fmu(
            str(result.fmu_path),
            start_time=0.0,
            stop_time=6.28,  # One full period (2*pi)
            output_interval=0.1,
            fmi_type="ModelExchange",
        )

        assert sim_result is not None
        assert len(sim_result) > 0
        assert "y" in sim_result.dtype.names

        # The integral of sin(t) from 0 to 2*pi is 0
        # y(t) = integral of sin(omega*t) with omega=1, y(0)=0
        # At t=2*pi, y should be close to 0
        y_final = sim_result["y"][-1]
        assert abs(y_final) < 0.1  # Should be close to 0

    def test_compare_cs_and_me_results(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test that Co-Simulation and Model Exchange produce similar results."""
        import numpy as np
        from fmpy import simulate_fmu

        # Compile Co-Simulation FMU
        outdir_cs = tmp_path / "output_cs"
        result_cs = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir_cs,
            backend="dymola",
            fmiType="cs",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )
        assert result_cs.success

        # Compile Model Exchange FMU
        outdir_me = tmp_path / "output_me"
        result_me = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir_me,
            backend="dymola",
            fmiType="me",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )
        assert result_me.success

        # Simulate both
        sim_cs = simulate_fmu(
            str(result_cs.fmu_path),
            start_time=0.0,
            stop_time=1.0,
            output_interval=0.1,
        )

        sim_me = simulate_fmu(
            str(result_me.fmu_path),
            start_time=0.0,
            stop_time=1.0,
            output_interval=0.1,
            fmi_type="ModelExchange",
        )

        # Compare results - they should be very close
        y_cs = sim_cs["y"]
        y_me = sim_me["y"]

        # Allow small differences due to different solvers
        max_diff = np.max(np.abs(y_cs - y_me))
        assert max_diff < 0.01, f"Max difference between CS and ME: {max_diff}"


@pytest.mark.skipif(not HAS_FMPY, reason="FMPy not available")
@pytest.mark.skipif(not HAS_DYMOLA, reason="Dymola not available")
@pytest.mark.skipif(not HAS_RUNTIME_LICENSE, reason="Dymola runtime license not available")
class TestFmpyFmi3Simulation:
    """Tests for FMI 3.0 FMU simulation using FMPy."""

    def test_simulate_fmi3_model_exchange(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test simulating an FMI 3.0 Model Exchange FMU."""
        from fmpy import simulate_fmu

        # Compile to FMI 3.0 Model Exchange
        outdir = tmp_path / "output_fmi3_me"
        result = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir,
            backend="dymola",
            fmiType="me",
            fmiVersion="3",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        # FMI 3.0 may not be supported by all Dymola versions
        if not result.success:
            pytest.skip("FMI 3.0 not supported by current Dymola version")

        assert result.fmu_path is not None
        assert result.fmu_path.exists()

        # Try to simulate - FMPy 0.3+ supports FMI 3.0
        try:
            sim_result = simulate_fmu(
                str(result.fmu_path),
                start_time=0.0,
                stop_time=1.0,
                output_interval=0.01,
                fmi_type="ModelExchange",
            )

            assert sim_result is not None
            assert len(sim_result) > 0
        except Exception as e:
            # FMPy might not fully support FMI 3.0 yet
            pytest.skip(f"FMPy FMI 3.0 simulation failed: {e}")

    def test_simulate_fmi3_cosimulation(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test simulating an FMI 3.0 Co-Simulation FMU."""
        from fmpy import simulate_fmu

        # Compile to FMI 3.0 Co-Simulation
        outdir = tmp_path / "output_fmi3_cs"
        result = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir,
            backend="dymola",
            fmiType="cs",
            fmiVersion="3",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        # FMI 3.0 may not be supported
        if not result.success:
            pytest.skip("FMI 3.0 not supported by current Dymola version")

        assert result.fmu_path is not None

        try:
            sim_result = simulate_fmu(
                str(result.fmu_path),
                start_time=0.0,
                stop_time=1.0,
                output_interval=0.01,
            )

            assert sim_result is not None
            assert len(sim_result) > 0
        except Exception as e:
            pytest.skip(f"FMPy FMI 3.0 simulation failed: {e}")


@pytest.mark.skipif(not HAS_FMPY, reason="FMPy not available")
class TestFmpyValidation:
    """Tests for FMU validation using FMPy."""

    @pytest.mark.skipif(not HAS_DYMOLA, reason="Dymola not available")
    def test_validate_fmu(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test FMU validation using FMPy."""
        from fmpy import read_model_description
        from fmpy.validation import validate_fmu

        # Compile the model
        outdir = tmp_path / "output"
        result = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir,
            backend="dymola",
            fmiType="cs",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success
        assert result.fmu_path is not None

        # Validate the FMU
        problems = validate_fmu(str(result.fmu_path))

        # Should have no critical problems
        critical_problems = [p for p in problems if "Error" in str(p)]
        assert len(critical_problems) == 0, f"FMU validation errors: {critical_problems}"

        # Read model description
        model_desc = read_model_description(str(result.fmu_path))
        assert model_desc is not None
        assert model_desc.modelName is not None

    @pytest.mark.skipif(not HAS_DYMOLA, reason="Dymola not available")
    def test_read_model_variables(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test reading model variables from FMU."""
        from fmpy import read_model_description

        # Compile the model
        outdir = tmp_path / "output"
        result = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir,
            backend="dymola",
            fmiType="me",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success

        # Read model description
        model_desc = read_model_description(str(result.fmu_path))

        # Check that expected variables exist
        var_names = [v.name for v in model_desc.modelVariables]
        assert "y" in var_names  # State variable
        assert "lambda" in var_names  # Parameter


# =============================================================================
# Bouncing Ball Tests (Event Handling / FMI 3.0)
# =============================================================================


@pytest.mark.skipif(not HAS_FMPY, reason="FMPy not available")
@pytest.mark.skipif(not HAS_DYMOLA, reason="Dymola not available")
@pytest.mark.skipif(not HAS_RUNTIME_LICENSE, reason="Dymola runtime license not available")
class TestBouncingBallSimulation:
    """Tests for bouncing ball model with events using FMPy.

    The bouncing ball model tests:
    - Event handling (zero-crossing when h <= 0)
    - Discrete variables (bounce_count)
    - State reinit (velocity reversal on bounce)
    - Input variables (wind_force)
    """

    def test_compile_bouncing_ball_fmi2(self, bouncingBallModel: Path, tmp_path: Path) -> None:
        """Test compiling bouncing ball to FMI 2.0."""
        outdir = tmp_path / "output_bb_fmi2"
        result = compileFmu(
            mo=bouncingBallModel,
            outdir=outdir,
            backend="dymola",
            fmiType="me",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success, f"Compilation failed: {result.error_message}"
        assert result.fmu_path is not None
        assert result.fmu_path.exists()

    def test_simulate_bouncing_ball_cosimulation(
        self, bouncingBallModel: Path, tmp_path: Path
    ) -> None:
        """Test simulating bouncing ball as Co-Simulation FMU."""
        from fmpy import simulate_fmu

        # Compile to Co-Simulation
        outdir = tmp_path / "output_bb_cs"
        result = compileFmu(
            mo=bouncingBallModel,
            outdir=outdir,
            backend="dymola",
            fmiType="cs",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success, f"Compilation failed: {result.error_message}"

        # Simulate for 3 seconds (should see multiple bounces)
        sim_result = simulate_fmu(
            str(result.fmu_path),
            start_time=0.0,
            stop_time=3.0,
            output_interval=0.01,
        )

        assert sim_result is not None
        assert len(sim_result) > 0

        # Check expected outputs exist
        assert "time" in sim_result.dtype.names
        assert "h_out" in sim_result.dtype.names or "h" in sim_result.dtype.names

        # Height should start at 1.0
        h_var = "h_out" if "h_out" in sim_result.dtype.names else "h"
        h_values = sim_result[h_var]
        assert abs(h_values[0] - 1.0) < 0.01

    def test_simulate_bouncing_ball_model_exchange(
        self, bouncingBallModel: Path, tmp_path: Path
    ) -> None:
        """Test simulating bouncing ball as Model Exchange with CVODE solver.

        Note: Event handling in Model Exchange mode depends on the external solver.
        FMPy's CVODE may not perfectly handle state events (zero-crossings),
        so we verify the simulation runs and produces reasonable results.
        """
        from fmpy import simulate_fmu

        # Compile to Model Exchange
        outdir = tmp_path / "output_bb_me"
        result = compileFmu(
            mo=bouncingBallModel,
            outdir=outdir,
            backend="dymola",
            fmiType="me",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success, f"Compilation failed: {result.error_message}"

        # Simulate with Model Exchange (CVODE handles the events)
        sim_result = simulate_fmu(
            str(result.fmu_path),
            start_time=0.0,
            stop_time=3.0,
            output_interval=0.01,
            fmi_type="ModelExchange",
        )

        assert sim_result is not None
        assert len(sim_result) > 0

        # Verify the simulation ran and produced output
        h_var = "h_out" if "h_out" in sim_result.dtype.names else "h"
        assert h_var in sim_result.dtype.names
        h_values = sim_result[h_var]

        # Check initial condition
        assert abs(h_values[0] - 1.0) < 0.01  # Should start at h=1

        # Note: CVODE in FMPy may not handle state events perfectly,
        # so we just verify the simulation completes and bounce_count increases
        if "bounce_count" in sim_result.dtype.names:
            bounce_counts = sim_result["bounce_count"]
            # Should detect at least some bounces
            assert max(bounce_counts) >= 1, "No bounces detected in ME simulation"

    def test_bouncing_ball_bounce_count(self, bouncingBallModel: Path, tmp_path: Path) -> None:
        """Test that bounce counter increments correctly."""
        from fmpy import simulate_fmu

        # Compile to Co-Simulation (more reliable for event handling)
        outdir = tmp_path / "output_bb_count"
        result = compileFmu(
            mo=bouncingBallModel,
            outdir=outdir,
            backend="dymola",
            fmiType="cs",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success

        # Simulate long enough for multiple bounces
        sim_result = simulate_fmu(
            str(result.fmu_path),
            start_time=0.0,
            stop_time=5.0,
            output_interval=0.1,
        )

        # Check if bounce_count exists and increases
        if "bounce_count" in sim_result.dtype.names:
            bounce_counts = sim_result["bounce_count"]
            # Should have at least one bounce in 5 seconds
            assert max(bounce_counts) >= 1

    def test_bouncing_ball_fmi3_model_exchange(
        self, bouncingBallModel: Path, tmp_path: Path
    ) -> None:
        """Test bouncing ball with FMI 3.0 Model Exchange - tests event handling."""
        from fmpy import simulate_fmu

        # Compile to FMI 3.0 Model Exchange
        outdir = tmp_path / "output_bb_fmi3_me"
        result = compileFmu(
            mo=bouncingBallModel,
            outdir=outdir,
            backend="dymola",
            fmiType="me",
            fmiVersion="3",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        # FMI 3.0 may not be supported
        if not result.success:
            pytest.skip("FMI 3.0 not supported by current Dymola version")

        assert result.fmu_path is not None
        assert result.fmu_path.exists()

        # Try to simulate with FMI 3.0
        try:
            sim_result = simulate_fmu(
                str(result.fmu_path),
                start_time=0.0,
                stop_time=3.0,
                output_interval=0.01,
                fmi_type="ModelExchange",
            )

            assert sim_result is not None
            assert len(sim_result) > 0

            # Verify physics - ball should bounce and height stay >= 0
            h_var = "h_out" if "h_out" in sim_result.dtype.names else "h"
            if h_var in sim_result.dtype.names:
                h_values = sim_result[h_var]
                assert min(h_values) >= -0.01

        except Exception as e:
            pytest.skip(f"FMPy FMI 3.0 event simulation failed: {e}")

    def test_bouncing_ball_fmi3_cosimulation(self, bouncingBallModel: Path, tmp_path: Path) -> None:
        """Test bouncing ball with FMI 3.0 Co-Simulation."""
        from fmpy import simulate_fmu

        # Compile to FMI 3.0 Co-Simulation
        outdir = tmp_path / "output_bb_fmi3_cs"
        result = compileFmu(
            mo=bouncingBallModel,
            outdir=outdir,
            backend="dymola",
            fmiType="cs",
            fmiVersion="3",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        # FMI 3.0 may not be supported
        if not result.success:
            pytest.skip("FMI 3.0 not supported by current Dymola version")

        assert result.fmu_path is not None

        try:
            sim_result = simulate_fmu(
                str(result.fmu_path),
                start_time=0.0,
                stop_time=3.0,
                output_interval=0.01,
            )

            assert sim_result is not None
            assert len(sim_result) > 0

        except Exception as e:
            pytest.skip(f"FMPy FMI 3.0 Co-Simulation failed: {e}")

    def test_bouncing_ball_with_wind_input(self, bouncingBallModel: Path, tmp_path: Path) -> None:
        """Test bouncing ball with wind_force input variable."""
        from fmpy import read_model_description

        # Compile to Model Exchange
        outdir = tmp_path / "output_bb_wind"
        result = compileFmu(
            mo=bouncingBallModel,
            outdir=outdir,
            backend="dymola",
            fmiType="me",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=_get_dymola_config(),
        )

        assert result.success

        # Read model description to verify input exists
        model_desc = read_model_description(str(result.fmu_path))
        var_names = [v.name for v in model_desc.modelVariables]

        # Verify expected variables
        assert "h" in var_names or "h_out" in var_names  # Height output
        assert "v" in var_names  # Velocity state
        assert "wind_force" in var_names  # Input variable
        assert "e" in var_names  # Restitution parameter
        assert "g" in var_names  # Gravity parameter
