# `openlane_plugin_fabulous`

This is a plugin for [OpenLane 2](https://github.com/efabless/openlane2) that integrates [FABulous](https://github.com/FPGA-Research/FABulous).

It provides two custom flows:

- `FABulousTile` - Used to harden a tile or supertile.
- `FABulousFabric` - Used to stitch the tiles into a fabric.

> [!IMPORTANT]
> For documentation about tile stitching, please see the [README](docs/README.md) in the docs.

## FABulousTile

The `config.json` needs to be placed in the same directory as the `tile.csv` file.

- Set `DESIGN_NAME` to the name of the tile, e.g. `LUT4AB`.
- Set `CLOCK_PORT` to the clock port of the tile, e.g. `UserCLK`.

Additional configuration variables:

- `FABULOUS_EXTERNAL_SIDE`: `Optional[Literal["N", "E", "S", "W"]]`  
  The side of the macro at which the external pins are placed.

## FABulousFabric

- Set `DESIGN_NAME` to `eFPGA`
- Add your models and custom cells to `VERILOG_FILES`, e.g. `["models_pack.v", "custom.v"]`

Additional configuration variables:

- `FABULOUS_TILE_MAP`: `List[List[str]]`  
  A tile map of FABulous tiles available in the tile library.
- `FABULOUS_TILE_LIBRARY`: `str`  
  A path to the tile library.

## Testing this Plugin

Enable a shell with the plugin:

```bash
nix-shell
```

Checking if the plugin is recognized by OpenLane:

```bash
$ nix develop --command openlane --version
[…]
Discovered plugins:
openlane_plugin_fabulous -> 0.1.0
```

## License

Apache License, version 2.0.

See `License`.

