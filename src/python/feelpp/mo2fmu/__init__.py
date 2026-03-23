"""Feel++ Modelica to FMU converter package.

This package provides tools for converting Modelica models to
Functional Mock-up Units (FMUs) using either Dymola or OpenModelica.

Example:
    Using the primary API::

        from feelpp.mo2fmu import compileFmu, CompilationResult

        result = compileFmu("model.mo", "./output", backend="auto")
        if result.success:
            print(f"FMU created at {result.fmu_path}")

    Checking compiler availability::

        from feelpp.mo2fmu import checkCompilers

        results = checkCompilers()
        if results["dymola"]["available"]:
            print(f"Dymola {results['dymola']['version']} available")

    Using specific compilers::

        from feelpp.mo2fmu.compilers import DymolaCompiler, OpenModelicaCompiler

        compiler = OpenModelicaCompiler()
        if compiler.is_available:
            result = compiler.compile(model, output_dir, config)
"""

from __future__ import annotations

from importlib.metadata import version as _get_version

# Single source of truth: version comes from pyproject.toml
__version__ = _get_version("feelpp-mo2fmu")
__all__ = [
    "CompilationConfig",
    "CompilationRequest",
    "CompilationResult",
    "DymolaCompiler",
    "DymolaConfig",
    "FMUCompiler",
    "ModelicaModel",
    "OpenModelicaCompiler",
    "OpenModelicaConfig",
    "checkCompilers",
    "compileFmu",
    "compileFmus",
    "getCompiler",
    "get_compiler",
    "mo2fmu",
    "mo2fmuCLI",
    "mo2fmu_new",
]

from feelpp.mo2fmu.compilers.base import (
    CompilationConfig,
    CompilationRequest,
    CompilationResult,
    FMUCompiler,
    ModelicaModel,
)
from feelpp.mo2fmu.compilers.dymola import DymolaCompiler, DymolaConfig
from feelpp.mo2fmu.compilers.openmodelica import (
    OpenModelicaCompiler,
    OpenModelicaConfig,
)
from feelpp.mo2fmu.mo2fmu import (
    # Primary API
    checkCompilers,
    compileFmu,
    compileFmus,
    # Legacy API (deprecated)
    get_compiler,
    getCompiler,
    mo2fmu,
    mo2fmu_new,
    mo2fmuCLI,
)
