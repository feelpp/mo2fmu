import platform
import sys
import os
from pathlib import Path, PurePosixPath
import shutil
from xvfbwrapper import Xvfb
import click
import spdlog as spd


def mo2fmu(mo, outdir, fmumodelname, load, flags, type, version, dymola, dymolapath, dymolawhl, verbose, force):
    """
    mo2fmu converts a .mo file into a .fmu

    mo2fmu -v foo.mo .
    """
    logger = spd.ConsoleLogger('Logger', False, True, True)
    has_dymola = False

    # Prevent writing FMU into the same directory as cwd
    if Path(outdir) == Path(os.getcwd()):
        logger.error('the destination directory should be different from {}'.format(os.getcwd()))
        return False

    # Attempt to load Dymola’s Python interface
    try:
        sys.path.append(str(Path(dymola) / Path(dymolawhl)))
        logger.info("add {} to sys path".format(Path(dymola) / Path(dymolawhl)))
        if not (Path(dymola) / Path(dymolawhl)).is_file():
            logger.error("dymola whl {} does not exist".format(Path(dymola) / Path(dymolawhl)))
        import dymola
        from dymola.dymola_interface import DymolaInterface
        from dymola.dymola_exception import DymolaException
        has_dymola = True
        logger.info("dymola is available in {}/{}".format(dymola, dymolawhl))
    except ImportError:
        logger.info("dymola module is not available, has_dymola: {}".format(has_dymola))
    if not has_dymola:
        logger.error("dymola is not available, mo2fmu failed")
        return False

    # Start a virtual framebuffer (for headless Dymola)
    vdisplay = Xvfb()
    vdisplay.start()

    osString = platform.system()
    isWindows = osString.startswith("Win")

    dymola = None
    try:
        # Determine the FMU model name (default: .mo file stem)
        fmumodelname = Path(fmumodelname if fmumodelname else mo).stem
        if verbose:
            logger.info("convert {} to {}.fmu".format(mo, fmumodelname))

        # If an FMU already exists in outdir
        target_fmu = Path(outdir) / f"{fmumodelname}.fmu"
        if target_fmu.is_file() and force:
            logger.warn(f"{fmumodelname}.fmu exists in {outdir}, will overwrite it")
        elif target_fmu.is_file():
            logger.warn(f"{fmumodelname}.fmu exists in {outdir}; use `--force` to overwrite.")
            return False

        # Create outdir if it doesn’t exist
        if not Path(outdir).is_dir():
            os.mkdir(outdir)

        # Instantiate Dymola interface
        dymola = DymolaInterface(dymolapath=dymolapath, showwindow=False)

        # **1) Disable any 32-bit build first and force 64-bit-only compilation **
        dymola.ExecuteCommand("Advanced.CompileWith64=2;")
        # **2) Enable code export so FMU contains sources or compiled binaries and no longer requires a license to run **
        dymola.ExecuteCommand("Advanced.EnableCodeExport=true;")
        # **3) Turn on full compiler optimizations (instead of the default -O1) :contentReference[oaicite:0]{index=0}
        dymola.ExecuteCommand("Advanced.Define.GlobalOptimizations=2;")

        # Compute the fully qualified model name (package + file stem)
        packageName = ""
        with open(mo, "r") as f:
            lines = f.readlines()
        for line in lines:
            if line.strip().startswith('within '):
                packageName = line.split(' ')[1][:-2]
        if packageName:
            moModel = f"{packageName}.{Path(mo).stem}"
        else:
            moModel = Path(mo).stem

        # Load any additional packages
        if load:
            for package in load:
                if verbose:
                    logger.info("load modelica package {}".format(package))
                dymola.openModel(package, changeDirectory=False)

        # Apply any Dymola flags
        if flags:
            for flag in flags:
                if verbose:
                    logger.info("Flag {}".format(flag))
                dymola.ExecuteCommand(flag)

        # Open the .mo file
        dymola.openModel(mo, changeDirectory=False)

        # Ensure Dymola’s working directory matches Python’s cwd
        cwd_posix = str(Path.cwd().as_posix())
        dymola.ExecuteCommand(f'cd("{cwd_posix}");')
        logger.info(f"Dymola working directory = {cwd_posix}")

        # Request FMU translation (now only 64-bit since 32-bit is disabled)
        result = dymola.translateModelFMU(
            moModel, modelName=fmumodelname, fmiVersion="2", fmiType=type
        )

        if not result:
            log = dymola.getLastErrorLog()
            licInfo = dymola.DymolaLicenseInfo()
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
            logger.warn(f"{target_fmu.name} already exists in {outdir}; use --force to overwrite")
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
        if dymola is not None:
            dymola.close()
        vdisplay.stop()
        spd.drop('Logger')


@click.command()
@click.argument('mo', type=str, nargs=1)
@click.argument('outdir', type=click.Path(), nargs=1)
@click.option('--fmumodelname', default=None, type=str,
              help="change the model name of the FMU (default: .mo file stem)")
@click.option('--load', default=None, multiple=True,
              help='load one or more Modelica packages.')
@click.option('--flags', default=None, multiple=True,
              help='one or more Dymola flags for FMU translation.')
@click.option('--type', default="all", type=click.Choice(['all', 'cs', 'me', 'csSolver']),
              help='the FMI type: cs, me, all, or csSolver.')
@click.option('--version', default="2", help='the FMI version.')
@click.option('--dymola', default="/opt/dymola-2025xRefresh1-x86_64/", type=click.Path(),
              help='path to Dymola root.')
@click.option('--dymolapath', default="/usr/local/bin/dymola", type=click.Path(),
              help='path to Dymola executable.')
@click.option('--dymolawhl', default="Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl", type=click.Path(),
              help='path to Dymola whl file, relative to Dymola root.')
@click.option('-v', '--verbose', is_flag=True, help='verbose mode.')
@click.option('-f', '--force', is_flag=True, help='force FMU generation even if file exists.')
def mo2fmuCLI(mo, outdir, fmumodelname, load, flags, type, version, dymola, dymolapath, dymolawhl, verbose, force):
    mo2fmu(mo, outdir, fmumodelname, load, flags, type, version, dymola, dymolapath, dymolawhl, verbose, force)
