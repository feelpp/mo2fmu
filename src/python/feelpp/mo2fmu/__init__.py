"""Feel++ Modelica to FMU converter package."""

from __future__ import annotations

__version__ = "0.5.0"
__all__ = ["mo2fmu", "mo2fmuCLI"]

from feelpp.mo2fmu.mo2fmu import mo2fmu, mo2fmuCLI
