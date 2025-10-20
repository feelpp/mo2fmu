# Feel++ mo2fmu converter

Modelica to FMU converter based on dymola

## Installation

```console
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml --extra dev --extra test
uv pip install .
```

## Usage in command line

```console
$ mo2fmu --help
Usage: mo2fmu [OPTIONS] MO OUTDIR

Options:
  --fmumodelname TEXT          change the model name of the FMU (default: .mo
                               file stem)
  --load TEXT                  load one or more Modelica packages.
  --flags TEXT                 one or more Dymola flags for FMU translation.
  --type [all|cs|me|csSolver]  the FMI type: cs, me, all, or csSolver.
  --version TEXT               the FMI version.
  --dymola PATH                path to Dymola root.
  --dymolapath PATH            path to Dymola executable.
  --dymolawhl PATH             path to Dymola whl file, relative to Dymola
                               root.
  -v, --verbose                verbose mode.
  -f, --force                  force FMU generation even if file exists.
  --help                       Show this message and exit.----
```

## Usage in Python

Here is an example of how to use the `mo2fmu` function in Python that would convert a Modelica file to an FMU:

```python
from feelpp.mo2fmu import mo2fmu
mo2fmu(
    mo_file="path/to/model.mo",
    outdir="path/to/output/dir",
    fmumodelname="MyFMUModel",
    load=["Modelica", "SomePackage"],
    flags=["-d=initialization"],
    fmi_type="cs",
    fmi_version="2.0",
    dymola_root="/path/to/dymola/root",
    dymola_executable="/path/to/dymola/executable",
    dymola_whl="/path/to/dymola.whl",
    verbose=True,
    force=False
)
```

## Continuous Integration

Our GitHub Actions workflow (`.github/workflows/ci.yml`) includes:

* build_wheel: Python wheel compilation and artifact upload.
* docs: Builds the Antora site, deploys to GitHub Pages on master.
* deliver: Docker image build & push to GHCR.
* release: On tags vX.Y.Z, publishes binaries, wheels, datasets, and creates a GitHub release.

## Versioning & Release

Project version is centrally defined in:

* docs/antora.yml
* docs/package.json

## Contributing

We welcome contributions! Please:

* Fork the repository and create a feature branch.
* Adhere to existing coding conventions; add python tests where appropriate.
* Update documentation (docs/) for any new features.
* Submit a pull request with a clear description of your changes.

## License

This project is licensed under the MIT License.
See LICENSE for full details.
