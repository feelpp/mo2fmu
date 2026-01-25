"""Shared pytest fixtures for mo2fmu tests."""

from __future__ import annotations

from pathlib import Path

import pytest

# =============================================================================
# Model Directory Fixtures
# =============================================================================


@pytest.fixture
def modelsDir() -> Path:
    """Return the path to the shared test models directory."""
    return Path(__file__).parent / "fixtures" / "models"


# =============================================================================
# Model File Fixtures
# =============================================================================


@pytest.fixture
def simpleOdeModel(modelsDir: Path) -> Path:
    """Return path to simple_ode.mo - a basic exponential decay ODE."""
    return modelsDir / "simple_ode.mo"


@pytest.fixture
def odeWithInputModel(modelsDir: Path) -> Path:
    """Return path to ode_with_input.mo - an ODE with external input."""
    return modelsDir / "ode_with_input.mo"


@pytest.fixture
def odeSinusoidalModel(modelsDir: Path) -> Path:
    """Return path to ode_sinusoidal.mo - an ODE with sinusoidal forcing."""
    return modelsDir / "ode_sinusoidal.mo"


@pytest.fixture
def multiStateModel(modelsDir: Path) -> Path:
    """Return path to multi_state.mo - a model with multiple state variables."""
    return modelsDir / "multi_state.mo"


@pytest.fixture
def bouncingBallModel(modelsDir: Path) -> Path:
    """Return path to bouncing_ball.mo - a model with events for FMI 3.0 testing."""
    return modelsDir / "bouncing_ball.mo"


# =============================================================================
# Compiler Configuration Fixtures
# =============================================================================


@pytest.fixture
def dymolaConfig():
    """Return default Dymola configuration from environment."""
    from feelpp.mo2fmu.compilers.dymola import DymolaConfig

    return DymolaConfig.from_env()


@pytest.fixture
def openModelicaConfig():
    """Return default OpenModelica configuration from environment."""
    from feelpp.mo2fmu.compilers.openmodelica import OpenModelicaConfig

    return OpenModelicaConfig.from_env()
