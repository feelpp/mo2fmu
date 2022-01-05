# mo2fmu
Modelica to FMU converter

## Installation

```
$ pip install --editable .
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
