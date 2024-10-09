import os
import csv
import shutil
import pickle
import fnmatch
from decimal import Decimal
from openlane.steps import Step, OdbpyStep, OpenROADStep
from openlane.steps.step import (
    ViewsUpdate,
    MetricsUpdate,
)
from openlane.steps.common_variables import io_layer_variables
from openlane.flows import Flow, FlowError
from openlane.state import DesignFormat, State
from openlane.common import Path
from openlane.config import Variable
from openlane.logging import (
    verbose,
    debug,
    info,
    rule,
    success,
    warn,
    err,
    subprocess,
)

import pathlib

from typing import Callable, List, Literal, Mapping, Tuple, Union, Optional, Dict, Any

from openlane.steps import (
    Yosys,
    OpenROAD,
    Magic,
    KLayout,
    Odb,
    Netgen,
    Checker,
    Verilator,
    Misc,
)

from openlane.steps.common_variables import pdn_variables

__dir__ = os.path.dirname(os.path.abspath(__file__))

from FABulous import FABulous_API
from FABulous.fabric_generator import code_generation_Verilog

@Step.factory.register()
class FABulousManualIOPlacement(OpenROADStep):
    """
    Manually place I/O pins on a floor-planned ODB file using OpenROAD's built-in placer.
    """

    id = "OpenROAD.ManualIOPlacement"
    name = "Manual I/O Placement"

    config_vars = (
        OpenROADStep.config_vars
        + [
            Variable(
                "FABULOUS_MANUAL_PINS",
                Dict[str, Tuple[str, Decimal, Decimal, Decimal, Decimal]],
                "Dict of pin name to [layer, x, y, width, height]",
                default={},
            ),
        ]
    )

    def get_script_path(self):
        return os.path.join(os.path.dirname(__file__), "scripts", "manual_ioplacer.tcl")

@Step.factory.register()
class FABulousPower(OdbpyStep):

    id = "Odb.FABulousPower"
    name = "FABulous Power connections for the tiles"

    config_vars = pdn_variables + [
        Variable(
            "FABULOUS_HALO_SPACING",
            Optional[Tuple[Decimal, Decimal, Decimal, Decimal]],
            "The spacing around the fabric. [left, bottom, right, top]",
            units="µm",
            default=[100, 100, 100, 100],
        ),
        Variable(
            "FABULOUS_TILE_WIDTHS",
            List[Decimal],
            "The tile widths for each column.",
            units="µm",
            default=[],
        ),
    ]

    def get_script_path(self):
        return os.path.join(os.path.dirname(__file__), "scripts", "odb_power.py")

    def get_command(self) -> List[str]:
        
        x0, y0, x1, y1 = self.config["DIE_AREA"]
        print(f"{x0} {y0} {x1} {y1}")
        
        assert (x0 == 0)
        assert (y0 == 0)
        
        HALO_SPACING = self.config["FABULOUS_HALO_SPACING"]
        halo_left, halo_bottom, halo_right, halo_top = (HALO_SPACING[0], HALO_SPACING[1], HALO_SPACING[2], HALO_SPACING[3])
        print(f"{halo_left} {halo_bottom} {halo_right} {halo_top}")
        
        if self.config["PDK"] in ["sky130"]:
            core_voffset = 5.52
            core_hoffset = 10.88
        elif self.config["PDK"] in ["ihp-sg13g2"]:
            core_voffset = 5.76
            core_hoffset = 9.3
        else:
            print(f'[Error] FABulousPower unknown PDK!')
        
        return super().get_command() + [
            "--width",
            x1,
            "--height",
            y1,
        
            "--halo_left",
            halo_left,
            "--halo_bottom",
            halo_bottom,
            "--halo_right",
            halo_right,
            "--halo_top",
            halo_top,
            
            "--voffset",
            self.config["FP_PDN_VOFFSET"],
            "--vspacing",
            self.config["FP_PDN_VSPACING"],
            "--vpitch",
            self.config["FP_PDN_VPITCH"],
            "--vwidth",
            self.config["FP_PDN_VWIDTH"],
            
            "--metal-layer-name",
            self.config["FP_PDN_VERTICAL_LAYER"],
            
            "--core-voffset",
            core_voffset,

            "--core-hoffset",
            core_hoffset,
            
            "--tile-widths",
            ';'.join(map(str, self.config["FABULOUS_TILE_WIDTHS"])),
        ]

Classic = Flow.factory.get("Classic")

