"""mo2fmu - Convert Modelica models to Functional Mock-up Units (FMUs).

This module provides both a Python API and CLI for converting Modelica
models to FMUs using either Dymola (commercial) or OpenModelica (open source).
"""

from __future__ import annotations

import warnings
from importlib.metadata import version as get_version
from pathlib import Path
from typing import Literal, Optional

import click

# Import compiler classes
from feelpp.mo2fmu.compilers.base import (
    CompilationConfig,
    CompilationRequest,
    CompilationResult,
    FMIType,
    FMIVersion,
    FMUCompiler,
    ModelicaModel,
)
from feelpp.mo2fmu.compilers.dymola import DymolaCompiler, DymolaConfig
from feelpp.mo2fmu.compilers.openmodelica import (
    OpenModelicaCompiler,
    OpenModelicaConfig,
)

# Type alias for backend selection
Backend = Literal["dymola", "openmodelica", "auto"]


# =============================================================================
# Public API Functions (camelCase)
# =============================================================================


def checkCompilers(
    dymolaConfig: Optional[DymolaConfig] = None,
    openModelicaConfig: Optional[OpenModelicaConfig] = None,
) -> dict[str, dict[str, object]]:
    """Check availability and FMI version support for all compilers.

    Args:
        dymolaConfig: Configuration for Dymola compiler
        openModelicaConfig: Configuration for OpenModelica compiler

    Returns:
        Dictionary with compiler availability and FMI support information
    """
    results: dict[str, dict[str, object]] = {
        "dymola": {
            "available": False,
            "version": None,
            "fmiSupport": [],
        },
        "openmodelica": {
            "available": False,
            "version": None,
            "fmiSupport": [],
        },
    }

    # Check Dymola
    dymola = DymolaCompiler(dymolaConfig)
    results["dymola"]["available"] = dymola.is_available
    if dymola.is_available:
        dymolaVersion = dymola.get_version()
        results["dymola"]["version"] = dymolaVersion
        # Dymola 2024+ supports FMI 3.0, earlier versions support FMI 1.0 and 2.0
        fmiSupport: list[str] = ["1", "2"]
        if dymolaVersion:
            try:
                # Version format: "2025.1" or "2024.1"
                majorVersion = int(dymolaVersion.split(".")[0])
                if majorVersion >= 2024:
                    fmiSupport.append("3")
            except (ValueError, IndexError):
                pass  # Keep default FMI 1.0 and 2.0 support
        results["dymola"]["fmiSupport"] = fmiSupport

    # Check OpenModelica
    omc = OpenModelicaCompiler(openModelicaConfig)
    results["openmodelica"]["available"] = omc.is_available
    if omc.is_available:
        omcVersion = omc.get_version()
        results["openmodelica"]["version"] = omcVersion
        # OpenModelica 1.21+ supports FMI 3.0, earlier versions support FMI 1.0 and 2.0
        fmiSupport = ["1", "2"]
        if omcVersion:
            try:
                # Version format: "1.22.0" or "1.21.0"
                parts = omcVersion.split(".")
                major = int(parts[0])
                minor = int(parts[1]) if len(parts) > 1 else 0
                if major > 1 or (major == 1 and minor >= 21):
                    fmiSupport.append("3")
            except (ValueError, IndexError):
                pass  # Keep default FMI 1.0 and 2.0 support
        results["openmodelica"]["fmiSupport"] = fmiSupport

    return results


def getCompiler(
    backend: Backend = "auto",
    dymolaConfig: Optional[DymolaConfig] = None,
    openModelicaConfig: Optional[OpenModelicaConfig] = None,
) -> FMUCompiler:
    """Get an FMU compiler instance.

    Args:
        backend: Compiler backend to use ("dymola", "openmodelica", or "auto")
        dymolaConfig: Configuration for Dymola compiler
        openModelicaConfig: Configuration for OpenModelica compiler

    Returns:
        An FMUCompiler instance

    Raises:
        RuntimeError: If no suitable compiler is available
    """
    if backend == "dymola":
        dymolaCompiler = DymolaCompiler(dymolaConfig)
        if not dymolaCompiler.is_available:
            msg = "Dymola is not available. Check installation and configuration."
            raise RuntimeError(msg)
        return dymolaCompiler

    if backend == "openmodelica":
        omcCompiler = OpenModelicaCompiler(openModelicaConfig)
        if not omcCompiler.is_available:
            msg = "OpenModelica is not available. Install omc and/or OMPython."
            raise RuntimeError(msg)
        return omcCompiler

    # Auto-detection: prefer Dymola if available, fall back to OpenModelica
    dymola = DymolaCompiler(dymolaConfig)
    if dymola.is_available:
        return dymola

    omc = OpenModelicaCompiler(openModelicaConfig)
    if omc.is_available:
        return omc

    msg = "No Modelica compiler available. Install Dymola or OpenModelica."
    raise RuntimeError(msg)


