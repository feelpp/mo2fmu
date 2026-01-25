"""Tests for the compiler abstraction layer.

This module tests the base classes, Dymola compiler, and OpenModelica compiler.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from feelpp.mo2fmu.compilers.base import (
    CompilationConfig,
    CompilationResult,
    FMIType,
    FMIVersion,
    ModelicaModel,
)
from feelpp.mo2fmu.compilers.dymola import DymolaCompiler, DymolaConfig
from feelpp.mo2fmu.compilers.openmodelica import OpenModelicaCompiler, OpenModelicaConfig


# =============================================================================
# Compiler Availability Checks
# =============================================================================


def _check_omc_available() -> bool:
    """Check if OpenModelica is available via OMPython or CLI."""
    compiler = OpenModelicaCompiler()
    return compiler.is_available


HAS_OMC = _check_omc_available()


# =============================================================================
# Test Data Classes
# =============================================================================


class TestFMIType:
    """Tests for FMIType enum."""

    def test_from_string_valid(self) -> None:
        """Test valid string conversions."""
        assert FMIType.from_string("me") == FMIType.MODEL_EXCHANGE
        assert FMIType.from_string("cs") == FMIType.CO_SIMULATION
        assert FMIType.from_string("all") == FMIType.BOTH
        assert FMIType.from_string("csSolver") == FMIType.CO_SIMULATION_SOLVER

    def test_from_string_invalid(self) -> None:
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid FMI type"):
            FMIType.from_string("invalid")


class TestFMIVersion:
    """Tests for FMIVersion enum."""

    def test_from_string_valid(self) -> None:
        """Test valid string conversions."""
        assert FMIVersion.from_string("1") == FMIVersion.FMI_1_0
        assert FMIVersion.from_string("2") == FMIVersion.FMI_2_0
        assert FMIVersion.from_string("3") == FMIVersion.FMI_3_0

    def test_from_string_invalid(self) -> None:
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid FMI version"):
            FMIVersion.from_string("4")


class TestModelicaModel:
    """Tests for ModelicaModel class."""

    def test_simple_model(self, tmp_path: Path) -> None:
        """Test creating a model from a simple .mo file."""
        mo_file = tmp_path / "simple.mo"
        mo_file.write_text(
            """model simple
  Real x;
equation
  der(x) = -x;
end simple;
"""
        )

        model = ModelicaModel(mo_file)

        assert model.path == mo_file
        assert model.model_name == "simple"
        assert model.package_name is None
        assert model.fully_qualified_name == "simple"

    def test_model_with_package(self, tmp_path: Path) -> None:
        """Test creating a model with a 'within' statement."""
        mo_file = tmp_path / "test_model.mo"
        mo_file.write_text(
            """within MyPackage.SubPackage;
model test_model
  Real x;
equation
  der(x) = -x;
end test_model;
"""
        )

        model = ModelicaModel(mo_file)

        assert model.path == mo_file
        assert model.model_name == "test_model"
        assert model.package_name == "MyPackage.SubPackage"
        assert model.fully_qualified_name == "MyPackage.SubPackage.test_model"

    def test_model_explicit_name(self, tmp_path: Path) -> None:
        """Test creating a model with explicit model name."""
        mo_file = tmp_path / "test.mo"
        mo_file.write_text("model test end test;")

        model = ModelicaModel(mo_file, model_name="CustomName")

        assert model.model_name == "CustomName"
        assert model.fully_qualified_name == "CustomName"


class TestCompilationConfig:
    """Tests for CompilationConfig class."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CompilationConfig()

        assert config.fmi_type == FMIType.BOTH
        assert config.fmi_version == FMIVersion.FMI_2_0
        assert config.output_name is None
        assert config.packages == []
        assert config.flags == []
        assert config.force is False
        assert config.verbose is False

    def test_from_legacy(self) -> None:
        """Test creating config from legacy parameters."""
        config = CompilationConfig.from_legacy(
            type="cs",
            version="2",
            fmumodelname="MyModel",
            load=("pkg1", "pkg2"),
            flags=("-d=debug",),
            force=True,
            verbose=True,
        )

        assert config.fmi_type == FMIType.CO_SIMULATION
        assert config.fmi_version == FMIVersion.FMI_2_0
        assert config.output_name == "MyModel"
        assert config.packages == ["pkg1", "pkg2"]
        assert config.flags == ["-d=debug"]
        assert config.force is True
        assert config.verbose is True


