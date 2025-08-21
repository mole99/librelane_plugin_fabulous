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
import odb
import click
from reader import click_odb


@click.option(
    "--metal-layer-name",
    default=None,
    type=str,
    help="Metal layer for the power/ground straps",
)
@click.command()
@click_odb
def power(
    reader,
    metal_layer_name: str,
):
    # Create ground / power nets
    tech = reader.db.getTech()

    print(f"metal_layer_name: {metal_layer_name}")
    metal_layer = tech.findLayer(metal_layer_name)

    # Create nets, if they don't exist yet
    # TODO make this generic using VDD_NETS, GND_NETS
    for net_name, net_type in [("VPWR", "POWER"), ("VGND", "GROUND")]:
        net = reader.block.findNet(net_name)
        if net is None:
            # Create net
            net = odb.dbNet.create(reader.block, net_name)
            net.setSpecial()
            net.setSigType(net_type)

    vpwr_net = reader.block.findNet("VPWR")
    vgnd_net = reader.block.findNet("VGND")

    # Create wires
    # vpwr_wire = vpwr_net.getSWires()[0]
    # vgnd_wire = vgnd_net.getSWires()[0]
    vpwr_wire = odb.dbSWire.create(vpwr_net, "ROUTED")
    vgnd_wire = odb.dbSWire.create(vgnd_net, "ROUTED")

    # Create bterms (top-level)
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

    # Connect instance-iterms to power nets,
    # draw the wires and pins
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

        inst_master = blk_inst.getMaster()

        # Now, for each power/ground mterm (TODO: check signal type instead of name)
        # Copy the geomtry of the pins to wires and top-level pins
        for master_mterm in inst_master.getMTerms():
            if master_mterm.getName() == "VPWR" or master_mterm.getName() == "VGND":
                for mterm_mpins in master_mterm.getMPins():
                    for mpins_dbox in mterm_mpins.getGeometry():
                        if master_mterm.getName() == "VPWR":
                            odb.dbSBox_create(
                                vpwr_wire,
                                metal_layer,
                                blk_inst.getLocation()[0] + mpins_dbox.xMin(),
                                blk_inst.getLocation()[1] + mpins_dbox.yMin(),
                                blk_inst.getLocation()[0] + mpins_dbox.xMax(),
                                blk_inst.getLocation()[1] + mpins_dbox.yMax(),
                                "STRIPE",
                            )
                            odb.dbBox_create(
                                vpwr_bpin,
                                metal_layer,
                                blk_inst.getLocation()[0] + mpins_dbox.xMin(),
                                blk_inst.getLocation()[1] + mpins_dbox.yMin(),
                                blk_inst.getLocation()[0] + mpins_dbox.xMax(),
                                blk_inst.getLocation()[1] + mpins_dbox.yMax(),
                            )

                        if master_mterm.getName() == "VGND":
                            odb.dbSBox_create(
                                vgnd_wire,
                                metal_layer,
                                blk_inst.getLocation()[0] + mpins_dbox.xMin(),
                                blk_inst.getLocation()[1] + mpins_dbox.yMin(),
                                blk_inst.getLocation()[0] + mpins_dbox.xMax(),
                                blk_inst.getLocation()[1] + mpins_dbox.yMax(),
                                "STRIPE",
                            )
                            odb.dbBox_create(
                                vgnd_bpin,
                                metal_layer,
                                blk_inst.getLocation()[0] + mpins_dbox.xMin(),
                                blk_inst.getLocation()[1] + mpins_dbox.yMin(),
                                blk_inst.getLocation()[0] + mpins_dbox.xMax(),
                                blk_inst.getLocation()[1] + mpins_dbox.yMax(),
                            )

    vpwr_bpin.setPlacementStatus("FIRM")
    vgnd_bpin.setPlacementStatus("FIRM")


if __name__ == "__main__":
    power()
