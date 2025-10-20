"""mo2fmu - Convert Modelica models to Functional Mock-up Units (FMUs)."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Optional

import click
import spdlog as spd
from xvfbwrapper import Xvfb


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
) -> bool:
    """Convert a .mo file into a .fmu.

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

    Returns:
        True if conversion was successful, False otherwise

    Example:
        >>> mo2fmu("model.mo", "./output", None, None, None, "cs", "2",
        ...        "/opt/dymola", "/usr/local/bin/dymola", "dymola.whl", True, False)
    """
    # Create logger with unique name based on file being processed
    import uuid

    logger_name = f"mo2fmu_{uuid.uuid4().hex[:8]}"
    logger = spd.ConsoleLogger(logger_name, False, True, True)
    has_dymola = False

    # Prevent writing FMU into the same directory as cwd
    if Path(outdir) == Path(os.getcwd()):
        logger.error(f"the destination directory should be different from {os.getcwd()}")
        return False

    # Attempt to load Dymola's Python interface
    try:
        sys.path.append(str(Path(dymola_root) / Path(dymolawhl)))
        logger.info(f"add {Path(dymola_root) / Path(dymolawhl)} to sys path")
        if not (Path(dymola_root) / Path(dymolawhl)).is_file():
            logger.error(f"dymola whl {Path(dymola_root) / Path(dymolawhl)} does not exist")
        import dymola  # noqa: F401
        from dymola.dymola_exception import DymolaException
        from dymola.dymola_interface import DymolaInterface

        has_dymola = True
        logger.info(f"dymola is available in {dymola_root}/{dymolawhl}")
    except ImportError:
        logger.info(f"dymola module is not available, has_dymola: {has_dymola}")
    if not has_dymola:
        logger.error("dymola is not available, mo2fmu failed")
        return False

    # Start a virtual framebuffer (for headless Dymola)
    vdisplay = Xvfb()
    vdisplay.start()

    osString = platform.system()
    isWindows = osString.startswith("Win")  # noqa: F841

    dymola_interface = None
    try:
        # Determine the FMU model name (default: .mo file stem)
        fmumodelname = Path(fmumodelname if fmumodelname else mo).stem
        if verbose:
            logger.info(f"convert {mo} to {fmumodelname}.fmu")

        # If an FMU already exists in outdir
        target_fmu = Path(outdir) / f"{fmumodelname}.fmu"
        if target_fmu.is_file() and force:
            logger.warn(f"{fmumodelname}.fmu exists in {outdir}, will overwrite it")
        elif target_fmu.is_file():
            logger.warn(f"{fmumodelname}.fmu exists in {outdir}; use `--force` to overwrite.")
            return False

        # Create outdir if it doesn't exist
        if not Path(outdir).is_dir():
            Path(outdir).mkdir(parents=True, exist_ok=True)

        # Instantiate Dymola interface
        dymola_interface = DymolaInterface(dymolapath=dymolapath, showwindow=False)

        # **1) Disable any 32-bit build first and force 64-bit-only compilation **
        dymola_interface.ExecuteCommand("Advanced.CompileWith64=2;")
        # **2) Enable code export so FMU contains sources or compiled binaries **
        # and no longer requires a license to run
        dymola_interface.ExecuteCommand("Advanced.EnableCodeExport=true;")
        # **3) Turn on full compiler optimizations (instead of the default -O1)
        dymola_interface.ExecuteCommand("Advanced.Define.GlobalOptimizations=2;")

        # Compute the fully qualified model name (package + file stem)
        packageName = ""
        with open(mo) as f:
            lines = f.readlines()
        for line in lines:
            if line.strip().startswith("within "):
                packageName = line.split(" ")[1][:-2]
        if packageName:
            moModel = f"{packageName}.{Path(mo).stem}"
        else:
            moModel = Path(mo).stem

        # Load any additional packages
        if load:
            for package in load:
                if verbose:
                    logger.info(f"load modelica package {package}")
                dymola_interface.openModel(package, changeDirectory=False)

        # Apply any Dymola flags
        if flags:
            for flag in flags:
                if verbose:
                    logger.info(f"Flag {flag}")
                dymola_interface.ExecuteCommand(flag)

        # Open the .mo file
        dymola_interface.openModel(mo, changeDirectory=False)

        # Ensure Dymola's working directory matches Python's cwd
        cwd_posix = str(Path.cwd().as_posix())
        dymola_interface.ExecuteCommand(f'cd("{cwd_posix}");')
        logger.info(f"Dymola working directory = {cwd_posix}")

        # Request FMU translation (now only 64-bit since 32-bit is disabled)
        result = dymola_interface.translateModelFMU(
            moModel, modelName=fmumodelname, fmiVersion="2", fmiType=type
        )

        if not result:
            log = dymola_interface.getLastErrorLog()
            licInfo = dymola_interface.DymolaLicenseInfo()
            logger.error("translateModelFMU returned False. Dymola log:")
            logger.error(log)
            logger.error("Dymola License Information:")
            logger.error(licInfo)
            return False

        # Verify that the FMU file actually appeared
        expected_fmu = Path.cwd() / f"{fmumodelname}.fmu"
        if not expected_fmu.is_file():
            logger.error(f"Expected FMU '{expected_fmu.name}' not found in {Path.cwd()}")
            logger.error(f"Directory listing (*.fmu): {list(Path.cwd().glob('*.fmu'))}")
            return False

        # If an old FMU exists in outdir and --force was given, remove it
        if target_fmu.is_file() and force:
            target_fmu.unlink()
        elif target_fmu.is_file():
            logger.warning(
                f"{target_fmu.name} already exists in {outdir}; use --force to overwrite"
            )
            return False

        # Move the FMU to the output directory
        dest = shutil.move(str(expected_fmu), str(Path(outdir)))
        logger.info(f"translateModelFMU {Path(mo).stem} → {dest}")

        if verbose:
            logger.info(f"{fmumodelname}.fmu successfully generated in {outdir}")

        return True

    except DymolaException as ex:
        logger.error(str(ex))
        return False

    finally:
        # Clean up: close Dymola and stop the virtual framebuffer
        if dymola_interface is not None:
            dymola_interface.close()
        vdisplay.stop()
        spd.drop("Logger")


@click.command()
@click.argument("mo", type=str, nargs=1)
@click.argument("outdir", type=click.Path(), nargs=1)
@click.option(
    "--fmumodelname",
    default=None,
    type=str,
    help="change the model name of the FMU (default: .mo file stem)",
)
@click.option("--load", default=None, multiple=True, help="load one or more Modelica packages.")
@click.option(
    "--flags",
    default=None,
    multiple=True,
    help="one or more Dymola flags for FMU translation.",
)
@click.option(
    "--type",
    default="all",
    type=click.Choice(["all", "cs", "me", "csSolver"]),
    help="the FMI type: cs, me, all, or csSolver.",
)
@click.option("--version", default="2", help="the FMI version.")
@click.option(
    "--dymola",
    default="/opt/dymola-2025xRefresh1-x86_64/",
    type=click.Path(),
    help="path to Dymola root.",
)
@click.option(
    "--dymolapath",
    default="/usr/local/bin/dymola",
    type=click.Path(),
    help="path to Dymola executable.",
)
@click.option(
    "--dymolawhl",
    default="Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl",
    type=click.Path(),
    help="path to Dymola whl file, relative to Dymola root.",
)
@click.option("-v", "--verbose", is_flag=True, help="verbose mode.")
@click.option("-f", "--force", is_flag=True, help="force FMU generation even if file exists.")
def mo2fmuCLI(
    mo: str,
    outdir: str,
    fmumodelname: Optional[str],
    load: Optional[tuple[str, ...]],
    flags: Optional[tuple[str, ...]],
    type: str,
    version: str,
    dymola: str,
    dymolapath: str,
    dymolawhl: str,
    verbose: bool,
    force: bool,
) -> None:
    """Convert Modelica (.mo) files to Functional Mock-up Units (.fmu).

    MO: Path to the Modelica model file (.mo)
    OUTDIR: Output directory for the generated FMU

    Examples:
        mo2fmu model.mo ./output

        mo2fmu -v --force model.mo ./output

        mo2fmu --load package.mo model.mo ./output
    """
    mo2fmu(
        mo,
        outdir,
        fmumodelname,
        load,
        flags,
        type,
        version,
        dymola,  # CLI parameter name stays as 'dymola' for backward compatibility
        dymolapath,
        dymolawhl,
        verbose,
        force,
    )