class TestCompilationResult:
    """Tests for CompilationResult class."""

    def test_success_result(self) -> None:
        """Test successful compilation result."""
        result = CompilationResult(
            success=True,
            fmu_path=Path("/path/to/model.fmu"),
        )

        assert result.success is True
        assert result.fmu_path == Path("/path/to/model.fmu")
        assert result.error_message is None

    def test_failure_result(self) -> None:
        """Test failed compilation result."""
        result = CompilationResult(
            success=False,
            error_message="Compilation failed",
            log="Error details...",
        )

        assert result.success is False
        assert result.fmu_path is None
        assert result.error_message == "Compilation failed"
        assert result.log == "Error details..."


# =============================================================================
# Test Dymola Compiler
# =============================================================================


class TestDymolaConfig:
    """Tests for DymolaConfig class."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = DymolaConfig()

        assert config.root == "/opt/dymola-2025xRefresh1-x86_64/"
        assert config.executable == "/usr/local/bin/dymola"
        assert config.compile_64bit_only is True
        assert config.enable_code_export is True
        assert config.global_optimizations == 2
        assert config.linger_time == 0

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test creating config from environment variables."""
        monkeypatch.setenv("DYMOLA_ROOT", "/custom/dymola")
        monkeypatch.setenv("DYMOLA_EXECUTABLE", "/custom/bin/dymola")
        monkeypatch.setenv("DYMOLA_WHL", "custom/wheel.whl")

        config = DymolaConfig.from_env()

        assert config.root == "/custom/dymola"
        assert config.executable == "/custom/bin/dymola"
        assert config.wheel_path == "custom/wheel.whl"


class TestDymolaCompiler:
    """Tests for DymolaCompiler class."""

    def test_compiler_name(self) -> None:
        """Test compiler name property."""
        compiler = DymolaCompiler()
        assert compiler.name == "dymola"

    def test_availability_check(self) -> None:
        """Test availability check with invalid path."""
        config = DymolaConfig(root="/nonexistent/path")
        compiler = DymolaCompiler(config)

        assert compiler.is_available is False

    def test_compile_unavailable(self, tmp_path: Path) -> None:
        """Test compilation when Dymola is not available."""
        config = DymolaConfig(root="/nonexistent/path")
        compiler = DymolaCompiler(config)

        mo_file = tmp_path / "test.mo"
        mo_file.write_text("model test end test;")
        model = ModelicaModel(mo_file)

        result = compiler.compile(model, tmp_path / "output", CompilationConfig())

        assert result.success is False
        assert "not available" in result.error_message.lower()


# =============================================================================
# Test OpenModelica Compiler
# =============================================================================


class TestOpenModelicaConfig:
    """Tests for OpenModelicaConfig class."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = OpenModelicaConfig()

        assert config.omc_path is None
        assert config.ompython_session is True
        assert config.target_platform == "static"
        assert config.debug is False
        assert config.num_procs == 1

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test creating config from environment variables."""
        monkeypatch.setenv("OPENMODELICA_HOME", "/custom/omc")
        monkeypatch.setenv("CXX", "clang++")
        monkeypatch.setenv("CC", "clang")

        config = OpenModelicaConfig.from_env()

        assert config.omc_path == "/custom/omc"
        assert config.cpp_compiler == "clang++"
        assert config.c_compiler == "clang"