def compileFmu(
    mo: str | Path,
    outdir: str | Path,
    backend: Backend = "auto",
    fmuModelName: Optional[str] = None,
    load: Optional[list[str]] = None,
    flags: Optional[list[str]] = None,
    fmiType: str = "all",
    fmiVersion: str = "2",
    verbose: bool = False,
    force: bool = False,
    dymolaConfig: Optional[DymolaConfig] = None,
    openModelicaConfig: Optional[OpenModelicaConfig] = None,
) -> CompilationResult:
    """Convert a Modelica model to FMU.

    This is the primary API for FMU compilation.

    Args:
        mo: Path to the Modelica .mo file
        outdir: Output directory for the generated FMU
        backend: Compiler backend ("dymola", "openmodelica", or "auto")
        fmuModelName: Custom name for the FMU (defaults to model name)
        load: List of Modelica packages to load
        flags: List of compiler-specific flags
        fmiType: FMI type ("cs", "me", "all", or "csSolver")
        fmiVersion: FMI version ("1", "2", or "3")
        verbose: Enable verbose logging
        force: Overwrite existing FMU if present
        dymolaConfig: Dymola-specific configuration
        openModelicaConfig: OpenModelica-specific configuration

    Returns:
        CompilationResult with success status and FMU path or error info

    Example:
        >>> result = compileFmu("model.mo", "./output", backend="auto")
        >>> if result.success:
        ...     print(f"FMU created at {result.fmu_path}")
        ... else:
        ...     print(f"Error: {result.error_message}")
    """
    # Get compiler
    compiler = getCompiler(backend, dymolaConfig, openModelicaConfig)

    # Create model representation
    model = ModelicaModel(Path(mo))

    # Create compilation config
    config = CompilationConfig(
        fmi_type=FMIType.from_string(fmiType),
        fmi_version=FMIVersion.from_string(fmiVersion),
        output_name=fmuModelName,
        packages=load or [],
        flags=flags or [],
        force=force,
        verbose=verbose,
    )

    # Compile
    return compiler.compile(model, Path(outdir), config)


def compileFmus(
    requests: list[CompilationRequest],
    backend: Backend = "auto",
    dymolaConfig: Optional[DymolaConfig] = None,
    openModelicaConfig: Optional[OpenModelicaConfig] = None,
) -> list[CompilationResult]:
    """Compile several Modelica models to FMUs.

    When the Dymola backend is selected, this keeps one Dymola session alive
    across the whole batch to avoid repeated license checkout/release cycles.

    Args:
        requests: Per-FMU compilation requests
        backend: Compiler backend ("dymola", "openmodelica", or "auto")
        dymolaConfig: Dymola-specific configuration
        openModelicaConfig: OpenModelica-specific configuration

    Returns:
        One CompilationResult per request, in the same order
    """
    compiler = getCompiler(backend, dymolaConfig, openModelicaConfig)
    if isinstance(compiler, DymolaCompiler):
        jobs = [
            (request.createModel(), Path(request.outdir), request.createConfig())
            for request in requests
        ]
        return compiler.compileMany(jobs)

    results: list[CompilationResult] = []
    for request in requests:
        results.append(
            compiler.compile(
                request.createModel(),
                Path(request.outdir),
                request.createConfig(),
            )
        )
    return results


# =============================================================================
# Legacy API (deprecated, for backward compatibility)
# =============================================================================


