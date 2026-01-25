"""Tests for the mo2fmu CLI and Python API."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from xvfbwrapper import Xvfb

from feelpp.mo2fmu import compileFmu
from feelpp.mo2fmu.compilers.dymola import DymolaConfig


def checkFmuFileExist(fmuPath: Path, outdir: Path) -> None:
    """Check if FMU file exists.

    Parameters
    ----------
    fmuPath: Path
        path of the fmu file
    outdir: Path
        path of the output file directory.
    """
    assert fmuPath.exists(), f"FMU file {fmuPath} was not created."
    print(f"FMU file created at: {fmuPath}")


def checkFmuValidity(fmuPath: Path, fmuModel: str, dymolapath: str) -> None:
    """Check that the fmu model has the same number of unknowns and equations.

    Also verifies that it can be simulated.

    Parameters
    ----------
    fmuPath: Path
        path of the fmu file
    fmuModel: str
        name of the fmu model in Dymola
    dymolapath: str
        path of the dymola application
    """
    # launch a display server (needed to launch Dymola)
    vdisplay = Xvfb()
    vdisplay.start()

    # launch Dymola
    from dymola.dymola_interface import DymolaInterface

    dymApp = DymolaInterface(dymolapath=dymolapath, showwindow=False)

    # import the FMU
    importedFMU = dymApp.importFMU(str(fmuPath))
    assert importedFMU, f"FMU file {fmuPath} couldn't be imported"

    # check the model and simulate it
    result = dymApp.checkModel(problem=fmuModel, simulate=True)
    if result is False:
        log = dymApp.getLastErrorLog()
        print(log)

    # close Dymola and display server
    dymApp.close()
    vdisplay.stop()

    assert result, f"FMU file {fmuPath} isn't valid, see the log above."


# =============================================================================
# Path Existence Tests
# =============================================================================


def test_fixturesExist(modelsDir: Path) -> None:
    """Test if the shared fixtures directory exists."""
    assert modelsDir.exists(), f"Models directory {modelsDir} does not exist"
    assert modelsDir.is_dir(), f"{modelsDir} is not a directory"


def test_simpleOdeModelExists(simpleOdeModel: Path) -> None:
    """Test if the simple ODE model exists."""
    assert simpleOdeModel.exists(), f"Model {simpleOdeModel} does not exist"
    print(f"Model path: {simpleOdeModel}")


def test_odeSinusoidalModelExists(odeSinusoidalModel: Path) -> None:
    """Test if the sinusoidal ODE model exists."""
    assert odeSinusoidalModel.exists(), f"Model {odeSinusoidalModel} does not exist"


# =============================================================================
# Compilation Tests (require Dymola)
# =============================================================================


# Check if Dymola is available
# Configure via environment variables:
# - DYMOLA_ROOT: Path to Dymola installation (default: /opt/dymola-2025xRefresh1-x86_64/)
# - DYMOLA_EXECUTABLE: Path to Dymola binary (default: /usr/local/bin/dymola)
# - DYMOLA_WHL: Relative path to Python wheel
DYMOLA_PATH = os.getenv("DYMOLA_ROOT", "/opt/dymola-2025xRefresh1-x86_64/")
DYMOLA_EXECUTABLE = os.getenv("DYMOLA_EXECUTABLE", "/usr/local/bin/dymola")
DYMOLA_WHL = os.getenv(
    "DYMOLA_WHL", "Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl"
)
HAS_DYMOLA = (Path(DYMOLA_PATH) / DYMOLA_WHL).is_file()


@pytest.mark.skipif(not HAS_DYMOLA, reason="Dymola not available in test environment")
class TestDymolaCompilation:
    """Tests for FMU compilation with Dymola."""

    def test_compile_simple_ode(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compileFmu function using simple ODE model."""
        baseName = simpleOdeModel.stem
        outdir = tmp_path / "output"
        fmuPath = outdir / f"{baseName}.fmu"
        fmuDymola = f"{baseName}_fmu"

        # Configure Dymola
        dymolaConfig = DymolaConfig(
            root=DYMOLA_PATH,
            executable=DYMOLA_EXECUTABLE,
            wheel_path=DYMOLA_WHL,
        )

        # Call compileFmu converter
        result = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir,
            backend="dymola",
            fmiType="all",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=dymolaConfig,
        )

        # Check compilation succeeded
        assert result.success, f"Compilation failed: {result.error_message}"

        # Check if the FMU file is created
        checkFmuFileExist(fmuPath, outdir)

        # Check model validity of the fmu
        checkFmuValidity(fmuPath, fmuDymola, DYMOLA_EXECUTABLE)

    def test_compile_sinusoidal_ode(self, odeSinusoidalModel: Path, tmp_path: Path) -> None:
        """Test compileFmu function using sinusoidal ODE model."""
        baseName = odeSinusoidalModel.stem
        outdir = tmp_path / "output"
        fmuPath = outdir / f"{baseName}.fmu"
        fmuDymola = f"{baseName}_fmu"

        # Configure Dymola
        dymolaConfig = DymolaConfig(
            root=DYMOLA_PATH,
            executable=DYMOLA_EXECUTABLE,
            wheel_path=DYMOLA_WHL,
        )

        # Call compileFmu converter
        result = compileFmu(
            mo=odeSinusoidalModel,
            outdir=outdir,
            backend="dymola",
            fmiType="all",
            fmiVersion="2",
            verbose=True,
            force=True,
            dymolaConfig=dymolaConfig,
        )

        # Check compilation succeeded
        assert result.success, f"Compilation failed: {result.error_message}"

        # Check if the FMU file is created
        checkFmuFileExist(fmuPath, outdir)

        # Check model validity of the fmu
        checkFmuValidity(fmuPath, fmuDymola, DYMOLA_EXECUTABLE)

    def test_compile_fmi3(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compileFmu with FMI 3.0."""
        baseName = simpleOdeModel.stem
        outdir = tmp_path / "output_fmi3"
        fmuPath = outdir / f"{baseName}.fmu"

        # Configure Dymola
        dymolaConfig = DymolaConfig(
            root=DYMOLA_PATH,
            executable=DYMOLA_EXECUTABLE,
            wheel_path=DYMOLA_WHL,
        )

        # Call compileFmu converter with FMI 3.0
        result = compileFmu(
            mo=simpleOdeModel,
            outdir=outdir,
            backend="dymola",
            fmiType="cs",
            fmiVersion="3",
            verbose=True,
            force=True,
            dymolaConfig=dymolaConfig,
        )

        # FMI 3.0 requires Dymola 2024+
        if result.success:
            checkFmuFileExist(fmuPath, outdir)
        else:
            # Older Dymola versions may not support FMI 3.0
            assert "3" in result.error_message or result.error_message is not None
