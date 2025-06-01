import pytest
from feelpp.mo2fmu import mo2fmu
from pathlib import Path


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