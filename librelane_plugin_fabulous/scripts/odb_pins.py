#
# OpenDB script for custom Power for FABulous fabric
# This script places vertical PDN straps on top
# of already existing straps in order to tell OpenROAD
# that they should be considered connected and are pins
#
# Copyright (c) 2026 Leo Moser <leo.moser@pm.me>
# SPDX-License-Identifier: Apache-2.0
#

import os
import odb
import click
from reader import click_odb


@click.command()
@click_odb
def pins(
    reader,
):
    tech = reader.db.getTech()
    chip = reader.db.getChip()
    block = chip.getBlock()
    insts = block.getInsts()

    for bterm in block.getBTerms():

        if bterm.getSigType() == "SIGNAL":

            bterm_bpin = odb.dbBPin_create(bterm)
            net = bterm.getNet()

            for iterm in net.getITerms():

                instance = iterm.getInst()
                location = instance.getLocation()

                for mpins in iterm.getMTerm().getMPins():
                    for dbbox in mpins.getGeometry():

                        layer = dbbox.getTechLayer()
                        xmin = dbbox.xMin()
                        ymin = dbbox.yMin()
                        xmax = dbbox.xMax()
                        ymax = dbbox.yMax()

                        odb.dbBox_create(
                            bterm_bpin,
                            layer,
                            location[0] + xmin,
                            location[1] + ymin,
                            location[0] + xmax,
                            location[1] + ymax,
                        )

            bterm_bpin.setPlacementStatus("FIRM")


if __name__ == "__main__":
    pins()