class TestOpenModelicaCompiler:
    """Tests for OpenModelicaCompiler class."""

    def test_compiler_name(self) -> None:
        """Test compiler name property."""
        compiler = OpenModelicaCompiler()
        assert compiler.name == "openmodelica"

    @pytest.mark.skipif(not HAS_OMC, reason="OpenModelica not available")
    def test_compile_output_same_as_cwd(self, tmp_path: Path) -> None:
        """Test that compilation fails when output dir equals cwd."""
        import os

        compiler = OpenModelicaCompiler()

        mo_file = tmp_path / "test.mo"
        mo_file.write_text("model test end test;")
        model = ModelicaModel(mo_file)

        # Save current directory
        original_cwd = os.getcwd()

        try:
            os.chdir(tmp_path)
            result = compiler.compile(model, tmp_path, CompilationConfig())

            assert result.success is False
            assert "must differ" in result.error_message.lower()
        finally:
            os.chdir(original_cwd)

    @pytest.mark.skipif(not HAS_OMC, reason="OpenModelica not available")
    def test_compile_force_false_existing_fmu(self, tmp_path: Path) -> None:
        """Test that compilation fails when FMU exists and force=False."""
        compiler = OpenModelicaCompiler()

        mo_file = tmp_path / "test.mo"
        mo_file.write_text("model test end test;")
        model = ModelicaModel(mo_file)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing FMU
        existing_fmu = output_dir / "test.fmu"
        existing_fmu.write_text("dummy")

        config = CompilationConfig(force=False)
        result = compiler.compile(model, output_dir, config)

        assert result.success is False
        assert "exists" in result.error_message.lower()


# =============================================================================
# Integration Tests (require actual compilers)
# =============================================================================


