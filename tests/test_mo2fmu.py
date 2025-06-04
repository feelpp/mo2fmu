import pytest
from feelpp.mo2fmu.mo2fmu import mo2fmu
from pathlib import Path
from xvfbwrapper import Xvfb


@pytest.mark.parametrize("modelPath, outdirPath", [
    (Path("src/cases/ode_exp.mo"), Path("src"))
])
def test_pathExists(modelPath, outdirPath):
    assert modelPath.exists()
    assert outdirPath.exists()
    print(modelPath)


@pytest.mark.parametrize("mo, outdir", [
    ("src/cases/ode_exp.mo", "src/"),
])
def test_basicConversion(mo, outdir):
    """
    Test mo2fmu python script using mo file.

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
    dymola = "/opt/dymola-2023-x86_64/"
    dymolapath = "/usr/local/bin/dymola-2023-x86_64"
    dymolaegg = "Modelica/Library/python_interface/dymola.egg"
    verbose = True
    force = True

    mo2fmu(mo, outdir, fmumodelname, load, flags, type, version, dymola, dymolapath, dymolaegg, verbose, force)

    # check if the FMU file is created
    fmu_path = Path(outdir) / "ode_exp.fmu"
    assert fmu_path.exists(), f"FMU file {fmu_path} was not created."
    print(f"FMU file created at: {fmu_path}")

    # launch a display server (needed to launch Dymola)
    vdisplay = Xvfb()
    vdisplay.start()

    # check model validity of the fmu
    from dymola.dymola_interface import DymolaInterface
    dymApp = DymolaInterface(dymolapath=dymolapath, showwindow=False)
    importedFMU = dymApp.importFMU(str(fmu_path))
    print(importedFMU)
    result = dymApp.checkModel(problem="ode_exp_fmu", simulate=False)
    if result is False:
        log = dymApp.getLastErrorLog()
        print(log)
    dymApp.close()
    vdisplay.stop()
    assert result, f"FMU file {fmu_path} isn't valid, see the log: {log}"