def get_compiler(
    backend: Backend = "auto",
    dymola_config: Optional[DymolaConfig] = None,
    openmodelica_config: Optional[OpenModelicaConfig] = None,
) -> FMUCompiler:
    """Get an FMU compiler instance.

    .. deprecated::
        Use :func:`getCompiler` instead.
    """
    warnings.warn(
        "get_compiler() is deprecated, use getCompiler() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return getCompiler(backend, dymola_config, openmodelica_config)


def mo2fmu_new(
    mo: str | Path,
    outdir: str | Path,
    backend: Backend = "auto",
    fmumodelname: Optional[str] = None,
    load: Optional[list[str]] = None,
    flags: Optional[list[str]] = None,
    fmi_type: str = "all",
    fmi_version: str = "2",
    verbose: bool = False,
    force: bool = False,
    dymola_config: Optional[DymolaConfig] = None,
    openmodelica_config: Optional[OpenModelicaConfig] = None,
) -> CompilationResult:
    """Convert a Modelica model to FMU.

    .. deprecated::
        Use :func:`compileFmu` instead.
    """
    warnings.warn(
        "mo2fmu_new() is deprecated, use compileFmu() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return compileFmu(
        mo=mo,
        outdir=outdir,
        backend=backend,
        fmuModelName=fmumodelname,
        load=load,
        flags=flags,
        fmiType=fmi_type,
        fmiVersion=fmi_version,
        verbose=verbose,
        force=force,
        dymolaConfig=dymola_config,
        openModelicaConfig=openmodelica_config,
    )


def mo2fmu(
    mo: str,
    outdir: str,
    fmumodelname: Optional[str],
    load: Optional[tuple[str, ...]],
    flags: Optional[tuple[str, ...]],
    type: str,
    version: str,
    dymola_root: str,
    dymolapath: str,
    dymolawhl: str,
    verbose: bool,
    force: bool,
    backend: str = "dymola",
) -> bool:
    """Convert a .mo file into a .fmu.

    .. deprecated::
        Use :func:`compileFmu` instead. This function is maintained for
        backward compatibility only.

    Args:
        mo: Path to the Modelica .mo file to convert
        outdir: Output directory for the generated FMU
        fmumodelname: Custom name for the FMU model (defaults to .mo file stem)
        load: Tuple of Modelica packages to load
        flags: Tuple of Dymola flags for FMU translation
        type: FMI type (cs, me, all, or csSolver)
        version: FMI version
        dymola_root: Path to Dymola root directory
        dymolapath: Path to Dymola executable
        dymolawhl: Path to Dymola wheel file (relative to dymola root)
        verbose: Enable verbose logging
        force: Force overwrite of existing FMU
        backend: Compiler backend ("dymola" or "openmodelica")

    Returns:
        True if conversion was successful, False otherwise
    """
    warnings.warn(
        "mo2fmu() is deprecated, use compileFmu() instead",
        DeprecationWarning,
        stacklevel=2,
    )

    # Build config for Dymola
    dymolaConfig = DymolaConfig(
        root=dymola_root,
        executable=dymolapath,
        wheel_path=dymolawhl,
    )

    # Use the new unified API
    result = compileFmu(
        mo=mo,
        outdir=outdir,
        backend=backend,  # type: ignore[arg-type]
        fmuModelName=fmumodelname,
        load=list(load) if load else None,
        flags=list(flags) if flags else None,
        fmiType=type,
        fmiVersion=version,
        verbose=verbose,
        force=force,
        dymolaConfig=dymolaConfig,
    )

    return result.success


# =============================================================================
# CLI with Click Group
# =============================================================================


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("-v", "--version", is_flag=True, help="Show version information.")
def mo2fmuCLI(ctx: click.Context, version: bool) -> None:
    """mo2fmu - Convert Modelica models to Functional Mock-up Units (FMUs).

    Use 'mo2fmu compile' to generate FMUs or 'mo2fmu check' to verify compilers.

    Examples:
        mo2fmu compile model.mo ./output

        mo2fmu compile -v --force model.mo ./output

        mo2fmu check

        mo2fmu check --dymola /opt/dymola-2025x
    """
    if version:
        click.echo(f"mo2fmu version {get_version('feelpp-mo2fmu')}")
        return

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@mo2fmuCLI.command("compile")
@click.argument("mo", type=click.Path(exists=True))
@click.argument("outdir", type=click.Path())
@click.option(
    "--name",
    default=None,
    type=str,
    help="Custom name for the FMU (default: .mo file stem).",
)
@click.option(
    "--load",
    "-l",
    default=None,
    multiple=True,
    help="Load one or more Modelica packages.",
)
@click.option(
    "--flags",
    default=None,
    multiple=True,
    help="Compiler-specific flags for FMU translation.",
)
@click.option(
    "--type",
    "-t",
    "fmiType",
    default="all",
    type=click.Choice(["all", "cs", "me", "csSolver"]),
    help="FMI type: cs (Co-Simulation), me (Model Exchange), all, or csSolver.",
)
@click.option(
    "--fmi-version",
    default="2",
    type=click.Choice(["1", "2", "3"]),
    help="FMI version. FMI 3.0 requires Dymola 2024+ or OpenModelica 1.21+.",
)
@click.option(
    "--backend",
    "-b",
    default="auto",
    type=click.Choice(["dymola", "openmodelica", "auto"]),
    help="Modelica compiler backend (default: auto-detect).",
)
@click.option(
    "--dymola",
    default="/opt/dymola-2025xRefresh1-x86_64/",
    type=click.Path(),
    envvar="DYMOLA_ROOT",
    help="Path to Dymola root directory.",
)
@click.option(
    "--dymola-exec",
    default="/usr/local/bin/dymola",
    type=click.Path(),
    envvar="DYMOLA_EXECUTABLE",
    help="Path to Dymola executable.",
)
@click.option(
    "--dymola-whl",
    default="Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl",
    type=click.Path(),
    envvar="DYMOLA_WHL",
    help="Path to Dymola wheel file (relative to Dymola root).",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.option("-f", "--force", is_flag=True, help="Overwrite existing FMU.")
def compileCmd(
    mo: str,
    outdir: str,
    name: Optional[str],
    load: tuple[str, ...],
    flags: tuple[str, ...],
    fmiType: str,
    fmi_version: str,
    backend: str,
    dymola: str,
    dymola_exec: str,
    dymola_whl: str,
    verbose: bool,
    force: bool,
) -> None:
    """Compile a Modelica model to FMU.

    MO: Path to the Modelica model file (.mo)

    OUTDIR: Output directory for the generated FMU

    Examples:
        mo2fmu compile model.mo ./output

        mo2fmu compile -v --force --fmi-version 3 model.mo ./output

        mo2fmu compile --backend openmodelica model.mo ./output

        mo2fmu compile --load package.mo model.mo ./output
    """
    # Build Dymola config
    dymolaConfig = DymolaConfig(
        root=dymola,
        executable=dymola_exec,
        wheel_path=dymola_whl,
    )

    try:
        result = compileFmu(
            mo=mo,
            outdir=outdir,
            backend=backend,  # type: ignore[arg-type]
            fmuModelName=name,
            load=list(load) if load else None,
            flags=list(flags) if flags else None,
            fmiType=fmiType,
            fmiVersion=fmi_version,
            verbose=verbose,
            force=force,
            dymolaConfig=dymolaConfig,
        )

        if result.success:
            click.echo(f"FMU created: {result.fmu_path}")
        else:
            click.echo(f"Error: {result.error_message}", err=True)
            if result.log:
                click.echo(f"Log:\n{result.log}", err=True)
            raise SystemExit(1) from None

    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e


@mo2fmuCLI.command("check")
@click.option(
    "--dymola",
    default="/opt/dymola-2025xRefresh1-x86_64/",
    type=click.Path(),
    envvar="DYMOLA_ROOT",
    help="Path to Dymola root directory.",
)
@click.option(
    "--dymola-exec",
    default="/usr/local/bin/dymola",
    type=click.Path(),
    envvar="DYMOLA_EXECUTABLE",
    help="Path to Dymola executable.",
)
@click.option(
    "--dymola-whl",
    default="Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl",
    type=click.Path(),
    envvar="DYMOLA_WHL",
    help="Path to Dymola wheel file (relative to Dymola root).",
)
@click.option("--json", "asJson", is_flag=True, help="Output results as JSON.")
def checkCmd(
    dymola: str,
    dymola_exec: str,
    dymola_whl: str,
    asJson: bool,
) -> None:
    """Check availability of Modelica compilers and their FMI support.

    This command checks for Dymola and OpenModelica installations
    and reports their versions and supported FMI versions.

    Examples:
        mo2fmu check

        mo2fmu check --json

        mo2fmu check --dymola /opt/dymola-2024x
    """
    dymolaConfig = DymolaConfig(
        root=dymola,
        executable=dymola_exec,
        wheel_path=dymola_whl,
    )

    results = checkCompilers(dymolaConfig=dymolaConfig)

    if asJson:
        import json

        click.echo(json.dumps(results, indent=2))
        return

    click.echo("=" * 60)
    click.echo("mo2fmu Compiler Availability Check")
    click.echo("=" * 60)

    # Dymola
    click.echo("\nDymola:")
    if results["dymola"]["available"]:
        click.echo("  Status:      Available")
        click.echo(f"  Version:     {results['dymola']['version'] or 'Unknown'}")
        dymolaFmiSupport = results["dymola"]["fmiSupport"]
        if isinstance(dymolaFmiSupport, list):
            fmiVersions = ", ".join(dymolaFmiSupport)
            click.echo(f"  FMI Support: {fmiVersions}")
    else:
        click.echo("  Status:      Not available")
        click.echo("  Hint:        Set DYMOLA_ROOT environment variable or use --dymola option")

    # OpenModelica
    click.echo("\nOpenModelica:")
    if results["openmodelica"]["available"]:
        click.echo("  Status:      Available")
        click.echo(f"  Version:     {results['openmodelica']['version'] or 'Unknown'}")
        omcFmiSupport = results["openmodelica"]["fmiSupport"]
        if isinstance(omcFmiSupport, list):
            fmiVersions = ", ".join(omcFmiSupport)
            click.echo(f"  FMI Support: {fmiVersions}")
    else:
        click.echo("  Status:      Not available")
        click.echo("  Hint:        Install OpenModelica and OMPython (pip install OMPython)")

    click.echo("\n" + "=" * 60)

    # Summary
    availableCount = sum(1 for c in results.values() if c["available"])
    if availableCount == 0:
        click.echo("Warning: No compilers available!")
        raise SystemExit(1)
    if availableCount == 1:
        compilerName = "Dymola" if results["dymola"]["available"] else "OpenModelica"
        click.echo(f"Summary: {compilerName} is available for FMU generation.")
    else:
        click.echo("Summary: Both compilers are available for FMU generation.")


# =============================================================================
# Legacy CLI entry point (for backward compatibility with old command style)
# =============================================================================


@click.command("mo2fmu-legacy")
@click.argument("mo", type=str, nargs=1, required=False)
@click.argument("outdir", type=click.Path(), nargs=1, required=False)
@click.option("--check", is_flag=True, help="Check compiler availability.")
@click.option("--fmumodelname", default=None, type=str, help="Custom FMU name.")
@click.option("--load", default=None, multiple=True, help="Load Modelica packages.")
@click.option("--flags", default=None, multiple=True, help="Compiler flags.")
@click.option("--type", default="all", type=click.Choice(["all", "cs", "me", "csSolver"]))
@click.option("--version", "fmiVersion", default="2", type=click.Choice(["1", "2", "3"]))
@click.option("--backend", default="auto", type=click.Choice(["dymola", "openmodelica", "auto"]))
@click.option("--dymola", default="/opt/dymola-2025xRefresh1-x86_64/", type=click.Path())
@click.option("--dymolapath", default="/usr/local/bin/dymola", type=click.Path())
@click.option(
    "--dymolawhl", default="Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl"
)
@click.option("-v", "--verbose", is_flag=True)
@click.option("-f", "--force", is_flag=True)
def mo2fmuLegacyCLI(
    mo: Optional[str],
    outdir: Optional[str],
    check: bool,
    fmumodelname: Optional[str],
    load: tuple[str, ...],
    flags: tuple[str, ...],
    type: str,
    fmiVersion: str,
    backend: str,
    dymola: str,
    dymolapath: str,
    dymolawhl: str,
    verbose: bool,
    force: bool,
) -> None:
    """Legacy CLI for backward compatibility.

    .. deprecated::
        Use 'mo2fmu compile' or 'mo2fmu check' instead.
    """
    warnings.warn(
        "Legacy CLI style is deprecated. Use 'mo2fmu compile' or 'mo2fmu check' instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    if check:
        # Invoke check command
        ctx = click.Context(checkCmd)
        ctx.invoke(
            checkCmd, dymola=dymola, dymola_exec=dymolapath, dymola_whl=dymolawhl, asJson=False
        )
        return

    if not mo or not outdir:
        click.echo("Error: MO and OUTDIR arguments required.", err=True)
        raise SystemExit(1)

    # Invoke compile command
    ctx = click.Context(compileCmd)
    ctx.invoke(
        compileCmd,
        mo=mo,
        outdir=outdir,
        name=fmumodelname,
        load=load,
        flags=flags,
        fmiType=type,
        fmi_version=fmiVersion,
        backend=backend,
        dymola=dymola,
        dymola_exec=dymolapath,
        dymola_whl=dymolawhl,
        verbose=verbose,
        force=force,
    )
