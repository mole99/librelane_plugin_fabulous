import os
import yaml
import pathlib
from decimal import Decimal
from typing import Callable, List, Literal, Mapping, Tuple, Union, Optional, Dict, Any
from librelane.steps import Step, OdbpyStep
from librelane.steps.step import (
    ViewsUpdate,
    MetricsUpdate,
)
from librelane.steps.common_variables import io_layer_variables
from librelane.flows import Flow, FlowError
from librelane.state import DesignFormat, State
from librelane.common import Path
from librelane.config import Variable
from librelane.logging import (
    verbose,
    debug,
    info,
    rule,
    success,
    warn,
    err,
    subprocess,
)
from librelane.steps import (
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
from FABulous.fabric_generator.parser import parse_csv
from FABulous.fabric_generator.gen_fabric.gen_switchmatrix import genTileSwitchMatrix
from FABulous.fabric_generator.gen_fabric.gen_configmem import generateConfigMem
from FABulous.fabric_generator.code_generator.code_generator_Verilog import (
    VerilogCodeGenerator,
)
from FABulous.fabric_generator.gen_fabric.gen_tile import (
    generateSuperTile,
    generateTile,
)
from FABulous.fabric_definition.define import IO, Side
from FABulous.fabric_definition.Port import Port

__dir__ = os.path.dirname(os.path.abspath(__file__))
_migrate_unmatched_io = lambda x: "unmatched_design" if x else "none"

@Step.factory.register()
class FABulousIOPlacement(OdbpyStep):
    """
    Places I/O pins using a custom script, which uses a "pin order configuration"
    file.

    Check the reference documentation for the structure of said file.
    """

    id = "Odb.FABulousIOPlacement"
    name = "FABulous I/O Placement"
    long_name = "FABulous I/O Pin Placement Script"

    config_vars = io_layer_variables + [
        Variable(
            "IO_PIN_V_LENGTH",
            Optional[Decimal],
            """
            The length of the pins with a north or south orientation. If unspecified by a PDK, the script will use whichever is higher of the following two values:
                * The pin width
                * The minimum value satisfying the minimum area constraint given the pin width
            """,
            units="µm",
            pdk=True,
        ),
        Variable(
            "IO_PIN_H_LENGTH",
            Optional[Decimal],
            """
            The length of the pins with an east or west orientation. If unspecified by a PDK, the script will use whichever is higher of the following two values:
                * The pin width
                * The minimum value satisfying the minimum area constraint given the pin width
            """,
            units="µm",
            pdk=True,
        ),
        Variable(
            "IO_PIN_ORDER_CFG",
            Optional[Path],
            "Path to a custom pin configuration file.",
            deprecated_names=["FP_PIN_ORDER_CFG"],
        ),
        Variable(
            "ERRORS_ON_UNMATCHED_IO",
            Literal["none", "unmatched_design", "unmatched_cfg", "both"],
            "Controls whether to emit an error in: no situation, when pins exist in the design that do not exist in the config file, when pins exist in the config file that do not exist in the design, and both respectively. `both` is recommended, as the default is only for backwards compatibility with librelane 1.",
            default="unmatched_design",  # Backwards compatible with librelane 1
            deprecated_names=[
                ("QUIT_ON_UNMATCHED_IO", _migrate_unmatched_io),
            ],
        ),
    ]

    def get_script_path(self):
        return os.path.join(os.path.dirname(__file__), "scripts", "io_place.py")

    def get_command(self) -> List[str]:
        length_args = []
        if self.config["IO_PIN_V_LENGTH"] is not None:
            length_args += ["--ver-length", self.config["IO_PIN_V_LENGTH"]]
        if self.config["IO_PIN_H_LENGTH"] is not None:
            length_args += ["--hor-length", self.config["IO_PIN_H_LENGTH"]]

        return (
            super().get_command()
            + [
                "--config",
                self.config["IO_PIN_ORDER_CFG"],
                "--hor-layer",
                self.config["FP_IO_HLAYER"],
                "--ver-layer",
                self.config["FP_IO_VLAYER"],
                "--hor-width-mult",
                str(self.config["IO_PIN_V_THICKNESS_MULT"]),
                "--ver-width-mult",
                str(self.config["IO_PIN_H_THICKNESS_MULT"]),
                "--hor-extension",
                str(self.config["IO_PIN_H_EXTENSION"]),
                "--ver-extension",
                str(self.config["IO_PIN_V_EXTENSION"]),
                "--unmatched-error",
                self.config["ERRORS_ON_UNMATCHED_IO"],
            ]
            + length_args
        )

    def run(self, state_in, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["IO_PIN_ORDER_CFG"] is None:
            info("No custom floorplan file configured, skipping…")
            return {}, {}
        return super().run(state_in, **kwargs)

Classic = Flow.factory.get("Classic")

@Flow.factory.register()
class FABulousTile(Classic):
    Substitutions = [
        # Replace with FABulous IO Placement
        ("Odb.CustomIOPlacement", FABulousIOPlacement),
        
        # Disable STA
        ("OpenROAD.STAPrePNR", None),
        ("OpenROAD.STAMidPNR", None),
        ("OpenROAD.STAMidPNR", None),
        ("OpenROAD.STAMidPNR", None),
        ("OpenROAD.STAMidPNR", None),
        ("OpenROAD.STAPostPNR", None),
    ]
    
    config_vars = Classic.config_vars + [
        Variable(
            "FABULOUS_EXTERNAL_SIDE",
            Optional[Literal["N", "E", "S", "W"]],
            """
            The side of the macro at which the external pins are placed.
            """
        ),
        Variable(
            "FABULOUS_SUPERTILE",
            Optional[bool],
            """
            Is the tile a supertile?
            """,
            default = False,
        ),
        Variable(
            "FABULOUS_TILE_DIR",
            Path,
            """
            Path to the tile directory where the CSV file is located.
            """,
        ),
        
    ]

    def run(
        self,
        initial_state: State,
        **kwargs,
    ) -> Tuple[State, List[Step]]:
        step_list: List[Step] = []

        info(f"VERILOG_FILES: {self.config['VERILOG_FILES']}")
        info(f"FABULOUS_TILE_DIR: {self.config['FABULOUS_TILE_DIR']}")
        
        verilog_files = self.config['VERILOG_FILES']

        # Create a dummy fabric
        # TODO FABulous should be able to create tiles without a fabric
        csv_file = os.path.join(self.run_dir, 'fabric.csv')
        
        # If supertile get the individual tiles
        supertile_tiles = []
        if self.config["FABULOUS_SUPERTILE"]:
            with open(os.path.join(self.config["FABULOUS_TILE_DIR"], self.config["DESIGN_NAME"] + ".csv"), 'r') as f:
                f.readline() # Skip SuperTILE header
                
                while 'EndSuperTILE' not in (line := f.readline()):
                    line = line.strip()
                    tiles = line.split(',')
                    for tile in tiles:
                        if tile != '':
                            supertile_tiles.append(tile)
        
        print(f'supertile_tiles: {supertile_tiles}')
        
        with open(csv_file, 'w') as f:
            f.write('FabricBegin\n')

            name = self.config["DESIGN_NAME"]

            # Only 1x2 supported for now
            if self.config["FABULOUS_SUPERTILE"]:
                for tile in supertile_tiles:
                    f.write(f'{tile}\n')
            else:
                f.write(f'{name}\n')

            f.write('FabricEnd\n')
            f.write('ParametersBegin\n')

            f.write('ConfigBitMode,frame_based\n') # default is FlipFlopChain
            f.write('GenerateDelayInSwitchMatrix,80\n')
            f.write('MultiplexerStyle,custom\n')
            f.write('SuperTileEnable,{"TRUE" if self.config["FABULOUS_SUPERTILE"] else "FALSE"}\n') # TRUE/FALSE
            
            
            if self.config["FABULOUS_SUPERTILE"]:
                for tile in supertile_tiles:
                    f.write(f'Tile,{os.path.abspath(os.path.join(self.config["FABULOUS_TILE_DIR"], tile, f"{tile}.csv"))}\n')
                f.write(f'Supertile,{os.path.abspath(os.path.join(self.config["FABULOUS_TILE_DIR"], self.config["DESIGN_NAME"] + ".csv"))}\n')
            else:
                f.write(f'Tile,{os.path.abspath(os.path.join(self.config["FABULOUS_TILE_DIR"], self.config["DESIGN_NAME"] + ".csv"))}\n')
            
            f.write('ParametersEnd\n')
        
        # Unfortunately necessary
        os.environ["FAB_PROJ_DIR"] = '.'
        
        self.writer = VerilogCodeGenerator()
        self.fabric = parse_csv.parseFabricCSV(pathlib.Path(csv_file))
        self.fabric.name = 'fabulous_fabric'
        
        tileByFabric = list(self.fabric.tileDic.keys())
        superTileByFabric = list(self.fabric.superTileDic.keys())
        allTile = list(set(tileByFabric + superTileByFabric))

        info(f'Tiles used by fabric: {allTile}')

        is_supertile = False
        if self.config['DESIGN_NAME'] in self.fabric.superTileDic:
            is_supertile = True

        # Ports for pin placement
        north_ports_sides: List[List[str]] = []
        east_ports_sides: List[List[str]] = []
        south_ports_sides: List[List[str]] = []
        west_ports_sides: List[List[str]] = []

        if not is_supertile:

            tile = self.fabric.getTileByName(self.config['DESIGN_NAME'])

            # Gen switch matrix
            self.writer.outFileName = pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}_switch_matrix.v"))
            genTileSwitchMatrix(self.writer, self.fabric, tile, switch_matrix_debug_signal=False)
            verilog_files.append(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}_switch_matrix.v"))

            # Gen config mem
            self.writer.outFileName = pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}_ConfigMem.v"))
            generateConfigMem(self.writer, self.fabric, tile, pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}_ConfigMem.csv")))
            
            # Termination tiles have no config bits, therefore no config mem is generated
            if pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}_ConfigMem.csv")).exists():
                verilog_files.append(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}_ConfigMem.v"))

            # Gen tile
            info(f"Generating tile {self.config['DESIGN_NAME']}")
            self.writer.outFileName = pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}.v"))
            generateTile(self.writer, self.fabric, tile)
            verilog_files.append(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}.v"))
            info(f"Generated tile {self.config['DESIGN_NAME']}")

            info(tile)

            # Add BELs to verilog files
            for bel in tile.bels:
                if not os.path.relpath(bel.src) in verilog_files:
                    verilog_files.append(os.path.relpath(bel.src))

            # Check external pins side
            for bel in tile.bels:
                if (bel.externalInput or bel.externalOutput) and not self.config['FABULOUS_EXTERNAL_SIDE']:
                    err('Please specify FABULOUS_EXTERNAL_SIDE')

            # Get the ports for the tile
            
            # NORTH ports
            north_ports = []
            
            if self.config['FABULOUS_EXTERNAL_SIDE'] == 'N':
                for bel in tile.bels:
                    info(bel.inputs)
                    info(bel.outputs)
                    info(bel.externalInput)
                    info(bel.externalOutput)
                    
                    north_ports.extend(bel.externalInput)
                    north_ports.extend(bel.externalOutput)

            for port in [port for port in tile.getNorthSidePorts() if port.inOut == IO.OUTPUT]:
                if port.wireCount * abs(port.yOffset) > 1:
                    north_ports.append(f'{port.name}\\[.*\\]')
                else:
                    north_ports.append(port.name)
    
            for port in [port for port in tile.getNorthSidePorts() if port.inOut == IO.INPUT]:
                if port.wireCount * abs(port.yOffset) > 1:
                    north_ports.append(f'{port.name}\\[.*\\]')
                else:
                    north_ports.append(port.name)
            
            north_ports.append('UserCLKo')
            north_ports.append('FrameStrobe_O\\[.*\\]')
            
            # EAST ports
            east_ports = []
            
            if self.config['FABULOUS_EXTERNAL_SIDE'] == 'E':
                for bel in tile.bels:
                    info(bel.inputs)
                    info(bel.outputs)
                    info(bel.externalInput)
                    info(bel.externalOutput)
                    
                    east_ports.extend(bel.externalInput)
                    east_ports.extend(bel.externalOutput)

            for port in [port for port in tile.getEastSidePorts() if port.inOut == IO.INPUT]:
                if port.wireCount * abs(port.xOffset) > 1:
                    east_ports.append(f'{port.name}\\[.*\\]')
                else:
                    east_ports.append(port.name)
    
            for port in [port for port in tile.getEastSidePorts() if port.inOut == IO.OUTPUT]:
                if port.wireCount * abs(port.xOffset) > 1:
                    east_ports.append(f'{port.name}\\[.*\\]')
                else:
                    east_ports.append(port.name)
            
            east_ports.append(f'FrameData_O\\[.*\\]')
            
            # SOUTH ports
            south_ports = []
            
            if self.config['FABULOUS_EXTERNAL_SIDE'] == 'S':
                for bel in tile.bels:
                    info(bel.inputs)
                    info(bel.outputs)
                    info(bel.externalInput)
                    info(bel.externalOutput)
                    
                    south_ports.extend(bel.externalInput)
                    south_ports.extend(bel.externalOutput)

            for port in [port for port in tile.getSouthSidePorts() if port.inOut == IO.INPUT]:
                if port.wireCount * abs(port.yOffset) > 1:
                    south_ports.append(f'{port.name}\\[.*\\]')
                else:
                    south_ports.append(port.name)
    
            for port in [port for port in tile.getSouthSidePorts() if port.inOut == IO.OUTPUT]:
                if port.wireCount * abs(port.yOffset) > 1:
                    south_ports.append(f'{port.name}\\[.*\\]')
                else:
                    south_ports.append(port.name)
            
            south_ports.append('UserCLK')
            south_ports.append('FrameStrobe\\[.*\\]')
            
            # WEST ports
            west_ports = []
            
            if self.config['FABULOUS_EXTERNAL_SIDE'] == 'W':
                for bel in tile.bels:
                    info(bel.inputs)
                    info(bel.outputs)
                    info(bel.externalInput)
                    info(bel.externalOutput)
                    
                    west_ports.extend(bel.externalInput)
                    west_ports.extend(bel.externalOutput)

            for port in [port for port in tile.getWestSidePorts() if port.inOut == IO.OUTPUT]:
                if port.wireCount * abs(port.xOffset) > 1:
                    west_ports.append(f'{port.name}\\[.*\\]')
                else:
                    west_ports.append(port.name)
    
            for port in [port for port in tile.getWestSidePorts() if port.inOut == IO.INPUT]:
                if port.wireCount * abs(port.xOffset) > 1:
                    west_ports.append(f'{port.name}\\[.*\\]')
                else:
                    west_ports.append(port.name)
            
            west_ports.append(f'FrameData\\[.*\\]')

            # A single tile only has 1 side per direction
            north_ports_sides.append(north_ports)
            east_ports_sides.append(east_ports)
            south_ports_sides.append(south_ports)
            west_ports_sides.append(west_ports)

        else:
        
            # Get the supertile
            supertile = self.fabric.superTileDic[self.config['DESIGN_NAME']]
        
            for tile in supertile.tiles:
            
                # Gen switch matrix
                self.writer.outFileName = pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], tile.name, f"{tile.name}_switch_matrix.v"))
                genTileSwitchMatrix(self.writer, self.fabric, tile, switch_matrix_debug_signal=False)
                verilog_files.append(os.path.join(self.config["FABULOUS_TILE_DIR"], tile.name, f"{tile.name}_switch_matrix.v"))

                # Gen config mem
                self.writer.outFileName = pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], tile.name, f"{tile.name}_ConfigMem.v"))
                generateConfigMem(self.writer, self.fabric, tile, pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], tile.name, f"{tile.name}_ConfigMem.csv")))
                
                # Termination tiles have no config bits, therefore no config mem is generated
                if pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], tile.name, f"{tile.name}_ConfigMem.csv")).exists():
                    verilog_files.append(os.path.join(self.config["FABULOUS_TILE_DIR"], tile.name, f"{tile.name}_ConfigMem.v"))
                
                # Gen tile
                info(f"Generating tile {tile.name}")
                self.writer.outFileName = pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], tile.name, f"{tile.name}.v"))
                generateTile(self.writer, self.fabric, tile)
                verilog_files.append(os.path.join(self.config["FABULOUS_TILE_DIR"], tile.name, f"{tile.name}.v"))
                info(f"Generated tile {tile.name}")
                
                info(tile)

                # Add BELs to verilog files
                for bel in tile.bels:
                    if not os.path.relpath(bel.src) in verilog_files:
                        verilog_files.append(os.path.relpath(bel.src))
        
            # Gen super tile
            info(f"Generating tile {self.config['DESIGN_NAME']}")
            self.writer.outFileName = pathlib.Path(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}.v"))
            generateSuperTile(self.writer, self.fabric, supertile)
            info(f"Generated tile {self.config['DESIGN_NAME']}")
            verilog_files.append(os.path.join(self.config["FABULOUS_TILE_DIR"], f"{self.config['DESIGN_NAME']}.v"))
        
            portsAround = supertile.getPortsAroundTile()
            info(portsAround)

            port_sides_dict = {
                'N': north_ports_sides,
                'E': east_ports_sides,
                'S': south_ports_sides,
                'W': west_ports_sides
            }

            # Add external pins
            if self.config['FABULOUS_EXTERNAL_SIDE'] in port_sides_dict:
                ports = []
                ports.extend(bel.externalInput)
                ports.extend(bel.externalOutput)
                
                # TODO: Hack
                # Add FrameData Signals if external side = E
                if self.config['FABULOUS_EXTERNAL_SIDE'] == 'E':
                    east_ports = []
                    for k, v in portsAround.items():
                        if not v:
                            continue
                        x, y = k.split(",")
                
                        prefix = f'Tile_X{x}Y{y}_'
                        east_ports.append(prefix + 'FrameData_O\\[.*\\]')
                    ports.extend(east_ports)
                
                port_sides_dict[self.config['FABULOUS_EXTERNAL_SIDE']].append(ports)

            # Get the ports for the fabric            
            for coords, ports_side in portsAround.items():
            
                x, y = coords.split(',')
            
                info(f'({x},{y}): {ports_side}')
            
                for ports in ports_side:
                
                    # Empty side, continue with next one
                    if not ports:
                        continue

                    """port = Port(
                        wireDirection = port.wireDirection,
                        sourceName = port.sourceName,
                        xOffset = port.xOffset,
                        yOffset = port.yOffset,
                        destinationName = port.destinationName,
                        wireCount = port.wireCount,
                        name = f'Tile_X{x}Y{y}_' + port.name,
                        inOut = port.inOut,
                        sideOfTile = port.sideOfTile,
                    )"""
                    
                    prefix = f'Tile_X{x}Y{y}_'

                    # TODO Find a better way to get the side
                    side = ports[0].sideOfTile

                    if side == Side.NORTH:

                        # NORTH ports
                        north_ports = []

                        for port in [port for port in ports if port.inOut == IO.OUTPUT]:
                            if port.wireCount * abs(port.yOffset) > 1:
                                north_ports.append(f'{prefix}{port.name}\\[.*\\]')
                            else:
                                north_ports.append(prefix + port.name)
                
                        for port in [port for port in ports if port.inOut == IO.INPUT]:
                            if port.wireCount * abs(port.yOffset) > 1:
                                north_ports.append(f'{prefix}{port.name}\\[.*\\]')
                            else:
                                north_ports.append(prefix + port.name)
                        
                        north_ports.append(prefix + 'UserCLKo')
                        north_ports.append(prefix + 'FrameStrobe_O\\[.*\\]')
                        
                        north_ports_sides.append(north_ports)
                        
                    elif side == Side.EAST:
                        
                        # EAST ports
                        east_ports = []

                        for port in [port for port in ports if port.inOut == IO.INPUT]:
                            if port.wireCount * abs(port.xOffset) > 1:
                                east_ports.append(f'{prefix}{port.name}\\[.*\\]')
                            else:
                                east_ports.append(prefix + port.name)
                
                        for port in [port for port in ports if port.inOut == IO.OUTPUT]:
                            if port.wireCount * abs(port.xOffset) > 1:
                                east_ports.append(f'{prefix}{port.name}\\[.*\\]')
                            else:
                                east_ports.append(prefix + port.name)
                        
                        east_ports.append(prefix + 'FrameData_O\\[.*\\]')
                        
                        east_ports_sides.append(east_ports)

                    elif side == Side.SOUTH:

                        # SOUTH ports
                        south_ports = []

                        for port in [port for port in ports if port.inOut == IO.INPUT]:
                            if port.wireCount * abs(port.yOffset) > 1:
                                south_ports.append(f'{prefix}{port.name}\\[.*\\]')
                            else:
                                south_ports.append(prefix + port.name)
                
                        for port in [port for port in ports if port.inOut == IO.OUTPUT]:
                            if port.wireCount * abs(port.yOffset) > 1:
                                south_ports.append(f'{prefix}{port.name}\\[.*\\]')
                            else:
                                south_ports.append(prefix + port.name)
                        
                        south_ports.append(prefix + 'UserCLK')
                        south_ports.append(prefix + 'FrameStrobe\\[.*\\]')

                        south_ports_sides.append(south_ports)

                    elif side == Side.WEST:

                        # WEST ports
                        west_ports = []

                        for port in [port for port in ports if port.inOut == IO.OUTPUT]:
                            if port.wireCount * abs(port.xOffset) > 1:
                                west_ports.append(f'{prefix}{port.name}\\[.*\\]')
                            else:
                                west_ports.append(prefix + port.name)
                
                        for port in [port for port in ports if port.inOut == IO.INPUT]:
                            if port.wireCount * abs(port.xOffset) > 1:
                                west_ports.append(f'{prefix}{port.name}\\[.*\\]')
                            else:
                                west_ports.append(prefix + port.name)
                        
                        west_ports.append(prefix + 'FrameData\\[.*\\]')

                        west_ports_sides.append(west_ports)

                    else:
                        err('No side for port found!')

        info(f'north_ports_sides: {north_ports_sides}')
        info(f'east_ports_sides: {east_ports_sides}')
        info(f'south_ports_sides: {south_ports_sides}')
        info(f'west_ports_sides: {west_ports_sides}')

        # Create port files that can be read by the io_place script
        pin_file_old = os.path.join(self.run_dir, 'pins_old.cfg')
        with open(pin_file_old, 'w') as f:            
            f.write(f'#N\n\n')
            
            for port_side in north_ports_sides:
                for port in port_side:
                    f.write(f'{port}\n')
                
            #f.write('Tile_X0Y0_UserCLKo\n')
            #f.write('Tile_X0Y0_FrameStrobe_O\\[.*\\]\n')
            
            f.write(f'\n#E\n\n')
            
            for port_side in east_ports_sides:
                for port in port_side:
                    f.write(f'{port}\n')
            
            #f.write(f'Tile_X0Y0_FrameData_O\\[.*\\]\n')
            #f.write(f'Tile_X0Y1_FrameData_O\\[.*\\]\n')
            
            f.write(f'\n#S\n\n')
            
            for port_side in south_ports_sides:
                for port in port_side:
                    f.write(f'{port}\n')
        
            #f.write('Tile_X0Y1_UserCLK\n')
            #f.write('Tile_X0Y1_FrameStrobe\\[.*\\]\n')
            
            f.write(f'\n#W\n\n')
            
            for port_side in west_ports_sides:
                for port in port_side:
                    f.write(f'{port}\n')
        
            #f.write(f'Tile_X0Y0_FrameData\\[.*\\]\n')
            #f.write(f'Tile_X0Y1_FrameData\\[.*\\]\n')
    
    
        pins_dict = {'N': [], 'E': [], 'S': [], 'W': []}
    
        # TODO reverse?
        for port_side in reversed(north_ports_sides):
            pins_dict['N'].append(
                {
                    'min_distance': None,
                    'reverse_result': False,
                    'pins': port_side,
                    'sort_mode': 'bus_major'
                }
            )
        
        for port_side in reversed(east_ports_sides):
            pins_dict['E'].append(
                {
                    'min_distance': None,
                    'reverse_result': False,
                    'pins': port_side,
                    'sort_mode': 'bus_major'
                }
            )
        
        # TODO reverse?
        for port_side in reversed(south_ports_sides):
            pins_dict['S'].append(
                {
                    'min_distance': None,
                    'reverse_result': False,
                    'pins': port_side,
                    'sort_mode': 'bus_major'
                }
            )
        
        for port_side in reversed(west_ports_sides):
            pins_dict['W'].append(
                {
                    'min_distance': None,
                    'reverse_result': False,
                    'pins': port_side,
                    'sort_mode': 'bus_major'
                }
            )

    
        pin_file = os.path.join(self.run_dir, 'pins.yaml')
        with open(pin_file, 'w') as file:
            yaml.dump(pins_dict, file)
 
    
        self.config = self.config.copy(IO_PIN_ORDER_CFG=pin_file)

        info(self.run_dir)
        
        # Add models and custom cells
        #verilog_files.append('../../models_pack.v')
        #verilog_files.append('../../custom.v')

        # debug
        info(verilog_files)

        # Overwrite VERILOG_FILES config variable with our Verilog files
        self.config = self.config.copy(VERILOG_FILES=verilog_files)

        (final_state, steps) = super().run(initial_state, **kwargs)
        
        final_views_path = os.path.abspath(os.path.join(self.config["FABULOUS_TILE_DIR"], 'macro', self.config['PDK']))
        
        info(f'Saving final views for FABulous to {final_views_path}')
        
        final_state.save_snapshot(final_views_path)
        
        return (final_state, steps)
