"""Dymola compiler backend for mo2fmu.

This module implements FMU generation using Dymola (commercial Modelica tool).
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Optional

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
        startup_retry_timeout: Time to keep retrying when no shareable license is available
        startup_retry_interval: Delay between startup retries
    """

    root: str = "/opt/dymola-2025xRefresh1-x86_64/"
    executable: str = "/usr/local/bin/dymola"
    wheel_path: str = "Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl"
    compile_64bit_only: bool = True
    enable_code_export: bool = True
    global_optimizations: int = 2
    linger_time: int = 0
    startup_retry_timeout: int = 0
    startup_retry_interval: int = 30
    additional_commands: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> DymolaConfig:
        """Create configuration from environment variables."""
        return cls(
            root=os.getenv("DYMOLA_ROOT", cls.root),
            executable=os.getenv("DYMOLA_EXECUTABLE", cls.executable),
            wheel_path=os.getenv("DYMOLA_WHL", cls.wheel_path),
            startup_retry_timeout=int(os.getenv("DYMOLA_STARTUP_RETRY_TIMEOUT", "0")),
            startup_retry_interval=int(os.getenv("DYMOLA_STARTUP_RETRY_INTERVAL", "30")),
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
        self._activeSession: Optional[Any] = None
        self._sessionDepth = 0
        self._loadedPackages: set[str] = set()
        self._loadedModels: set[str] = set()

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

    def _licenseUnavailable(self, licenseInfo: Any) -> bool:
        """Check whether Dymola fell back to a non-shareable license."""
        licenseText = str(licenseInfo).lower()
        unavailablePatterns = [
            "trial version",
            "shareable license users exceeded",
            "maximum number of shareable license users exceeded",
            "license checkout failed",
        ]
        return any(pattern in licenseText for pattern in unavailablePatterns)

    def _createSession(self) -> Any:
        """Start a configured Dymola session, retrying on transient license fallback."""
        self._start_display()
        self._setup_environment()

        deadline = None
        if self._config.startup_retry_timeout > 0:
            deadline = time.monotonic() + self._config.startup_retry_timeout

        try:
            while True:
                dymola = self._dymola_interface(  # type: ignore[misc]
                    dymolapath=self._config.executable, showwindow=False
                )
                licenseInfo = dymola.DymolaLicenseInfo()
                if not self._licenseUnavailable(licenseInfo):
                    self._configure_compiler(dymola)
                    self._loadedPackages.clear()
                    self._loadedModels.clear()
                    return dymola

                dymola.close()

                if deadline is None or time.monotonic() >= deadline:
                    msg = "Dymola shareable license is not available"
                    errorMessage = f"{msg}.\nLicense info:\n{licenseInfo}"
                    raise RuntimeError(errorMessage)

                time.sleep(self._config.startup_retry_interval)
        except Exception:
            self._stop_display()
            raise

    def _closeSession(self) -> None:
        """Close the active Dymola session and clear cached state."""
        if self._activeSession is not None:
            self._activeSession.close()
            self._activeSession = None
        self._loadedPackages.clear()
        self._loadedModels.clear()
        self._stop_display()

    @contextmanager
    def session(self) -> Iterator[DymolaCompiler]:
        """Keep one Dymola process alive across multiple compile calls."""
        if not self.is_available:
            msg = "Dymola is not available. Check DYMOLA_ROOT and wheel path."
            raise RuntimeError(msg)

        createdSession = False
        if self._activeSession is None:
            self._activeSession = self._createSession()
            createdSession = True

        self._sessionDepth += 1
        try:
            yield self
        finally:
            self._sessionDepth -= 1
            if createdSession and self._sessionDepth == 0:
                self._closeSession()

    def _loadPackage(self, dymola: Any, package: str, verbose: bool) -> None:
        """Load a package only once per Dymola session."""
        if package in self._loadedPackages:
            return

        logger = self._logger
        if verbose and logger is not None:
            logger.info(f"Loading package: {package}")
        dymola.openModel(package, changeDirectory=False)
        self._loadedPackages.add(package)

    def _loadModel(self, dymola: Any, model: ModelicaModel) -> None:
        """Load a model file only once per Dymola session."""
        modelPath = str(model.path)
        if modelPath in self._loadedModels:
            return

        dymola.openModel(modelPath, changeDirectory=False)
        self._loadedModels.add(modelPath)

    def compileMany(
        self,
        jobs: list[tuple[ModelicaModel, Path, CompilationConfig]],
    ) -> list[CompilationResult]:
        """Compile several models while reusing one Dymola session."""
        results: list[CompilationResult] = []
        try:
            with self.session():
                for model, outputDir, config in jobs:
                    results.append(self.compile(model, outputDir, config))
        except RuntimeError as ex:
            return [
                CompilationResult(
                    success=False,
                    error_message=str(ex),
                )
                for _model, _outputDir, _config in jobs
            ]
        return results

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

        try:
            with self.session():
                dymola = self._activeSession
                assert dymola is not None

                self._logger = logger

                # Load packages
                for package in config.packages:
                    self._loadPackage(dymola, package, config.verbose)

                # Apply custom flags
                for flag in config.flags:
                    if config.verbose:
                        logger.info(f"Applying flag: {flag}")
                    dymola.ExecuteCommand(flag)

                # Open the model file
                self._loadModel(dymola, model)

                # Set working directory
                cwd_posix = str(Path.cwd().as_posix())
                dymola.ExecuteCommand(f'cd("{cwd_posix}");')

                if config.verbose:
                    logger.info(f"Compiling {model.fully_qualified_name} to {fmu_name}.fmu")

                expected_fmu = Path.cwd() / f"{fmu_name}.fmu"
                if expected_fmu.is_file():
                    expected_fmu.unlink()

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

        except RuntimeError as ex:
            return CompilationResult(
                success=False,
                error_message=str(ex),
            )

        except Exception as ex:
            if self._dymola_exception and isinstance(ex, self._dymola_exception):
                return CompilationResult(
                    success=False,
                    error_message=f"Dymola exception: {ex}",
                )
            raise

        finally:
            self._logger = None
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
        try:
            with self.session():
                dymola = self._activeSession
                assert dymola is not None

                # Load packages
                if packages:
                    for package in packages:
                        self._loadPackage(dymola, package, False)

                # Open the model
                self._loadModel(dymola, model)

                # Check the model
                return bool(dymola.checkModel(model.fully_qualified_name))

        except Exception:
            return False

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
        try:
            with self.session():
                dymola = self._activeSession
                assert dymola is not None

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
