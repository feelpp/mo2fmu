"""Dymola compiler backend for mo2fmu.

This module implements FMU generation using Dymola (commercial Modelica tool).
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import spdlog as spd

from feelpp.mo2fmu.compilers.base import (
    CompilationConfig,
    CompilationResult,
    FMIType,
    FMUCompiler,
    ModelicaModel,
)

if TYPE_CHECKING:
    pass


@dataclass
class DymolaConfig:
    """Dymola-specific configuration.

    Attributes:
        root: Path to Dymola installation directory
        executable: Path to Dymola executable
        wheel_path: Path to Dymola Python wheel (relative to root)
        compile_64bit_only: Force 64-bit compilation only
        enable_code_export: Enable code export (license-free FMU execution)
        global_optimizations: Optimization level (0-2)
        linger_time: License release delay in seconds (0 = immediate)
    """

    root: str = "/opt/dymola-2025xRefresh1-x86_64/"
    executable: str = "/usr/local/bin/dymola"
    wheel_path: str = "Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl"
    compile_64bit_only: bool = True
    enable_code_export: bool = True
    global_optimizations: int = 2
    linger_time: int = 0
    additional_commands: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> DymolaConfig:
        """Create configuration from environment variables."""
        return cls(
            root=os.getenv("DYMOLA_ROOT", cls.root),
            executable=os.getenv("DYMOLA_EXECUTABLE", cls.executable),
            wheel_path=os.getenv("DYMOLA_WHL", cls.wheel_path),
        )


class DymolaCompiler(FMUCompiler):
    """Dymola-based FMU compiler.

    Uses Dymola's Python interface to compile Modelica models to FMUs.
    Requires a valid Dymola license for compilation.

    Example:
        >>> config = DymolaConfig.from_env()
        >>> compiler = DymolaCompiler(config)
        >>> if compiler.is_available:
        ...     model = ModelicaModel(Path("model.mo"))
        ...     result = compiler.compile(model, Path("output"), CompilationConfig())
        ...     if result.success:
        ...         print(f"FMU created at {result.fmu_path}")
    """

    def __init__(self, config: Optional[DymolaConfig] = None) -> None:
        """Initialize Dymola compiler.

        Args:
            config: Dymola configuration. If None, uses environment variables.
        """
        self._config = config or DymolaConfig.from_env()
        self._dymola_interface: Optional[Any] = None
        self._dymola_exception: Optional[type] = None
        self._vdisplay: Optional[Any] = None
        self._logger: Optional[Any] = None
        self._interface_loaded = False

        # Try to load Dymola interface
        self._load_interface()

    def _load_interface(self) -> bool:
        """Attempt to load the Dymola Python interface."""
        if self._interface_loaded:
            return True

        wheel_full_path = Path(self._config.root) / self._config.wheel_path
        if not wheel_full_path.is_file():
            return False

        try:
            sys.path.append(str(wheel_full_path))
            from dymola.dymola_exception import DymolaException
            from dymola.dymola_interface import DymolaInterface

            self._dymola_interface = DymolaInterface
            self._dymola_exception = DymolaException
            self._interface_loaded = True
            return True
        except ImportError:
            return False

    @property
    def name(self) -> str:
        """Return the compiler backend name."""
        return "dymola"

    @property
    def is_available(self) -> bool:
        """Check if Dymola is available on this system."""
        wheel_path = Path(self._config.root) / self._config.wheel_path
        return wheel_path.is_file() and self._load_interface()

    @property
    def config(self) -> DymolaConfig:
        """Return the Dymola configuration."""
        return self._config

    def get_version(self) -> Optional[str]:
        """Return the Dymola version string."""
        # Version is embedded in wheel path typically
        # e.g., "dymola-2025.1-py3-none-any.whl"
        wheel_name = Path(self._config.wheel_path).name
        if wheel_name.startswith("dymola-"):
            parts = wheel_name.split("-")
            if len(parts) >= 2:
                return parts[1]
        return None

    def _create_logger(self) -> Any:
        """Create a unique logger instance."""
        logger_name = f"dymola_{uuid.uuid4().hex[:8]}"
        return spd.ConsoleLogger(logger_name, False, True, True)

    def _start_display(self) -> None:
        """Start virtual framebuffer for headless operation."""
        if platform.system() != "Windows":
            from xvfbwrapper import Xvfb

            self._vdisplay = Xvfb()
            self._vdisplay.start()

    def _stop_display(self) -> None:
        """Stop virtual framebuffer."""
        if self._vdisplay is not None:
            self._vdisplay.stop()
            self._vdisplay = None

    def _setup_environment(self) -> None:
        """Configure environment for Dymola."""
        if "DYMOLA_LINGER_TIME" not in os.environ:
            os.environ["DYMOLA_LINGER_TIME"] = str(self._config.linger_time)

    def _configure_compiler(self, dymola: Any) -> None:
        """Apply Dymola compiler configuration."""
        if self._config.compile_64bit_only:
            dymola.ExecuteCommand("Advanced.CompileWith64=2;")

        if self._config.enable_code_export:
            dymola.ExecuteCommand("Advanced.EnableCodeExport=true;")

        if self._config.global_optimizations > 0:
            dymola.ExecuteCommand(
                f"Advanced.Define.GlobalOptimizations={self._config.global_optimizations};"
            )

        for cmd in self._config.additional_commands:
            dymola.ExecuteCommand(cmd)

    def _map_fmi_type(self, fmi_type: FMIType) -> str:
        """Map FMIType enum to Dymola string."""
        mapping = {
            FMIType.MODEL_EXCHANGE: "me",
            FMIType.CO_SIMULATION: "cs",
            FMIType.BOTH: "all",
            FMIType.CO_SIMULATION_SOLVER: "csSolver",
        }
        return mapping[fmi_type]

    def compile(
        self,
        model: ModelicaModel,
        output_dir: Path,
        config: CompilationConfig,
    ) -> CompilationResult:
        """Compile a Modelica model to FMU using Dymola.

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
                error_message="Dymola is not available. Check DYMOLA_ROOT and wheel path.",
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
        if target_fmu.is_file():
            if config.force:
                if config.verbose:
                    logger.warn(f"{fmu_name}.fmu exists in {output_dir}, will overwrite")
            else:
                return CompilationResult(
                    success=False,
                    error_message=f"{fmu_name}.fmu exists in {output_dir}. Use force=True to overwrite.",
                )

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Start display server
        self._start_display()
        self._setup_environment()

        dymola = None
        try:
            # Initialize Dymola (interface is guaranteed non-None after is_available check)
            dymola = self._dymola_interface(  # type: ignore[misc]
                dymolapath=self._config.executable, showwindow=False
            )

            # Configure compiler
            self._configure_compiler(dymola)

            # Load packages
            for package in config.packages:
                if config.verbose:
                    logger.info(f"Loading package: {package}")
                dymola.openModel(package, changeDirectory=False)

            # Apply custom flags
            for flag in config.flags:
                if config.verbose:
                    logger.info(f"Applying flag: {flag}")
                dymola.ExecuteCommand(flag)

            # Open the model file
            dymola.openModel(str(model.path), changeDirectory=False)

            # Set working directory
            cwd_posix = str(Path.cwd().as_posix())
            dymola.ExecuteCommand(f'cd("{cwd_posix}");')

            if config.verbose:
                logger.info(f"Compiling {model.fully_qualified_name} to {fmu_name}.fmu")

            # Translate to FMU
            result = dymola.translateModelFMU(
                model.fully_qualified_name,
                modelName=fmu_name,
                fmiVersion=config.fmi_version.value,
                fmiType=self._map_fmi_type(config.fmi_type),
            )

            if not result:
                error_log = dymola.getLastErrorLog()
                license_info = dymola.DymolaLicenseInfo()
                return CompilationResult(
                    success=False,
                    error_message="translateModelFMU returned False",
                    log=f"Error log:\n{error_log}\n\nLicense info:\n{license_info}",
                )

            # Verify FMU was created
            expected_fmu = Path.cwd() / f"{fmu_name}.fmu"
            if not expected_fmu.is_file():
                fmus_in_cwd = list(Path.cwd().glob("*.fmu"))
                return CompilationResult(
                    success=False,
                    error_message=f"Expected FMU '{expected_fmu.name}' not found",
                    log=f"FMUs in directory: {fmus_in_cwd}",
                )

            # Remove existing FMU if force is set
            if target_fmu.is_file() and config.force:
                target_fmu.unlink()

            # Move FMU to output directory
            dest = shutil.move(str(expected_fmu), str(output_dir))

            if config.verbose:
                logger.info(f"FMU successfully generated: {dest}")

            return CompilationResult(
                success=True,
                fmu_path=Path(dest),
            )

        except Exception as ex:
            if self._dymola_exception and isinstance(ex, self._dymola_exception):
                return CompilationResult(
                    success=False,
                    error_message=f"Dymola exception: {ex}",
                )
            raise

        finally:
            if dymola is not None:
                dymola.close()
            self._stop_display()
            spd.drop("Logger")

    def check_model(self, model: ModelicaModel, packages: Optional[list[str]] = None) -> bool:
        """Validate a Modelica model using Dymola.

        Args:
            model: The Modelica model to check
            packages: Additional packages to load

        Returns:
            True if the model is valid, False otherwise
        """
        if not self.is_available:
            return False

        self._start_display()
        self._setup_environment()

        dymola = None
        try:
            # Interface is guaranteed non-None after is_available check
            dymola = self._dymola_interface(  # type: ignore[misc]
                dymolapath=self._config.executable, showwindow=False
            )

            # Load packages
            if packages:
                for package in packages:
                    dymola.openModel(package, changeDirectory=False)

            # Open the model
            dymola.openModel(str(model.path), changeDirectory=False)

            # Check the model
            return bool(dymola.checkModel(model.fully_qualified_name))

        except Exception:
            return False

        finally:
            if dymola is not None:
                dymola.close()
            self._stop_display()

    def validate_fmu(self, fmu_path: Path, simulate: bool = True) -> bool:
        """Validate a generated FMU by importing and optionally simulating it.

        Args:
            fmu_path: Path to the FMU file
            simulate: Whether to run a simulation test

        Returns:
            True if validation passes, False otherwise
        """
        if not self.is_available:
            return False

        self._start_display()
        self._setup_environment()

        dymola = None
        try:
            # Interface is guaranteed non-None after is_available check
            dymola = self._dymola_interface(  # type: ignore[misc]
                dymolapath=self._config.executable, showwindow=False
            )

            # Import FMU
            imported = dymola.importFMU(str(fmu_path))
            if not imported:
                return False

            if simulate:
                # Get model name from FMU
                fmu_model = f"{fmu_path.stem}_fmu"
                return bool(dymola.checkModel(problem=fmu_model, simulate=True))

            return True

        except Exception:
            return False

        finally:
            if dymola is not None:
                dymola.close()
            self._stop_display()
