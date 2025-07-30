#
# OpenDB script for custom Power for FABulous fabric
# This script places vertical PDN straps on top
# of already existing straps in order to tell OpenROAD
# that they should be considered connected and are pins
#
# Copyright (c) 2023 Sylvain Munaut <tnt@246tNt.com>
# Copyright (c) 2025 Leo Moser <leo.moser@pm.me>
# SPDX-License-Identifier: Apache-2.0
#

import os
import sys

import odb
import click
from reader import click_odb


@click.option("--width", default=0, type=float, help="Width of macro in um")
@click.option("--height", default=0, type=float, help="Height of macro in um")
@click.option("--halo_left", default=0, type=float, help="Halo left in um")
@click.option("--halo_bottom", default=0, type=float, help="Halo bottom in um")
@click.option("--halo_right", default=0, type=float, help="Halo right in um")
@click.option("--halo_top", default=0, type=float, help="Halo top in um")
@click.option("--voffset", default=0, type=float, help="PDN vertical offset")
@click.option("--vspacing", default=0, type=float, help="PDN vertical spacing")
@click.option("--vpitch", default=0, type=float, help="PDN vertical pitch")
@click.option("--vwidth", default=0, type=float, help="PDN vertical width")
@click.option(
    "--metal-layer-name",
    default=None,
    type=str,
    help="Metal layer for the vertical straps",
)
@click.option(
    "--core-voffset",
    default=None,
    type=float,
    help="Die are to core area vertical offset",
)
@click.option(
    "--core-hoffset",
    default=None,
    type=float,
    help="Die are to core area horizontal offset",
)
@click.option(
    "--tile-widths",
    default="",
    type=str,
    help="Tile widths of a row in the form: width;width;width",
)
@click.command()
@click_odb
def power(
    reader,
    width: float,
    height: float,
    halo_left: float,
    halo_bottom: float,
    halo_right: float,
    halo_top: float,
    voffset: float,
    vspacing: float,
    vpitch: float,
    vwidth: float,
    metal_layer_name: str,
    core_voffset: float,
    core_hoffset: float,
    tile_widths: str,
):

    macro_x_pos = 0

    tile_widths = [
        int(float(tile_width) * 1000) for tile_width in tile_widths.split(";")
    ]
    print(tile_widths)

    # Create ground / power nets
    tech = reader.db.getTech()

    print(f"metal_layer_name: {metal_layer_name}")
    metal_layer = tech.findLayer(metal_layer_name)

    for net_name, net_type in [("VPWR", "POWER"), ("VGND", "GROUND")]:
        net = reader.block.findNet(net_name)
        if net is None:
            # Create net
            net = odb.dbNet.create(reader.block, net_name)
            net.setSpecial()
            net.setSigType(net_type)

    vpwr_net = reader.block.findNet("VPWR")
    vgnd_net = reader.block.findNet("VGND")

    # Connect instance-iterms to power nets
    for blk_inst in reader.block.getInsts():
        print(f"Instance: {blk_inst.getName()}")
        for iterm in blk_inst.getITerms():
            iterm_name = iterm.getMTerm().getName()

            if iterm_name == "VPWR":
                print("Connecting VPWR")
                iterm.connect(vpwr_net)

            if iterm_name == "VGND":
                print("Connecting VGND")
                iterm.connect(vgnd_net)

    # vpwr_wire = vpwr_net.getSWires()[0]
    # vgnd_wire = vgnd_net.getSWires()[0]
    vpwr_wire = odb.dbSWire.create(vpwr_net, "ROUTED")
    vgnd_wire = odb.dbSWire.create(vgnd_net, "ROUTED")

    vpwr_bterm = odb.dbBTerm.create(vpwr_net, "VPWR")
    vpwr_bterm.setIoType("INOUT")
    vpwr_bterm.setSigType(vpwr_net.getSigType())
    vpwr_bterm.setSpecial()
    vpwr_bpin = odb.dbBPin_create(vpwr_bterm)

    vgnd_bterm = odb.dbBTerm.create(vgnd_net, "VGND")
    vgnd_bterm.setIoType("INOUT")
    vgnd_bterm.setSigType(vgnd_net.getSigType())
    vgnd_bterm.setSpecial()
    vgnd_bpin = odb.dbBPin_create(vgnd_bterm)

    width = int(width * 1000)
    height = int(height * 1000)
    halo_left = int(halo_left * 1000)
    halo_bottom = int(halo_bottom * 1000)
    halo_right = int(halo_right * 1000)
    halo_top = int(halo_top * 1000)
    voffset = int(voffset * 1000)
    vspacing = int(vspacing * 1000)
    vpitch = int(vpitch * 1000)
    vwidth = int(vwidth * 1000)
    core_voffset = int(core_voffset * 1000)
    core_hoffset = int(core_hoffset * 1000)

    ymin = halo_bottom
    ymax = height - halo_top

    print(f"ymin: {ymin}")
    print(f"ymax: {ymax}")

    print(f"halo_left: {halo_left}")
    print(f"halo_bottom: {halo_bottom}")
    print(f"halo_right: {halo_right}")
    print(f"halo_top: {halo_top}")

    print(f"voffset: {voffset}")
    print(f"vspacing: {vspacing}")
    print(f"vpitch: {vpitch}")
    print(f"vwidth: {vwidth}")
    print(f"core_voffset: {core_voffset}")
    print(f"core_hoffset: {core_hoffset}")

    cur_x = halo_left
    for tile_width in tile_widths:
        print(f"tile_width: {tile_width}")

        print(f"cur_x: {cur_x/1000}")

        cur_x_tile = 0
        cur_x_tile += voffset + core_voffset
        while cur_x_tile < (tile_width - core_voffset):

            # VPWR
            if (tile_width - core_voffset) - cur_x_tile > vwidth // 2:
                x_vpwr_left = cur_x + cur_x_tile - vwidth // 2
                x_vpwr_right = cur_x + cur_x_tile + vwidth // 2

                print(x_vpwr_left / 1000)
                print(x_vpwr_right / 1000)

                print(
                    f'{type(vpwr_wire)}, {type(metal_layer)}, {type(x_vpwr_left)}, {type(ymin)}, {type(x_vpwr_right)}, {type(ymax)}, {type("STRIPE")}'
                )
                print(
                    f'{vpwr_wire}, {metal_layer}, {x_vpwr_left}, {ymin}, {x_vpwr_right}, {ymax}, {"STRIPE"}'
                )

                odb.dbSBox_create(
                    vpwr_wire,
                    metal_layer,
                    x_vpwr_left,
                    ymin,
                    x_vpwr_right,
                    ymax,
                    "STRIPE",
                )
                odb.dbBox_create(
                    vpwr_bpin, metal_layer, x_vpwr_left, ymin, x_vpwr_right, ymax
                )

            cur_x_tile += vwidth + vspacing

            # VGND
            if (tile_width - core_voffset) - cur_x_tile > vwidth // 2:
                x_vgnd_left = cur_x + cur_x_tile - vwidth // 2
                x_vgnd_right = cur_x + cur_x_tile + vwidth // 2

                print(x_vgnd_left / 1000)
                print(x_vgnd_right / 1000)

                odb.dbSBox_create(
                    vgnd_wire,
                    metal_layer,
                    x_vgnd_left,
                    ymin,
                    x_vgnd_right,
                    ymax,
                    "STRIPE",
                )
                odb.dbBox_create(
                    vgnd_bpin, metal_layer, x_vgnd_left, ymin, x_vgnd_right, ymax
                )

            cur_x_tile += vpitch - vspacing - vwidth

        cur_x += tile_width

        print(f"cur_x: {cur_x/1000}")

    vpwr_bpin.setPlacementStatus("FIRM")
    vgnd_bpin.setPlacementStatus("FIRM")


if __name__ == "__main__":
    power()
