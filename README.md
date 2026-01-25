# Feel++ mo2fmu converter

Modelica to FMU converter with Dymola and OpenModelica support.

## Features

- **Multiple backends**: Supports both Dymola and OpenModelica compilers
- **Automatic backend selection**: Automatically detects available compilers
- **FMI 1.0, 2.0, and 3.0 support**: Generate Co-Simulation and Model Exchange FMUs
- **Python API**: Programmatic access for integration into workflows
- **Command-line interface**: Simple CLI with `compile` and `check` subcommands

## Installation

### From PyPI (Recommended)

Install the latest stable release from PyPI using [uv](https://docs.astral.sh/uv/):

```console
uv pip install feelpp-mo2fmu
```

### With OpenModelica Support

To use OpenModelica as a backend, install with the optional dependency:

```console
uv pip install "feelpp-mo2fmu[openmodelica]"
```

This will install [OMPython](https://github.com/OpenModelica/OMPython) for Python integration with OpenModelica.

### With Simulation Support

To run simulations and validate FMUs (useful for testing):

```console
uv pip install "feelpp-mo2fmu[simulation]"
```

This will install [FMPy](https://github.com/CATIA-Systems/FMPy) for FMU simulation and validation.

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

**Environment Variables:**
- `DYMOLA_ROOT`: Path to Dymola installation root directory (default: `/opt/dymola-2025xRefresh1-x86_64/`)
- `DYMOLA_EXECUTABLE`: Path to Dymola executable binary (default: `/usr/local/bin/dymola`)
- `DYMOLA_WHL`: Relative path to Dymola Python wheel from DYMOLA_ROOT (default: `Modelica/Library/python_interface/dymola-2025.1-py3-none-any.whl`)

### OpenModelica Location

OpenModelica can be configured via environment variables:

```bash
export OPENMODELICA_HOME=/usr/lib/omc
```

**Environment Variables:**
- `OPENMODELICA_HOME`: Path to OpenModelica installation (default: auto-detected)

## Command Line Interface

The mo2fmu CLI provides two subcommands: `compile` and `check`.

### Main Help

```console
$ mo2fmu --help
Usage: mo2fmu [OPTIONS] COMMAND [ARGS]...

  mo2fmu - Convert Modelica models to Functional Mock-up Units (FMUs).

  Use 'mo2fmu compile' to generate FMUs or 'mo2fmu check' to verify compilers.

Options:
  -v, --version  Show version information.
  --help         Show this message and exit.

Commands:
  check    Check availability of Modelica compilers and their FMI support.
  compile  Compile a Modelica model to FMU.
```

### Compile Command

Generate FMUs from Modelica models:

```console
$ mo2fmu compile --help
Usage: mo2fmu compile [OPTIONS] MO OUTDIR

  Compile a Modelica model to FMU.

Options:
  --name TEXT                     Custom name for the FMU (default: .mo file stem).
  -l, --load TEXT                 Load one or more Modelica packages.
  --flags TEXT                    Compiler-specific flags for FMU translation.
  -t, --type [all|cs|me|csSolver] FMI type: cs (Co-Simulation), me (Model Exchange),
                                  all, or csSolver.
  --fmi-version [1|2|3]           FMI version. FMI 3.0 requires Dymola 2024+
                                  or OpenModelica 1.21+.
  -b, --backend [dymola|openmodelica|auto]
                                  Modelica compiler backend (default: auto-detect).
  --dymola PATH                   Path to Dymola root directory.
  --dymola-exec PATH              Path to Dymola executable.
  --dymola-whl PATH               Path to Dymola wheel file (relative to Dymola root).
  -v, --verbose                   Enable verbose output.
  -f, --force                     Overwrite existing FMU.
  --help                          Show this message and exit.
```

**Compile Examples:**

```console
# Basic compilation (auto-detect backend)
mo2fmu compile model.mo ./output

# Compile with OpenModelica backend
mo2fmu compile --backend openmodelica model.mo ./output

# Compile FMI 3.0 Co-Simulation FMU with verbose output
mo2fmu compile -v --fmi-version 3 --type cs model.mo ./output

# Force overwrite existing FMU
mo2fmu compile -f model.mo ./output

# Load additional Modelica packages
mo2fmu compile --load package1.mo --load package2.mo model.mo ./output
```

### Check Command

Verify compiler availability and FMI support:

```console
$ mo2fmu check --help
Usage: mo2fmu check [OPTIONS]

  Check availability of Modelica compilers and their FMI support.

Options:
  --dymola PATH       Path to Dymola root directory.
  --dymola-exec PATH  Path to Dymola executable.
  --dymola-whl PATH   Path to Dymola wheel file (relative to Dymola root).
  --json              Output results as JSON.
  --help              Show this message and exit.
```

**Check Examples:**

```console
# Check all available compilers
mo2fmu check

# Output as JSON (for scripting)
mo2fmu check --json

# Check with custom Dymola path
mo2fmu check --dymola /opt/dymola-2024x
```

## Python API

### Recommended API

The recommended API provides a clean interface with automatic backend selection:

```python
from feelpp.mo2fmu import compileFmu, getCompiler, checkCompilers

# Auto-detect and use available compiler
result = compileFmu("path/to/model.mo", "./output")
if result.success:
    print(f"FMU created at {result.fmu_path}")
else:
    print(f"Error: {result.error_message}")

# Explicitly use OpenModelica
result = compileFmu("path/to/model.mo", "./output", backend="openmodelica")

# Compile FMI 3.0 Model Exchange FMU
result = compileFmu(
    "path/to/model.mo",
    "./output",
    fmiType="me",
    fmiVersion="3",
    verbose=True,
)

# Check available compilers
available = checkCompilers()
for name, info in available.items():
    print(f"{name}: available={info['available']}, versions={info.get('fmi_versions', [])}")

# Get a specific compiler instance for more control
compiler = getCompiler("openmodelica")
if compiler.is_available:
    print(f"Using {compiler.name}")
```

### Using Compiler Classes Directly

For full control, use the compiler classes directly:

```python
from feelpp.mo2fmu import (
    DymolaCompiler,
    OpenModelicaCompiler,
    ModelicaModel,
    CompilationConfig,
)
from pathlib import Path

# Using OpenModelica
compiler = OpenModelicaCompiler()
if compiler.is_available:
    model = ModelicaModel(Path("path/to/model.mo"))
    config = CompilationConfig(
        fmi_type="cs",      # Co-Simulation
        fmi_version="3",    # FMI 3.0
        verbose=True,
    )
    result = compiler.compile(model, Path("./output"), config)

    if result.success:
        print(f"FMU created: {result.fmu_path}")
    else:
        print(f"Compilation failed: {result.error_message}")

# Using Dymola
compiler = DymolaCompiler()
if compiler.is_available:
    result = compiler.compile(model, Path("./output"), config)
```

### Legacy API

The original API is still available for backward compatibility:

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
    force=False,
    backend="dymola",  # or "openmodelica", "auto"
)
```

## Backend Comparison

| Feature | Dymola | OpenModelica |
|---------|--------|--------------|
| License | Commercial | Open Source (GPL) |
| FMI 1.0 | ✓ | ✓ |
| FMI 2.0 | ✓ | ✓ |
| FMI 3.0 | ✓ (2024+) | ✓ (v1.21+) |
| Co-Simulation | ✓ | ✓ |
| Model Exchange | ✓ | ✓ |
| csSolver type | ✓ | ✗ |
| Modelica Standard Library | ✓ | ✓ |
| BuildingSystems | ✓ | Partial |
| Buildings Library | ✓ | ✓ |

## Running Tests

The test suite includes unit tests and FMU simulation tests:

```console
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run only unit tests (no simulation)
uv run pytest tests/test_compilers.py tests/test_mo2fmu.py

# Run simulation tests (requires FMPy)
uv run pytest tests/test_fmu_simulation.py
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
