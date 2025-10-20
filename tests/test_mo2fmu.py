from __future__ import annotations

import os
from pathlib import Path

import pytest
from xvfbwrapper import Xvfb

from feelpp.mo2fmu.mo2fmu import mo2fmu


def checkFmuFileExist(fmuPath, outdir):
    """Check if FMU file exists.

    Parameters
    ----------
    fmuPath: path
        path of the fmu file
    outdir: path
        path of the output file directory.
    """
    assert fmuPath.exists(), f"FMU file {fmuPath} was not created."
    print(f"FMU file created at: {fmuPath}")


def checkFmuValidity(fmuPath, fmuModel, dymolapath):
    """Check that the fmu model has the same number of unknowns and equations.

    Also verifies that it can be simulated.

    Parameters
    ----------
    fmuPath: path
        path of the fmu file
    fmuModel: str
        name of the fmu model in Dymola
    dymolapath: path
        path of the dymola application
    """
    # launch a display server (needed to launch Dymola)
    vdisplay = Xvfb()
    vdisplay.start()

    # launch Dymola
    from dymola.dymola_interface import DymolaInterface

    dymApp = DymolaInterface(dymolapath=dymolapath, showwindow=False)

    # import the FMU
    importedFMU = dymApp.importFMU(str(fmuPath))
    assert importedFMU, f"FMU file {fmuPath} couldn't be imported"

    # check the model and simulate it
    result = dymApp.checkModel(problem=fmuModel, simulate=True)
    if result is False:
        log = dymApp.getLastErrorLog()
        print(log)

    # close Dymola and display server
    dymApp.close()
    vdisplay.stop()

    assert result, f"FMU file {fmuPath} isn't valid, see the log above."


@pytest.mark.parametrize(
    "modelPath, outdirPath",
    [(Path("src/cases/ode_exp.mo"), Path("src")), (Path("src/cases/ode_sin.mo"), Path("src"))],
)
def test_pathExists(modelPath, outdirPath):
    """Test if path of the modelica model and the output directory exist.

    Parameters
    ----------
    modelPath: path
        path of modelica model to convert into fmu
    outdirPath: path
        path of the output directory to find fmu file after conversion
    """
    assert modelPath.exists()
    assert outdirPath.exists()
    print(modelPath)


# Check if Dymola is available
# Configure via environment variables:
# - DYMOLA_ROOT: Path to Dymola installation (default: /opt/dymola-2025xRefresh1-x86_64/)
# - DYMOLA_EXECUTABLE: Path to Dymola binary (default: /usr/local/bin/dymola)
# - DYMOLA_WHL: Relative path to Python wheel (default: Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl)
DYMOLA_PATH = os.getenv("DYMOLA_ROOT", "/opt/dymola-2025xRefresh1-x86_64/")
DYMOLA_EXECUTABLE = os.getenv("DYMOLA_EXECUTABLE", "/usr/local/bin/dymola")
DYMOLA_WHL = os.getenv(
    "DYMOLA_WHL", "Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl"
)
HAS_DYMOLA = (Path(DYMOLA_PATH) / DYMOLA_WHL).is_file()


@pytest.mark.skipif(not HAS_DYMOLA, reason="Dymola not available in test environment")
@pytest.mark.parametrize(
    "mo, outdir", [("src/cases/ode_exp.mo", "src/"), ("src/cases/ode_sin.mo", "src/")]
)
def test_basicConversion(mo, outdir):
    """Test mo2fmu python script using mo file.

    Parameters
    ----------
    mo: path
        path of the modelica file to convert to FMU.
    outdir: path
        path of the output file directory.
    """
    fmumodelname = None
    load = None
    flags = None
    type = "all"
    version = "2"
    verbose = True
    force = True

    baseName = Path(mo).stem
    fmuPath = Path(outdir) / f"{baseName}.fmu"
    fmuDymola = f"{baseName}_fmu"

    # call mo2fmu converter
    mo2fmu(
        mo,
        outdir,
        fmumodelname,
        load,
        flags,
        type,
        version,
        DYMOLA_PATH,
        DYMOLA_EXECUTABLE,
        DYMOLA_WHL,
        verbose,
        force,
    )

    # check if the FMU file is created
    checkFmuFileExist(fmuPath, outdir)

    # check model validity of the fmu
    checkFmuValidity(fmuPath, fmuDymola, DYMOLA_EXECUTABLE)
