"""Compiler backends for mo2fmu.

This module provides abstract base classes and implementations for
different Modelica-to-FMU compilers.

Available compilers:
- DymolaCompiler: Uses Dymola (commercial) for FMU generation
- OpenModelicaCompiler: Uses OpenModelica (open source) for FMU generation
"""

from __future__ import annotations

from feelpp.mo2fmu.compilers.base import (
    CompilationConfig,
    CompilationResult,
    FMUCompiler,
    ModelicaModel,
)
from feelpp.mo2fmu.compilers.dymola import DymolaCompiler
from feelpp.mo2fmu.compilers.openmodelica import OpenModelicaCompiler

__all__ = [
    "FMUCompiler",
    "CompilationConfig",
    "CompilationResult",
    "ModelicaModel",
    "DymolaCompiler",
    "OpenModelicaCompiler",
]
