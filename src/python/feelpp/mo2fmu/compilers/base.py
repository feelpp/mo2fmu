"""Base classes for FMU compiler backends.

This module defines the abstract interface and data structures for
Modelica-to-FMU compilation backends.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Union


class FMIType(Enum):
    """FMI export type."""

    MODEL_EXCHANGE = "me"
    CO_SIMULATION = "cs"
    BOTH = "all"
    CO_SIMULATION_SOLVER = "csSolver"

    @classmethod
    def from_string(cls, value: str) -> FMIType:
        """Convert string to FMIType."""
        mapping = {
            "me": cls.MODEL_EXCHANGE,
            "cs": cls.CO_SIMULATION,
            "all": cls.BOTH,
            "csSolver": cls.CO_SIMULATION_SOLVER,
        }
        if value not in mapping:
            msg = f"Invalid FMI type: {value}. Valid options: {list(mapping.keys())}"
            raise ValueError(msg)
        return mapping[value]


class FMIVersion(Enum):
    """FMI specification version."""

    FMI_1_0 = "1"
    FMI_2_0 = "2"
    FMI_3_0 = "3"

    @classmethod
    def from_string(cls, value: str) -> FMIVersion:
        """Convert string to FMIVersion."""
        mapping = {"1": cls.FMI_1_0, "2": cls.FMI_2_0, "3": cls.FMI_3_0}
        if value not in mapping:
            msg = f"Invalid FMI version: {value}. Valid options: {list(mapping.keys())}"
            raise ValueError(msg)
        return mapping[value]


@dataclass
class ModelicaModel:
    """Representation of a Modelica model to compile.

    Attributes:
        path: Path to the .mo file
        package_name: The package name extracted from 'within' statement
        model_name: The model class name (usually the file stem)
        fully_qualified_name: Full model name (package.model)
    """

    path: Path
    package_name: Optional[str] = None
    model_name: Optional[str] = None
    fully_qualified_name: Optional[str] = None

    def __post_init__(self) -> None:
        """Initialize derived attributes from the .mo file."""
        self.path = Path(self.path)

        if self.model_name is None:
            self.model_name = self.path.stem

        if self.package_name is None:
            self.package_name = self._extract_package_name()

        if self.fully_qualified_name is None:
            if self.package_name:
                self.fully_qualified_name = f"{self.package_name}.{self.model_name}"
            else:
                self.fully_qualified_name = self.model_name

    def _extract_package_name(self) -> Optional[str]:
        """Extract package name from 'within' statement in .mo file."""
        try:
            with open(self.path) as f:
                content = f.read()

            # Match 'within PackageName;' or 'within Package.SubPackage;'
            match = re.search(r"within\s+([\w.]+)\s*;", content)
            if match:
                return match.group(1)
        except OSError:
            pass
        return None


@dataclass
class CompilationConfig:
    """Configuration for FMU compilation.

    Attributes:
        fmi_type: Type of FMU export (cs, me, all, csSolver)
        fmi_version: FMI specification version
        output_name: Custom name for the output FMU (defaults to model name)
        packages: List of additional Modelica packages to load
        flags: Backend-specific compilation flags
        force: Overwrite existing FMU if present
        verbose: Enable verbose logging
        optimize: Enable compiler optimizations
        include_sources: Include source code in FMU
    """

    fmi_type: FMIType = FMIType.BOTH
    fmi_version: FMIVersion = FMIVersion.FMI_2_0
    output_name: Optional[str] = None
    packages: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    force: bool = False
    verbose: bool = False
    optimize: bool = True
    include_sources: bool = False

    @classmethod
    def from_legacy(
        cls,
        type: str = "all",
        version: str = "2",
        fmumodelname: Optional[str] = None,
        load: Optional[tuple[str, ...]] = None,
        flags: Optional[tuple[str, ...]] = None,
        force: bool = False,
        verbose: bool = False,
    ) -> CompilationConfig:
        """Create config from legacy mo2fmu parameters."""
        return cls(
            fmi_type=FMIType.from_string(type),
            fmi_version=FMIVersion.from_string(version),
            output_name=fmumodelname,
            packages=list(load) if load else [],
            flags=list(flags) if flags else [],
            force=force,
            verbose=verbose,
        )


@dataclass
class CompilationRequest:
    """High-level request for compiling a single FMU.

    This is intended for batch workflows that need to keep compiler-specific
    state alive across multiple FMU exports.
    """

    mo: Union[str, Path]
    outdir: Union[str, Path]
    fmu_model_name: Optional[str] = None
    load: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    fmi_type: str = "all"
    fmi_version: str = "2"
    verbose: bool = False
    force: bool = False

    def createModel(self) -> ModelicaModel:
        """Create the Modelica model object for this request."""
        return ModelicaModel(Path(self.mo))

    def createConfig(self) -> CompilationConfig:
        """Create the low-level compilation config for this request."""
        return CompilationConfig(
            fmi_type=FMIType.from_string(self.fmi_type),
            fmi_version=FMIVersion.from_string(self.fmi_version),
            output_name=self.fmu_model_name,
            packages=list(self.load),
            flags=list(self.flags),
            force=self.force,
            verbose=self.verbose,
        )


@dataclass
class CompilationResult:
    """Result of FMU compilation.

    Attributes:
        success: Whether compilation succeeded
        fmu_path: Path to the generated FMU (if successful)
        error_message: Error description (if failed)
        log: Full compilation log
        warnings: List of warning messages
    """

    success: bool
    fmu_path: Optional[Path] = None
    error_message: Optional[str] = None
    log: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


class FMUCompiler(ABC):
    """Abstract base class for Modelica-to-FMU compilers.

    Subclasses implement specific compiler backends (Dymola, OpenModelica, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the compiler backend name."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the compiler is available on this system."""

    @abstractmethod
    def compile(
        self,
        model: ModelicaModel,
        output_dir: Path,
        config: CompilationConfig,
    ) -> CompilationResult:
        """Compile a Modelica model to FMU.

        Args:
            model: The Modelica model to compile
            output_dir: Directory to place the generated FMU
            config: Compilation configuration options

        Returns:
            CompilationResult with success status and FMU path or error info
        """

    @abstractmethod
    def check_model(self, model: ModelicaModel, packages: Optional[list[str]] = None) -> bool:
        """Validate a Modelica model without generating FMU.

        Args:
            model: The Modelica model to check
            packages: Additional packages to load

        Returns:
            True if the model is valid, False otherwise
        """

    def get_version(self) -> Optional[str]:
        """Return the compiler version string, if available."""
        return None
