# Feel++ mo2fmu converter

Modelica to FMU converter based on dymola

## Installation

```
$ uv venv --system-site-packages
$ source .venv/bin/activate
$ uv pip install -r pyproject.toml --extra dev --extra test
$ pipx run build
$ uv pip install dist/*.whl
```

## Usage
```
$ mo2fmu --help
Usage: mo2fmu [OPTIONS] MO

    convert a .mo file into a .fmu

Options:
  --fmumodelname TEXT          change the modelname of the fmu, by default use
                               the modelical file stem
  --type [all|cs|me|csSolver]  The fmi types cs, me, all.
  --version TEXT               The fmi version.
  --dymola PATH                path to dymola executable.
  --dymolapath PATH            path to dymola executable.
  --dymolaegg PATH             path to dymola egg file relative to dymola root
                               path.
  -v, --verbose                verbose mode.
  -f, --force                  force fmu generation even if file exists.
  --help                       Show this message and exit.
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
