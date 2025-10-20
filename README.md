# Feel++ mo2fmu converter

Modelica to FMU converter based on dymola

## Installation

### From PyPI (Recommended)

Install the latest stable release from PyPI:

```console
pip install feelpp-mo2fmu
```

Or using uv (faster):

```console
uv pip install feelpp-mo2fmu
```

### From Source

For development or to use the latest unreleased features:

```console
git clone https://github.com/feelpp/mo2fmu.git
cd mo2fmu
uv venv .venv-mo2fmu
source .venv-mo2fmu/bin/activate  # On Windows: .venv-mo2fmu\Scripts\activate
uv pip install -e ".[all]"
```

## Configuration

### Dymola Location

The Dymola installation location can be configured via environment variables:

```bash
export DYMOLA_ROOT=/opt/dymola-2025xRefresh1-x86_64/
export DYMOLA_EXECUTABLE=/usr/local/bin/dymola
export DYMOLA_WHL=Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl
```

These environment variables are used by:
- Tests (avoiding hardcoded paths)
- CI/CD workflows
- Command-line interface defaults

**Environment Variables:**
- `DYMOLA_ROOT`: Path to Dymola installation root directory (default: `/opt/dymola-2025xRefresh1-x86_64/`)
- `DYMOLA_EXECUTABLE`: Path to Dymola executable binary (default: `/usr/local/bin/dymola`)
- `DYMOLA_WHL`: Relative path to Dymola Python wheel from DYMOLA_ROOT (default: `Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl`)

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
