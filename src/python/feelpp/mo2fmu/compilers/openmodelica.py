"""OpenModelica compiler backend for mo2fmu.

This module implements FMU generation using OpenModelica (open source Modelica tool).

OpenModelica can be installed via:
- Linux: apt install openmodelica or from https://openmodelica.org/download
- macOS: brew install openmodelica
- Windows: Download from https://openmodelica.org/download

The OMPython package provides Python bindings:
    pip install OMPython
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import spdlog as spd

from feelpp.mo2fmu.compilers.base import (
    CompilationConfig,
    CompilationResult,
    FMIType,
    FMIVersion,
    FMUCompiler,
    ModelicaModel,
)


@dataclass
class OpenModelicaConfig:
    """OpenModelica-specific configuration.

    Attributes:
        omc_path: Path to omc executable (None = auto-detect from PATH)
        ompython_session: Use OMPython session instead of command line
        target_platform: Target platform for FMU (e.g., "static", "linux64")
        debug: Enable debug output
        cpp_compiler: C++ compiler to use (e.g., "g++", "clang++")
        c_compiler: C compiler to use (e.g., "gcc", "clang")
        num_procs: Number of parallel compilation processes
        command_line_options: Additional OMC command-line options
    """

    omc_path: Optional[str] = None
    ompython_session: bool = True
    target_platform: str = "static"
    debug: bool = False
    cpp_compiler: Optional[str] = None
    c_compiler: Optional[str] = None
    num_procs: int = 1
    command_line_options: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "OpenModelicaConfig":
        """Create configuration from environment variables."""
        return cls(
            omc_path=os.getenv("OPENMODELICA_HOME"),
            cpp_compiler=os.getenv("CXX"),
            c_compiler=os.getenv("CC"),
        )


class OpenModelicaCompiler(FMUCompiler):
    """OpenModelica-based FMU compiler.

    Uses OpenModelica's omc compiler or OMPython to compile Modelica models to FMUs.
    This is an open-source alternative to Dymola.

    Requires:
        - OpenModelica installed (omc in PATH or OPENMODELICA_HOME set)
        - OMPython package (pip install OMPython) for Python API mode

    Example:
        >>> config = OpenModelicaConfig.from_env()
        >>> compiler = OpenModelicaCompiler(config)
        >>> if compiler.is_available:
        ...     model = ModelicaModel(Path("model.mo"))
        ...     result = compiler.compile(model, Path("output"), CompilationConfig())
        ...     if result.success:
        ...         print(f"FMU created at {result.fmu_path}")
    """

    def __init__(self, config: Optional[OpenModelicaConfig] = None) -> None:
        """Initialize OpenModelica compiler.

        Args:
            config: OpenModelica configuration. If None, uses defaults/environment.
        """
        self._config = config or OpenModelicaConfig.from_env()
        self._omc_session: Optional[Any] = None
        self._ompython_available = False
        self._omc_cli_available = False
        self._logger: Optional[Any] = None

        self._check_availability()

    def _check_availability(self) -> None:
        """Check if OpenModelica is available."""
        # Check command-line omc first (required for both CLI and OMPython modes)
        omc_cmd = self._get_omc_command()
        try:
            result = subprocess.run(
                [omc_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._omc_cli_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self._omc_cli_available = False

        # Check OMPython (requires omc to be available)
        # OMPython is a Python interface to communicate with omc, so omc must be installed
        try:
            from OMPython import OMCSessionZMQ

            # OMPython package is installed, but it needs omc to work
            self._ompython_available = self._omc_cli_available
        except ImportError:
            self._ompython_available = False

    def _get_omc_command(self) -> str:
        """Get the omc command path."""
        if self._config.omc_path:
            omc_bin = Path(self._config.omc_path) / "bin" / "omc"
            if omc_bin.is_file():
                return str(omc_bin)
        return "omc"

    @property
    def name(self) -> str:
        """Return the compiler backend name."""
        return "openmodelica"

    @property
    def is_available(self) -> bool:
        """Check if OpenModelica is available on this system."""
        return self._ompython_available or self._omc_cli_available

    @property
    def config(self) -> OpenModelicaConfig:
        """Return the OpenModelica configuration."""
        return self._config

    def get_version(self) -> Optional[str]:
        """Return the OpenModelica version string."""
        omc_cmd = self._get_omc_command()
        try:
            result = subprocess.run(
                [omc_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse version from output like "OpenModelica v1.22.0"
                version_line = result.stdout.strip().split("\n")[0]
                if "OpenModelica" in version_line:
                    parts = version_line.split()
                    for part in parts:
                        if part.startswith("v") or part[0].isdigit():
                            return part.lstrip("v")
                return version_line
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def _create_logger(self) -> Any:
        """Create a unique logger instance."""
        logger_name = f"omc_{uuid.uuid4().hex[:8]}"
        return spd.ConsoleLogger(logger_name, False, True, True)

    def _map_fmi_type(self, fmi_type: FMIType) -> str:
        """Map FMIType enum to OpenModelica string."""
        mapping = {
            FMIType.MODEL_EXCHANGE: "me",
            FMIType.CO_SIMULATION: "cs",
            FMIType.BOTH: "me_cs",  # OpenModelica uses me_cs for both
            FMIType.CO_SIMULATION_SOLVER: "cs",  # Fallback to cs
        }
        return mapping[fmi_type]

    def _map_fmi_version(self, fmi_version: FMIVersion) -> str:
        """Map FMIVersion enum to OpenModelica string."""
        mapping = {
            FMIVersion.FMI_1_0: "1.0",
            FMIVersion.FMI_2_0: "2.0",
            FMIVersion.FMI_3_0: "3.0",
        }
        return mapping[fmi_version]

    def _build_fmu_flags(self, config: CompilationConfig) -> str:
        """Build the FMU flags string for buildModelFMU."""
        fmi_version = self._map_fmi_version(config.fmi_version)
        fmi_type = self._map_fmi_type(config.fmi_type)

        # Build platforms list
        platforms = f'{{"{self._config.target_platform}"}}'

        return f'version="{fmi_version}", fmuType="{fmi_type}", platforms={platforms}'

    def _compile_with_ompython(
        self,
        model: ModelicaModel,
        output_dir: Path,
        config: CompilationConfig,
        logger: Any,
    ) -> CompilationResult:
        """Compile using OMPython session."""
        from OMPython import OMCSessionZMQ

        fmu_name = config.output_name or model.model_name
        target_fmu = output_dir / f"{fmu_name}.fmu"

        omc = None
        original_cwd = Path.cwd()

        try:
            # Create OMC session
            omc = OMCSessionZMQ()

            if config.verbose:
                logger.info("OMC session started")

            # Change to a temporary working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Set working directory in OMC
                cd_result = omc.sendExpression(f'cd("{temp_path.as_posix()}")')
                if config.verbose:
                    logger.info(f"Working directory: {cd_result}")

                # Load packages
                for package in config.packages:
                    if config.verbose:
                        logger.info(f"Loading package: {package}")

                    pkg_path = Path(package)
                    if pkg_path.suffix == ".mo":
                        result = omc.sendExpression(f'loadFile("{pkg_path.as_posix()}")')
                    else:
                        result = omc.sendExpression(f'loadModel({package})')

                    if not result:
                        error = omc.sendExpression("getErrorString()")
                        logger.warn(f"Failed to load {package}: {error}")

                # Apply command-line options
                for opt in self._config.command_line_options:
                    omc.sendExpression(f'setCommandLineOptions("{opt}")')

                # Apply custom flags
                for flag in config.flags:
                    if config.verbose:
                        logger.info(f"Applying flag: {flag}")
                    omc.sendExpression(flag)

                # Load the model file
                load_result = omc.sendExpression(f'loadFile("{model.path.as_posix()}")')
                if not load_result:
                    error = omc.sendExpression("getErrorString()")
                    return CompilationResult(
                        success=False,
                        error_message=f"Failed to load model: {error}",
                    )

                if config.verbose:
                    logger.info(f"Model loaded: {model.fully_qualified_name}")

                # Check model first
                check_result = omc.sendExpression(f"checkModel({model.fully_qualified_name})")
                if config.verbose:
                    logger.info(f"Model check result: {check_result}")

                # Build FMU flags
                fmu_flags = self._build_fmu_flags(config)

                # Build the FMU
                build_cmd = f"buildModelFMU({model.fully_qualified_name}, {fmu_flags})"
                if config.verbose:
                    logger.info(f"Build command: {build_cmd}")

                fmu_result = omc.sendExpression(build_cmd)

                if config.verbose:
                    logger.info(f"Build result: {fmu_result}")

                # Check for errors
                error_string = omc.sendExpression("getErrorString()")
                if error_string and "Error" in error_string:
                    return CompilationResult(
                        success=False,
                        error_message="FMU compilation failed",
                        log=error_string,
                    )

                # Find the generated FMU
                if fmu_result and isinstance(fmu_result, str) and fmu_result.endswith(".fmu"):
                    generated_fmu = Path(fmu_result)
                else:
                    # Look for FMU in temp directory
                    fmus = list(temp_path.glob("*.fmu"))
                    if not fmus:
                        return CompilationResult(
                            success=False,
                            error_message="No FMU file generated",
                            log=error_string,
                        )
                    generated_fmu = fmus[0]

                if not generated_fmu.is_file():
                    return CompilationResult(
                        success=False,
                        error_message=f"Generated FMU not found: {generated_fmu}",
                        log=error_string,
                    )

                # Remove existing FMU if force is set
                if target_fmu.is_file() and config.force:
                    target_fmu.unlink()

                # Copy FMU to output directory
                shutil.copy2(generated_fmu, target_fmu)

                if config.verbose:
                    logger.info(f"FMU successfully generated: {target_fmu}")

                warnings = []
                if error_string and error_string.strip():
                    warnings = [
                        line
                        for line in error_string.split("\n")
                        if line.strip() and "Warning" in line
                    ]

                return CompilationResult(
                    success=True,
                    fmu_path=target_fmu,
                    log=error_string if error_string else None,
                    warnings=warnings,
                )

        except Exception as ex:
            return CompilationResult(
                success=False,
                error_message=f"OMPython exception: {ex}",
            )

        finally:
            if omc is not None:
                try:
                    omc.sendExpression("quit()")
                except Exception:
                    pass
            os.chdir(original_cwd)

    def _compile_with_cli(
        self,
        model: ModelicaModel,
        output_dir: Path,
        config: CompilationConfig,
        logger: Any,
    ) -> CompilationResult:
        """Compile using omc command line."""
        fmu_name = config.output_name or model.model_name
        target_fmu = output_dir / f"{fmu_name}.fmu"
        omc_cmd = self._get_omc_command()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Build the .mos script
            script_lines = []

            # Load packages
            for package in config.packages:
                pkg_path = Path(package)
                if pkg_path.suffix == ".mo":
                    script_lines.append(f'loadFile("{pkg_path.as_posix()}");')
                else:
                    script_lines.append(f"loadModel({package});")

            # Apply command-line options
            for opt in self._config.command_line_options:
                script_lines.append(f'setCommandLineOptions("{opt}");')

            # Apply custom flags
            for flag in config.flags:
                script_lines.append(flag if flag.endswith(";") else f"{flag};")

            # Load model
            script_lines.append(f'loadFile("{model.path.as_posix()}");')

            # Build FMU
            fmu_flags = self._build_fmu_flags(config)
            script_lines.append(f"buildModelFMU({model.fully_qualified_name}, {fmu_flags});")

            # Get errors
            script_lines.append("getErrorString();")

            # Write script
            script_path = temp_path / "build_fmu.mos"
            with open(script_path, "w") as f:
                f.write("\n".join(script_lines))

            if config.verbose:
                logger.info(f"OMC script:\n{chr(10).join(script_lines)}")

            # Run omc
            try:
                result = subprocess.run(
                    [omc_cmd, str(script_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(temp_path),
                    timeout=600,  # 10 minute timeout
                )
            except subprocess.TimeoutExpired:
                return CompilationResult(
                    success=False,
                    error_message="OMC compilation timed out after 10 minutes",
                )

            output = result.stdout + "\n" + result.stderr

            if config.verbose:
                logger.info(f"OMC output:\n{output}")

            # Check for generated FMU
            fmus = list(temp_path.glob("*.fmu"))
            if not fmus:
                return CompilationResult(
                    success=False,
                    error_message="No FMU file generated",
                    log=output,
                )

            generated_fmu = fmus[0]

            # Remove existing FMU if force is set
            if target_fmu.is_file() and config.force:
                target_fmu.unlink()

            # Copy FMU to output directory
            shutil.copy2(generated_fmu, target_fmu)

            if config.verbose:
                logger.info(f"FMU successfully generated: {target_fmu}")

            return CompilationResult(
                success=True,
                fmu_path=target_fmu,
                log=output,
            )

    def compile(
        self,
        model: ModelicaModel,
        output_dir: Path,
        config: CompilationConfig,
    ) -> CompilationResult:
        """Compile a Modelica model to FMU using OpenModelica.

        Args:
            model: The Modelica model to compile
            output_dir: Directory to place the generated FMU
            config: Compilation configuration options

        Returns:
            CompilationResult with success status and FMU path or error info
        """
        if not self.is_available:
            return CompilationResult(
                success=False,
                error_message="OpenModelica is not available. Install omc and/or OMPython.",
            )

        logger = self._create_logger()
        output_dir = Path(output_dir)

        # Validate output directory
        if output_dir == Path.cwd():
            return CompilationResult(
                success=False,
                error_message=f"Output directory must differ from current directory: {Path.cwd()}",
            )

        # Determine output FMU name
        fmu_name = config.output_name or model.model_name
        target_fmu = output_dir / f"{fmu_name}.fmu"

        # Check existing FMU
        if target_fmu.is_file() and not config.force:
            return CompilationResult(
                success=False,
                error_message=f"{fmu_name}.fmu exists in {output_dir}. Use force=True to overwrite.",
            )

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Choose compilation method
        if self._config.ompython_session and self._ompython_available:
            return self._compile_with_ompython(model, output_dir, config, logger)
        elif self._omc_cli_available:
            return self._compile_with_cli(model, output_dir, config, logger)
        else:
            return CompilationResult(
                success=False,
                error_message="Neither OMPython nor omc CLI is available",
            )

    def check_model(self, model: ModelicaModel, packages: Optional[list[str]] = None) -> bool:
        """Validate a Modelica model using OpenModelica.

        Args:
            model: The Modelica model to check
            packages: Additional packages to load

        Returns:
            True if the model is valid, False otherwise
        """
        if not self.is_available:
            return False

        if self._ompython_available:
            return self._check_model_ompython(model, packages)
        elif self._omc_cli_available:
            return self._check_model_cli(model, packages)
        return False

    def _check_model_ompython(
        self, model: ModelicaModel, packages: Optional[list[str]] = None
    ) -> bool:
        """Check model using OMPython."""
        from OMPython import OMCSessionZMQ

        omc = None
        try:
            omc = OMCSessionZMQ()

            # Load packages
            if packages:
                for package in packages:
                    pkg_path = Path(package)
                    if pkg_path.suffix == ".mo":
                        omc.sendExpression(f'loadFile("{pkg_path.as_posix()}")')
                    else:
                        omc.sendExpression(f"loadModel({package})")

            # Load model
            omc.sendExpression(f'loadFile("{model.path.as_posix()}")')

            # Check model
            result = omc.sendExpression(f"checkModel({model.fully_qualified_name})")
            return result is not None and "Error" not in str(result)

        except Exception:
            return False

        finally:
            if omc is not None:
                try:
                    omc.sendExpression("quit()")
                except Exception:
                    pass

    def _check_model_cli(
        self, model: ModelicaModel, packages: Optional[list[str]] = None
    ) -> bool:
        """Check model using omc CLI."""
        omc_cmd = self._get_omc_command()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            script_lines = []

            # Load packages
            if packages:
                for package in packages:
                    pkg_path = Path(package)
                    if pkg_path.suffix == ".mo":
                        script_lines.append(f'loadFile("{pkg_path.as_posix()}");')
                    else:
                        script_lines.append(f"loadModel({package});")

            # Load and check model
            script_lines.append(f'loadFile("{model.path.as_posix()}");')
            script_lines.append(f"checkModel({model.fully_qualified_name});")
            script_lines.append("getErrorString();")

            script_path = temp_path / "check_model.mos"
            with open(script_path, "w") as f:
                f.write("\n".join(script_lines))

            try:
                result = subprocess.run(
                    [omc_cmd, str(script_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(temp_path),
                    timeout=60,
                )
                return result.returncode == 0 and "Error" not in result.stdout
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                return False