@Flow.factory.register()
class FABulousFabric(Classic):
    Substitutions = [
        # Disable STA
        ("OpenROAD.STAPrePNR", None),
        ("OpenROAD.STAMidPNR", None),
        ("OpenROAD.STAMidPNR", None),
        ("OpenROAD.STAMidPNR", None),
        ("OpenROAD.STAMidPNR", None),
        ("OpenROAD.STAPostPNR", None),
        
        # Custom PDN generation script
        ("OpenROAD.GeneratePDN", FABulousPower),
        
        # Script to manually place single IOs
        ("+OpenROAD.GlobalPlacementSkipIO", FABulousManualIOPlacement)
    ]

    config_vars = Classic.config_vars + [
        Variable(
            "FABULOUS_FABRIC_CONFIG",
            Path,
            "The fabric configuration file.",
        ),
        Variable(
            "FABULOUS_TILE_LIBRARY",
            Path,
            "A path to the tile library.",
        ),
        Variable(
            "FABULOUS_TILE_SPACING",
            Decimal,
            "The spacing between tiles.",
        ),
        Variable(
            "FABULOUS_HALO_SPACING",
            Optional[Tuple[Decimal, Decimal, Decimal, Decimal]],
            "The spacing around the fabric. [left, bottom, right, top]",
            units="µm",
            default=[100, 100, 100, 100],
        ),
        Variable(
            "FABULOUS_TILE_SIZES",
            Dict[str, Tuple[Decimal, Decimal]],
            "The macro size for each tile, names are matched using a regex. First match is used.",
        ),
        Variable(
            "FABULOUS_SPEF_CORNERS",
            Optional[List[str]],
            "The SPEF corners to use for the tile macros.",
            default=["nom"],
        ),
    ]

    def run(
        self,
        initial_state: State,
        **kwargs,
    ) -> Tuple[State, List[Step]]:
        step_list: List[Step] = []

        info(f'VERILOG_FILES: {self.config["VERILOG_FILES"]}')
        info(f'FABULOUS_FABRIC_CONFIG: {self.config["FABULOUS_FABRIC_CONFIG"]}')
        info(f'FABULOUS_TILE_LIBRARY: {self.config["FABULOUS_TILE_LIBRARY"]}')

        assert(os.path.isfile(self.config['FABULOUS_FABRIC_CONFIG']))
        assert(os.path.isdir(self.config['FABULOUS_TILE_LIBRARY']))

        verilog_files = self.config['VERILOG_FILES']

        my_fabric = FABulous_API.FABulous_API(code_generation_Verilog.VerilogWriter(), self.config['FABULOUS_FABRIC_CONFIG'])
        my_fabric.fabric.name = 'eFPGA' # TODO name change does not change module name
        
        tileByFabric = list(my_fabric.fabric.tileDic.keys())
        superTileByFabric = list(my_fabric.fabric.superTileDic.keys())
        allTile = list(set(tileByFabric + superTileByFabric))

        info(f'Tiles used by fabric: {allTile}')
        
        my_fabric.setWriterOutputFile(os.path.join(self.run_dir, f'{my_fabric.fabric.name}.v'))
        my_fabric.genFabric()

        my_fabric.setWriterOutputFile(os.path.join(self.run_dir, f'geometry.csv'))
        my_fabric.genGeometry()

        # Export bitstream spec
        specObject = my_fabric.genBitStreamSpec()
        with open(
            os.path.join(self.run_dir, f'bitStreamSpec.bin'), "wb"
        ) as outFile:
            pickle.dump(specObject, outFile)

        with open(os.path.join(self.run_dir, f'bitStreamSpec.csv'), "w") as f:
            w = csv.writer(f)
            for key1 in specObject["TileSpecs"]:
                w.writerow([key1])
                for key2, val in specObject["TileSpecs"][key1].items():
                    w.writerow([key2, val])

        # Export nextpnr model
        npnrModel = my_fabric.genRoutingModel()
        with open(os.path.join(self.run_dir, f'pips.txt'), "w") as f:
            f.write(npnrModel[0])

        with open(os.path.join(self.run_dir, f'bel.txt'), "w") as f:
            f.write(npnrModel[1])

        with open(os.path.join(self.run_dir, f'bel.v2.txt'), "w") as f:
            f.write(npnrModel[2])

        with open(os.path.join(self.run_dir, f'template.pcf'), "w") as f:
            f.write(npnrModel[3])

        # Get the fabric Verilog file
        verilog_files.append(os.path.join(self.run_dir, f'{my_fabric.fabric.name}.v'))

        tiles = []
        for row in my_fabric.fabric.tile:
            for tile in row:
                if tile != None and not tile.name in tiles:
                    tiles.append(tile.name)
        
        info(f'Discovered tiles in tile map: {tiles}')

        flat = False

        # Extract subtiles from supertiles
        supertiles = {}
        for supertile_name, supertile in my_fabric.fabric.superTileDic.items():
            supertiles[supertile_name] = []
            for tile in supertile.tiles:
                supertiles[supertile_name].append(tile.name)
        
        info(f'supertiles: {supertiles}')

        if flat:
            # Find tile sources
            for tile in tiles:
                info(f'Appending sources for {tile}')
                tile_path = pathlib.Path(self.config['FABULOUS_TILE_LIBRARY']) / tile
                
                if tile_path.is_dir():
                    tile_sources = tile_path.glob('*.v')
                    
                    for source in tile_sources:
                        info(f'- {source}')
                        
                        verilog_files.append(str(source))
                else:
                    if tile_path.exists():
                        raise FlowError(f'Error: {tile_path} is not a directory')
                    else:
                        raise FlowError(f'Error: {tile_path} does not exist')
        else:

            # Create macro configurations
            macros = {}
            
            for macro_name in tiles:
                for supertile, subtiles in supertiles.items():
                    if macro_name in subtiles:
                        # TODO hardcoded anchor
                        if macro_name == subtiles[-1]:
                            macro_name = supertile
                        else:
                            macro_name = None
                    
                if macro_name == None:
                    continue
            
                macros[macro_name] = {
                    'gds': [ os.path.join(self.config['FABULOUS_TILE_LIBRARY'], macro_name, 'macro', self.config['PDK'], 'gds', f'{macro_name}.gds') ],
                    'lef': [ os.path.join(self.config['FABULOUS_TILE_LIBRARY'], macro_name, 'macro', self.config['PDK'], 'lef', f'{macro_name}.lef') ],
                    'nl':  [ os.path.join(self.config['FABULOUS_TILE_LIBRARY'], macro_name, 'macro', self.config['PDK'], 'nl',  f'{macro_name}.nl.v') ],
                    'spef': { },
                    'instances': { },
                }
                
                for corner in self.config['FABULOUS_SPEF_CORNERS']:
                    macros[macro_name]['spef'][f'{corner}_*'] = [ os.path.join(self.config['FABULOUS_TILE_LIBRARY'], macro_name, 'macro', self.config['PDK'], 'spef', corner, f'{macro_name}.{corner}.spef') ],

            # Tile Placement
            TILE_SPACING = self.config["FABULOUS_TILE_SPACING"]
            HALO_SPACING = self.config["FABULOUS_HALO_SPACING"]
            (halo_left, halo_bottom, halo_right, halo_top) = (HALO_SPACING[0], HALO_SPACING[1], HALO_SPACING[2], HALO_SPACING[3])
            
            info(f'FABULOUS_TILE_SIZES: {self.config["FABULOUS_TILE_SIZES"]}')

            tile_sizes = {}

            # Get the tile sizes for each individual tile
            for tile_name in my_fabric.fabric.tileDic:
                tile_size = None
                for pattern in self.config["FABULOUS_TILE_SIZES"]:
                    if fnmatch.fnmatch(tile_name, pattern):
                        tile_size = self.config["FABULOUS_TILE_SIZES"][pattern]
                        break
                
                if tile_size == None:
                    err(f'Could not match {tile_name} with FABULOUS_TILE_SIZES')
                tile_sizes[tile_name] = tile_size
            
            info(f'Tile sizes: {tile_sizes}')
            
            # Calculate width and height of the fabric
            # from the sizes of the individual tiles
            
            FABRIC_NUM_TILES_X = my_fabric.fabric.numberOfColumns
            FABRIC_NUM_TILES_Y = my_fabric.fabric.numberOfRows
            
            # FABRIC_WIDTH
            FABRIC_WIDTH = halo_left + halo_right
            
            for i in range(FABRIC_NUM_TILES_X):
                # Find a non-NULL tile
                for row in my_fabric.fabric.tile:
                    if row[i] != None:
                        # Append tile width
                        FABRIC_WIDTH += tile_sizes[row[i].name][0] + TILE_SPACING
                        break
            
            FABRIC_WIDTH -= TILE_SPACING
            info(f'FABRIC_WIDTH: {FABRIC_WIDTH}')

            # FABRIC_HEIGHT
            FABRIC_HEIGHT = halo_bottom + halo_top
            
            for i in range(FABRIC_NUM_TILES_Y):
                # Find a non-NULL tile
                for tile in my_fabric.fabric.tile[i]:
                    if tile != None:
                        # Append tile height
                        FABRIC_HEIGHT += tile_sizes[tile.name][1] + TILE_SPACING
                        break

            FABRIC_HEIGHT -= TILE_SPACING
            info(f'FABRIC_HEIGHT: {FABRIC_HEIGHT}')

            # Calculate the height of each row
            row_heights = []
            for i in range(FABRIC_NUM_TILES_Y):
                # Find a non-NULL tile
                for tile in my_fabric.fabric.tile[i]:
                    if tile != None:
                        # Append tile height
                        row_heights.append(tile_sizes[tile.name][1])
                        break
            info(f'row_heights: {row_heights}')
            assert(len(row_heights) == FABRIC_NUM_TILES_Y)

            # Calculate the width of each column
            column_widths = []
            for i in range(FABRIC_NUM_TILES_X):
                # Find a non-NULL tile
                for row in my_fabric.fabric.tile:
                    if row[i] != None:
                        # Append tile width
                        column_widths.append(tile_sizes[row[i].name][0])
                        break
            info(f'column_widths: {column_widths}')
            assert(len(column_widths) == FABRIC_NUM_TILES_X)

            # Place macros
            cur_y = 0
            for y, row in enumerate(reversed(my_fabric.fabric.tile)):
                cur_x = 0
                flipped_y = FABRIC_NUM_TILES_Y-1-y

                for x, tile in enumerate(row):
                    if tile == None:
                        tile_name = None
                    else:
                        tile_name = tile.name
                    
                    prefix = f'Tile_X{x}Y{flipped_y}_'
                    
                    for supertile, subtiles in supertiles.items():
                        if tile_name in subtiles:
                            # TODO hardcoded anchor
                            if tile_name == subtiles[-1]:
                                tile_name = supertile
                                
                                prefix = f'Tile_X{x}Y{flipped_y-1}_'
                            else:
                                tile_name = None
                    
                    if tile_name == None:
                        info(f'Skipping {tile_name}')
                    else:
                        if not tile_name in macros:
                            err(f'Could not find {tile_name} in macros')

                        macros[tile_name]['instances'][f'{prefix}{tile_name}'] = {
                            'location': [
                                halo_left + cur_x,
                                halo_bottom + cur_y #(TILE_HEIGHT + TILE_SPACING) * (FABRIC_NUM_TILES_Y-1-y)
                            ],
                            'orientation': 'N',
                        }
                    
                    cur_x += column_widths[x]

                cur_y += row_heights[flipped_y]

            # Set DIE_AREA and FP_SIZING
            self.config = self.config.copy(DIE_AREA=[0, 0, FABRIC_WIDTH, FABRIC_HEIGHT])
            self.config = self.config.copy(FP_SIZING="absolute")

            info(f'Setting DIE_AREA to {self.config["DIE_AREA"]}')
            info(f'Setting FP_SIZING to {self.config["FP_SIZING"]}')

            # Set MACROS
            self.config = self.config.copy(MACROS=macros)
            
            # Set FABULOUS_TILE_WIDTHS
            self.config = self.config.copy(FABULOUS_TILE_WIDTHS=column_widths)
            
            info(f'Setting MACROS to {self.config["MACROS"]}')

        info(verilog_files)

        # Overwrite VERILOG_FILES config variable with our Verilog files
        self.config = self.config.copy(VERILOG_FILES=verilog_files)

        info(f'Setting VERILOG_FILES to {self.config["VERILOG_FILES"]}')

        (final_state, steps) = super().run(initial_state, **kwargs)
        
        final_views_path = os.path.abspath(os.path.join('.', 'macro', self.config['PDK']))
        info(f'Saving final views for FABulous to {final_views_path}')
        final_state.save_snapshot(final_views_path)
        
        info(f'Copying FABulous related files.')
        fabulous_path = os.path.abspath(os.path.join('.', 'macro', self.config['PDK'], 'fabulous'))
        fabulous_hidden_path = os.path.join(fabulous_path, '.FABulous')
        
        os.makedirs(fabulous_path, exist_ok=True)
        os.makedirs(fabulous_hidden_path, exist_ok=True)
        
        shutil.copy(os.path.join(self.run_dir, f'{my_fabric.fabric.name}.v'), os.path.join(fabulous_path, f'{my_fabric.fabric.name}.v'))
        shutil.copy(os.path.join(self.run_dir, f'geometry.csv'), os.path.join(fabulous_path, f'geometry.csv'))
        shutil.copy(os.path.join(self.run_dir, f'bitStreamSpec.bin'), os.path.join(fabulous_path, f'bitStreamSpec.bin'))
        shutil.copy(os.path.join(self.run_dir, f'bitStreamSpec.csv'), os.path.join(fabulous_path, f'bitStreamSpec.csv'))
        shutil.copy(os.path.join(self.run_dir, f'template.pcf'), os.path.join(fabulous_path, f'template.pcf'))
        
        # Hidden files, they need to be in .FABulous
        shutil.copy(os.path.join(self.run_dir, f'pips.txt'), os.path.join(fabulous_hidden_path, f'pips.txt'))
        shutil.copy(os.path.join(self.run_dir, f'bel.txt'), os.path.join(fabulous_hidden_path, f'bel.txt'))
        shutil.copy(os.path.join(self.run_dir, f'bel.v2.txt'), os.path.join(fabulous_hidden_path, f'bel.v2.txt'))
        
        return (final_state, steps)
