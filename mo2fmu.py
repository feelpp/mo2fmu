import platform
import sys
import os
from pathlib import Path, PurePosixPath
from xvfbwrapper import Xvfb
import click
import spdlog as spd


@click.command()
@click.argument('mo', type=str, nargs=1)
@click.option('--fmumodelname', default=None, type=str, help="change the modelname of the fmu, by default use the modelical file stem")
@click.option('--type', default="all",  type=click.Choice(['all', 'cs', "me", "csSolver"]), help='The fmi types cs, me, all.')
@click.option('--version', default="2", help='The fmi version.')
@click.option('--dymola', default="/opt/dymola-2021-x86_64/", type=click.Path(), help='path to dymola executable.')
@click.option('--dymolapath', default="/usr/local/bin/dymola-2021-x86_64", type=click.Path(), help='path to dymola executable.')
@click.option('--dymolaegg', default="Modelica/Library/python_interface/dymola.egg", type=click.Path(), help='path to dymola egg file relative to dymola root path.')
@click.option('-v', '--verbose', is_flag=True, help='verbose mode.')
@click.option('-f', '--force', is_flag=True, help='force fmu generation even if file exists.')
def mo2fmu(mo, fmumodelname, type, version, dymola, dymolapath, dymolaegg, verbose, force):
    """
    convert a .mo file into a .fmu
    """
    logger = spd.ConsoleLogger('Logger', False, True, True)
    # Changement du PYTHONPATH
    try:
        sys.path.append(Path(dymola) / Path(dymolaegg))
        import dymola
        from dymola.dymola_interface import DymolaInterface
        from dymola.dymola_exception import DymolaException
        has_dymola = True
    except ImportError as e:
        logger.info(
            'dymola module is not available, has_dymola: {}'.format(has_dymola))
        pass  # module doesn't exist, deal with it.
    if not has_dymola:
        logger.error("dymola is not available, mo2fmu failed")
        return False
    vdisplay = Xvfb()
    vdisplay.start()
    osString = platform.system()
    isWindows = osString.startswith("Win")

    dymola = None
    try:
        fmumodelname = Path(fmumodelname if fmumodelname else mo).stem
        if verbose:
            logger.info("convert {} to {}.fmu".format(mo, fmumodelname))

        if Path(fmumodelname+'.fmu').is_file() and force:
            logger.warn(
                "{}.fmu exists, dymola will overwrite it".format(fmumodelname))
        elif Path(fmumodelname+'.fmu').is_file():
            logger.warn(
                "{}.fmu exists, dymola will not overwrite it, use `--force` or `-f` to overwrite it.".format(fmumodelname))
            return

        # Instantiate the Dymola interface and start Dymola
        dymola = DymolaInterface(dymolapath=dymolapath, showwindow=False)
        dymola.openModel(mo, changeDirectory=False)
        result = dymola.translateModelFMU(
            Path(mo).stem, modelName=fmumodelname, fmiVersion="2", fmiType=type)
        if not result:
            log = dymola.getLastErrorLog()
            logger.error("Simulation failed. Below is the translation log.")
            logger.info(log)
            return
        if verbose:
            logger.info("{} file successfully generated".format(fmumodelname))
        assert(Path(fmumodelname+'.fmu').is_file())
    except DymolaException as ex:
        logger.error(str(ex))
        vdisplay.stop()
    finally:
        if dymola is not None:
            dymola.close()
            dymola = None
            vdisplay.stop()
    # return modelpath+fmufilname
