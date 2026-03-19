# `librelane_plugin_fabulous`

This is a plugin for [LibreLane](https://github.com/librelane/librelane) that integrates [FABulous](https://github.com/FPGA-Research/FABulous).

It provides two custom flows:

- `FABulousTile` - Used to harden a tile or supertile.
- `FABulousFabric` - Used to stitch the tiles into a fabric.

Example tile libraries can be found in this repository: https://github.com/mole99/fabulous-tiles
Examples of fabrics using these tile libraries can be found under: https://github.com/mole99/fabulous-fabrics

> [!IMPORTANT]
> For documentation about tile stitching, please see the [README](docs/README.md) in the docs.

## FABulousTile

The `config.json` needs to be placed in the same directory as the `tile.csv` file.

- Set `DESIGN_NAME` to the name of the tile, e.g. `LUT4AB`.
- Set `CLOCK_PORT` to the clock port of the tile.

Additional configuration variables:

- `FABULOUS_EXTERNAL_SIDE`: `Optional[Literal["N", "E", "S", "W"]]`
  The side of the macro at which the external pins are placed.
- `FABULOUS_SUPERTILE`: `Optional[bool]`
  Is the tile a supertile?
- `FABULOUS_TILE_DIR`: `Path`
  Path to the tile directory where the tile CSV file is located.

## FABulousFabric

- Set `DESIGN_NAME` to the name of your fabric.
- Add your models and custom cells to `VERILOG_FILES`, e.g. `["models_pack.v", "custom.v"]`.

Additional configuration variables:

- `FABULOUS_FABRIC_CONFIG`: `Path`
  The fabric configuration CSV file. It includes the tile map of the fabric, the parameters, and paths to the tiles.
- `FABULOUS_TILE_LIBRARY`: `Path`
  The path to the tile library.
- `FABULOUS_TILE_SPACING`: `Optional[Decimal]`
  The spacing between tiles.
- `FABULOUS_HALO_SPACING`: `Optional[Tuple[Decimal, Decimal, Decimal, Decimal]]`
  The spacing around the fabric. [left, bottom, right, top]
- `FABULOUS_SPEF_CORNERS`: `Optional[List[str]]`
  The SPEF corners to use for the tile macros.

## Testing this Plugin

Enable a shell with the plugin:

```bash
nix-shell
```

Checking if the plugin is recognized by LibreLane:

```bash
$ nix develop --command librelane --version
[…]
Discovered plugins:
librelane_plugin_fabulous -> 1.0.0
```

## License

Apache License, version 2.0.

See `License`.