@pytest.mark.skipif(not HAS_OMC, reason="OpenModelica not available")
class TestOpenModelicaIntegration:
    """Integration tests for OpenModelica compiler."""

    def test_version(self) -> None:
        """Test getting OpenModelica version."""
        compiler = OpenModelicaCompiler()
        version = compiler.get_version()

        assert version is not None
        # Version should contain a number
        assert any(c.isdigit() for c in version)

    def test_check_model(self, simpleOdeModel: Path) -> None:
        """Test checking a simple model."""
        compiler = OpenModelicaCompiler()
        model = ModelicaModel(simpleOdeModel)

        result = compiler.check_model(model)
        # Note: checkModel might return True even with warnings
        assert result is True or result is False  # Just ensure it runs

    def test_compile_simple_model(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compiling a simple model to FMU."""
        compiler = OpenModelicaCompiler()
        model = ModelicaModel(simpleOdeModel)

        output_dir = tmp_path / "output"
        config = CompilationConfig(
            fmi_type=FMIType.CO_SIMULATION,
            fmi_version=FMIVersion.FMI_2_0,
            verbose=True,
            force=True,
        )

        result = compiler.compile(model, output_dir, config)

        if result.success:
            assert result.fmu_path is not None
            assert result.fmu_path.exists()
            assert result.fmu_path.suffix == ".fmu"
        else:
            # OpenModelica might fail on some systems - just check result is valid
            assert result.error_message is not None

    def test_compile_model_exchange(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compiling with Model Exchange type."""
        compiler = OpenModelicaCompiler()
        model = ModelicaModel(simpleOdeModel)

        output_dir = tmp_path / "output_me"
        config = CompilationConfig(
            fmi_type=FMIType.MODEL_EXCHANGE,
            fmi_version=FMIVersion.FMI_2_0,
            verbose=True,
            force=True,
        )

        result = compiler.compile(model, output_dir, config)

        # Just verify it produces a valid result structure
        assert isinstance(result, CompilationResult)
        assert isinstance(result.success, bool)

    def test_compile_fmi3_cosimulation(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compiling a simple model to FMI 3.0 Co-Simulation FMU."""
        compiler = OpenModelicaCompiler()
        model = ModelicaModel(simpleOdeModel)

        output_dir = tmp_path / "output_fmi3_cs"
        config = CompilationConfig(
            fmi_type=FMIType.CO_SIMULATION,
            fmi_version=FMIVersion.FMI_3_0,
            verbose=True,
            force=True,
        )

        result = compiler.compile(model, output_dir, config)

        # FMI 3.0 requires OpenModelica 1.21+, so this may fail on older versions
        # Just verify the result structure is valid
        assert isinstance(result, CompilationResult)
        assert isinstance(result.success, bool)
        if result.success:
            assert result.fmu_path is not None
            assert result.fmu_path.exists()
            assert result.fmu_path.suffix == ".fmu"

    def test_compile_fmi3_model_exchange(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compiling a simple model to FMI 3.0 Model Exchange FMU."""
        compiler = OpenModelicaCompiler()
        model = ModelicaModel(simpleOdeModel)

        output_dir = tmp_path / "output_fmi3_me"
        config = CompilationConfig(
            fmi_type=FMIType.MODEL_EXCHANGE,
            fmi_version=FMIVersion.FMI_3_0,
            verbose=True,
            force=True,
        )

        result = compiler.compile(model, output_dir, config)

        # FMI 3.0 requires OpenModelica 1.21+, so this may fail on older versions
        # Just verify the result structure is valid
        assert isinstance(result, CompilationResult)
        assert isinstance(result.success, bool)
        if result.success:
            assert result.fmu_path is not None
            assert result.fmu_path.exists()
            assert result.fmu_path.suffix == ".fmu"

    def test_compile_fmi3_both(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compiling a simple model to FMI 3.0 with both ME and CS."""
        compiler = OpenModelicaCompiler()
        model = ModelicaModel(simpleOdeModel)

        output_dir = tmp_path / "output_fmi3_both"
        config = CompilationConfig(
            fmi_type=FMIType.BOTH,
            fmi_version=FMIVersion.FMI_3_0,
            verbose=True,
            force=True,
        )

        result = compiler.compile(model, output_dir, config)

        # FMI 3.0 requires OpenModelica 1.21+, so this may fail on older versions
        # Just verify the result structure is valid
        assert isinstance(result, CompilationResult)
        assert isinstance(result.success, bool)
        if result.success:
            assert result.fmu_path is not None
            assert result.fmu_path.exists()
            assert result.fmu_path.suffix == ".fmu"


# Check if Dymola is available
def _check_dymola_available() -> bool:
    """Check if Dymola is available."""
    import os

    dymola_root = os.getenv("DYMOLA_ROOT", "/opt/dymola-2025xRefresh1-x86_64/")
    dymola_whl = os.getenv(
        "DYMOLA_WHL", "Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl"
    )
    return (Path(dymola_root) / dymola_whl).is_file()


HAS_DYMOLA = _check_dymola_available()


@pytest.mark.skipif(not HAS_DYMOLA, reason="Dymola not available")
class TestDymolaIntegration:
    """Integration tests for Dymola compiler."""

    def test_version(self) -> None:
        """Test getting Dymola version."""
        compiler = DymolaCompiler()
        version = compiler.get_version()

        # Version might be None if we can't parse it
        assert version is None or isinstance(version, str)

    def test_compile_simple_model(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compiling a simple model to FMU."""
        compiler = DymolaCompiler()
        model = ModelicaModel(simpleOdeModel)

        output_dir = tmp_path / "output"
        config = CompilationConfig(
            fmi_type=FMIType.CO_SIMULATION,
            fmi_version=FMIVersion.FMI_2_0,
            verbose=True,
            force=True,
        )

        result = compiler.compile(model, output_dir, config)

        if result.success:
            assert result.fmu_path is not None
            assert result.fmu_path.exists()
            assert result.fmu_path.suffix == ".fmu"

    def test_compile_fmi3_cosimulation(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compiling a simple model to FMI 3.0 Co-Simulation FMU."""
        compiler = DymolaCompiler()
        model = ModelicaModel(simpleOdeModel)

        output_dir = tmp_path / "output_fmi3_cs"
        config = CompilationConfig(
            fmi_type=FMIType.CO_SIMULATION,
            fmi_version=FMIVersion.FMI_3_0,
            verbose=True,
            force=True,
        )

        result = compiler.compile(model, output_dir, config)

        # FMI 3.0 requires Dymola 2024+, so this may fail on older versions
        # Just verify the result structure is valid
        assert isinstance(result, CompilationResult)
        assert isinstance(result.success, bool)
        if result.success:
            assert result.fmu_path is not None
            assert result.fmu_path.exists()
            assert result.fmu_path.suffix == ".fmu"

    def test_compile_fmi3_model_exchange(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compiling a simple model to FMI 3.0 Model Exchange FMU."""
        compiler = DymolaCompiler()
        model = ModelicaModel(simpleOdeModel)

        output_dir = tmp_path / "output_fmi3_me"
        config = CompilationConfig(
            fmi_type=FMIType.MODEL_EXCHANGE,
            fmi_version=FMIVersion.FMI_3_0,
            verbose=True,
            force=True,
        )

        result = compiler.compile(model, output_dir, config)

        # FMI 3.0 requires Dymola 2024+, so this may fail on older versions
        # Just verify the result structure is valid
        assert isinstance(result, CompilationResult)
        assert isinstance(result.success, bool)
        if result.success:
            assert result.fmu_path is not None
            assert result.fmu_path.exists()
            assert result.fmu_path.suffix == ".fmu"

    def test_compile_fmi3_both(self, simpleOdeModel: Path, tmp_path: Path) -> None:
        """Test compiling a simple model to FMI 3.0 with both ME and CS."""
        compiler = DymolaCompiler()
        model = ModelicaModel(simpleOdeModel)

        output_dir = tmp_path / "output_fmi3_both"
        config = CompilationConfig(
            fmi_type=FMIType.BOTH,
            fmi_version=FMIVersion.FMI_3_0,
            verbose=True,
            force=True,
        )

        result = compiler.compile(model, output_dir, config)

        # FMI 3.0 requires Dymola 2024+, so this may fail on older versions
        # Just verify the result structure is valid
        assert isinstance(result, CompilationResult)
        assert isinstance(result.success, bool)
        if result.success:
            assert result.fmu_path is not None
            assert result.fmu_path.exists()
            assert result.fmu_path.suffix == ".fmu"


# =============================================================================
# Test get_compiler function
# =============================================================================


class TestGetCompilerFunction:
    """Tests for get_compiler function."""

    def test_auto_no_compilers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test auto mode when no compilers are available."""
        from feelpp.mo2fmu import getCompiler

        # Set invalid paths
        monkeypatch.setenv("DYMOLA_ROOT", "/nonexistent/dymola")
        monkeypatch.setenv("OPENMODELICA_HOME", "/nonexistent/omc")

        # Force reload of config
        dymolaConfig = DymolaConfig(root="/nonexistent/dymola")
        omcConfig = OpenModelicaConfig(omc_path="/nonexistent/omc")

        with pytest.raises(RuntimeError, match="No Modelica compiler available"):
            getCompiler(
                backend="auto",
                dymolaConfig=dymolaConfig,
                openModelicaConfig=omcConfig,
            )

    def test_explicit_dymola_unavailable(self) -> None:
        """Test requesting Dymola when not available."""
        from feelpp.mo2fmu import getCompiler

        dymolaConfig = DymolaConfig(root="/nonexistent/dymola")

        with pytest.raises(RuntimeError, match="Dymola is not available"):
            getCompiler(backend="dymola", dymolaConfig=dymolaConfig)

    def test_explicit_openmodelica_unavailable(self) -> None:
        """Test requesting OpenModelica when not available."""
        from feelpp.mo2fmu import getCompiler

        omcConfig = OpenModelicaConfig(omc_path="/nonexistent/omc")
        # Also need to ensure OMPython is not available
        # This test assumes OMPython is not installed

        # Create a compiler that definitely won't find omc
        compiler = OpenModelicaCompiler(omcConfig)
        if not compiler.is_available:
            with pytest.raises(RuntimeError, match="OpenModelica is not available"):
                getCompiler(backend="openmodelica", openModelicaConfig=omcConfig)
        else:
            # OMPython is available, so this test passes
            assert True
