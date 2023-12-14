[![MCHP](images/microchip.png)](https://www.microchip.com)

# pyawsutils - Python AWS utils
pyawsutils is a collection of utilities for interacting with Amazon Web Services

Install using pip from [pypi.org](https://pypi.org/project/pyawsutils):
```bash
pip install pyawsutils
```

Browse source code on [github](https://github.com/microchip-pic-avr-tools/pyawsutils)

Read API documentation on [github](https://microchip-pic-avr-tools.github.io/pyawsutils)

Read the changelog on [github](https://github.com/microchip-pic-avr-tools/pyawsutils/blob/main/CHANGELOG.md)

## Usage
pyawsutils can be used as a command-line interface or a library. 

### Using the pyawsutils CLI
To get top level help
```bash
pyawsutils --help
```
To get the pyawsutils version
```bash
pyawsutils --version
```

For more CLI usage examples see pypi.md.

### Using pyawsutils as a library package
pyawsutils can be used as a library.  Its primary consumer is [iotprovision](https://pypi.org/project/iotprovision)

For usage examples see pypi.md.

## Notes for Linux® systems
This package uses pyedbglib and other libraries for USB transport and some udev rules are required.
For details see the pyedbglib package: https://pypi.org/project/pyedbglib
