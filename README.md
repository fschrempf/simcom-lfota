# SIMCom Local FOTA

This is a small Python CLI tool to perform firmware updates via UART on SIMCom
A76xxE LTE modules using a local diff file provided by the manufacturer.

## Supported/Tested Devices

* SIMCom A7672E

## Dependencies

* Python 3
* [pyserial](https://pypi.org/project/pyserial/)

## Usage

Showing information about the module and its firmware:

```
./lfota --show /dev/ttyUSB1
```

Performing a firmware update:

```
./lfota --update /dev/ttyUSB1 delta.bin
```

## Copyright

Copyright (c) 2022 Kontron Electronics GmbH  
Author: Frieder Schrempf

## License

The code is licensed under the [MIT](LICENSE) license.
