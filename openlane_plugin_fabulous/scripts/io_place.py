# Copyright 2020-2022 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from functools import partial
import odb

import os
import re
import sys
import yaml
import math
import click
import random
from decimal import Decimal

from reader import click_odb
import ioplace_parser

def grid_to_tracks(origin, count, step):
    tracks = []
    pos = origin
    for _ in range(count):
        tracks.append(pos)
        pos += step
    assert len(tracks) > 0
    tracks.sort()

    return tracks


def equally_spaced_sequence(side, side_pin_placement, possible_locations):
    virtual_pin_count = 0
    actual_pin_count = len(side_pin_placement)
    total_pin_count = actual_pin_count + virtual_pin_count
    for i in range(len(side_pin_placement)):
        if isinstance(
            side_pin_placement[i], int
        ):  # This is an int value indicating virtual pins
            virtual_pin_count = virtual_pin_count + side_pin_placement[i]
            actual_pin_count = (
                actual_pin_count - 1
            )  # Decrement actual pin count, this value was only there to indicate virtual pin count
            total_pin_count = actual_pin_count + virtual_pin_count
    result = []
    tracks = len(possible_locations)

    if total_pin_count > tracks:
        print(
            f"[ERROR] The {side} side of the floorplan doesn't have enough slots for all the pins: {total_pin_count} pins/{tracks} slots.",
            file=sys.stderr,
        )
        print(
            "[INFO] Try re-assigning pins to other sides or making the floorplan larger.",
            file=sys.stderr,
        )
        sys.exit(1)
    elif total_pin_count == tracks:
        return possible_locations, side_pin_placement  # All positions.
    elif total_pin_count == 0:
        return result, side_pin_placement

    # From this point, pin_count always < tracks.
    tracks_per_pin = math.floor(tracks / total_pin_count)  # >=1
    # O| | | O| | | O| | |
    # tracks_per_pin = 3
    # notice the last two tracks are unused
    # thus:
    used_tracks = tracks_per_pin * (total_pin_count - 1) + 1
    unused_tracks = tracks - used_tracks

    # Place the pins at those tracks...
    current_track = unused_tracks // 2  # So that the tracks used are centered
    starting_track_index = current_track
    if virtual_pin_count == 0:  # No virtual pins
        for _ in range(0, total_pin_count):
            result.append(possible_locations[current_track])
            current_track += tracks_per_pin
    else:  # There are virtual pins
        for i in range(len(side_pin_placement)):
            if not isinstance(side_pin_placement[i], int):  # We have an actual pin
                result.append(possible_locations[current_track])
                current_track += tracks_per_pin
            else:  # Virtual Pins, so just leave their needed spaces
                current_track += tracks_per_pin * side_pin_placement[i]
        side_pin_placement = [
            pin for pin in side_pin_placement if not isinstance(pin, int)
        ]  # Remove the virtual pins from the side_pin_placement list

    print(f"Placement details for the {side} side")
    print("Virtual pin count: ", virtual_pin_count)
    print("Actual pin count: ", actual_pin_count)
    print("Total pin count: ", total_pin_count)
    print("Tracks count: ", len(possible_locations))
    print("Tracks per pin: ", tracks_per_pin)
    print("Used tracks count: ", used_tracks)
    print("Unused track count: ", unused_tracks)
    print("Starting track index: ", starting_track_index)

    VISUALIZE_PLACEMENT = False
    if VISUALIZE_PLACEMENT:
        print("Placement Map:")
        print("[", end="")
        used_track_indices = []
        for i, location in enumerate(possible_locations):
            if location in result:
                print(f"\033[91m{location}\033[0m, ", end="")
                used_track_indices.append(i)
            else:
                print(f"{location}, ", end="")
        print("]")
        print(f"Indices of used tracks: {used_track_indices}")
        print("---")

    return result, side_pin_placement


identifiers = re.compile(r"\b[A-Za-z_][A-Za-z_0-9]*\b")
standalone_numbers = re.compile(r"\b\d+\b")
trash = re.compile(r"^[^\w\d]+$")


def sorter(bterm, order: ioplace_parser.Order):
    text: str = bterm.getName()
    keys = []
    priority_keys = []
    # tokenize and add to key
    while trash.match(text) is None:
        if match := identifiers.search(text):
            bus = match[0]
            start, end = match.span(0)
            if order == ioplace_parser.Order.busMajor:
                priority_keys.append(bus)
            else:
                keys.append(bus)
            text = text[:start] + text[end + 1 :]
        elif match := standalone_numbers.search(text):
            index = int(match[0])
            if order == ioplace_parser.Order.bitMajor:
                priority_keys.append(index)
            else:
                keys.append(index)
            text = text[: match.pos] + text[match.endpos + 1 :]
        else:
            break
    return [priority_keys, keys]


@click.command()
@click.option(
    "-u",
    "--unmatched-error",
    type=click.Choice(["none", "unmatched_design", "unmatched_cfg", "both"]),
    default=True,
    help="Treat unmatched pins as error",
)
@click.option(
    "-c",
    "--config",
    required=True,
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    help="Input configuration file",
)
@click.option(
    "-v",
    "--ver-length",
    default=None,
    type=float,
    help="Length for pins with N/S orientations in microns.",
)
@click.option(
    "-h",
    "--hor-length",
    default=None,
    type=float,
    help="Length for pins with E/S orientations in microns.",
)
@click.option(
    "-V",
    "--ver-layer",
    required=True,
    help="Name of metal layer to place vertical pins on.",
)
@click.option(
    "-H",
    "--hor-layer",
    required=True,
    help="Name of metal layer to place horizontal pins on.",
)
@click.option(
    "--hor-extension",
    default=0,
    type=float,
    help="Extension for vertical pins in microns.",
)
@click.option(
    "--ver-extension",
    default=0,
    type=float,
    help="Extension for horizontal pins in microns.",
)
@click.option(
    "--ver-width-mult", default=2, type=float, help="Multiplier for vertical pins."
)
@click.option(
    "--hor-width-mult", default=2, type=float, help="Multiplier for horizontal pins."
)
@click_odb
def io_place(
    reader,
    config,
    ver_layer,
    hor_layer,
    ver_width_mult,
    hor_width_mult,
    hor_length,
    ver_length,
    hor_extension,
    ver_extension,
    unmatched_error,
):
    """
    Places the IOs in an input def with an optional config file that supports regexes.

    Config format:
    #N|#S|#E|#W
    pin1_regex (low co-ordinates to high co-ordinates; e.g., bottom to top and left to right)
    pin2_regex
    ...

    #S|#N|#E|#W
    """
    config_file_name = config
    micron_in_units = reader.dbunits

    H_EXTENSION = int(micron_in_units * hor_extension)
    V_EXTENSION = int(micron_in_units * ver_extension)

    if H_EXTENSION < 0:
        H_EXTENSION = 0

    if V_EXTENSION < 0:
        V_EXTENSION = 0

    H_LAYER = reader.tech.findLayer(hor_layer)
    V_LAYER = reader.tech.findLayer(ver_layer)

    H_WIDTH = int(Decimal(hor_width_mult) * H_LAYER.getWidth())
    V_WIDTH = int(Decimal(ver_width_mult) * V_LAYER.getWidth())

    if hor_length is not None:
        H_LENGTH = int(micron_in_units * hor_length)
    else:
        H_LENGTH = max(
            int(
                math.ceil(
                    H_LAYER.getArea() * micron_in_units * micron_in_units / H_WIDTH
                )
            ),
            H_WIDTH,
        )

    if ver_length is not None:
        V_LENGTH = int(micron_in_units * ver_length)
    else:
        V_LENGTH = max(
            int(
                math.ceil(
                    V_LAYER.getArea() * micron_in_units * micron_in_units / V_WIDTH
                )
            ),
            V_WIDTH,
        )

    # read config + calculate minima
    config_file_str = open(config_file_name, "r", encoding="utf8").read()

    """ TODO we are using our own custom "parser"
    try:
        info_by_side = ioplace_parser.parse(config_file_str)
        print(info_by_side)
    except ValueError as e:
        print(f"An exception occurred: {e}")
        exit(os.EX_DATAERR)
    """
    
    with open(config_file_name, 'r', encoding="utf8") as file:
        config_data = yaml.safe_load(file)
    
    
    # INFO: I changed info_by_side to have a list of Side objects
    # This is necessary for supertiles where there are multiple segments
    info_by_side = {
        'N': [],
        'E': [],
        'S': [],
        'W': [],
    }
    
    for side, segments in config_data.items():
        for segment in segments:
        
            if segment['sort_mode'] == 'bus_major':
                sort_mode = ioplace_parser.Order.busMajor
            elif segment['sort_mode'] == 'bus_minor':
                sort_mode = ioplace_parser.Order.busMinor
            else:
                print(f'Error: Unknown sort mode {segment["sort_mode"]}')
        
            info_by_side[side].append(
                ioplace_parser.Side(
                    min_distance = segment['min_distance'],
                    reverse_result = segment['reverse_result'],
                    pins = segment['pins'],
                    sort_mode = sort_mode
                )
            )
    
    print(f'info_by_side: {info_by_side}')
    

    print("Top-level design name:", reader.name)

    bterms = [
        bterm
        for bterm in reader.block.getBTerms()
        if bterm.getSigType() not in ["POWER", "GROUND"]
    ]

    for side, segments in info_by_side.items():
        for side_info in segments:
            min = (
                (V_WIDTH + V_LAYER.getSpacing())
                if side in ["N", "S"]
                else (H_WIDTH + H_LAYER.getSpacing())
            ) / reader.dbunits
            if side_info.min_distance is None:
                side_info.min_distance = min
            if side_info.min_distance < min:
                print(
                    f"[WARNING] Overriding minimum distance {side_info.min_distance} with {min} for pins on side {side} to avoid overlap.",
                    file=sys.stderr,
                )
                side_info.min_distance = min

    # build a list of pins
    pin_placement = {"N": [], "E": [], "W": [], "S": []}

    regex_by_bterm = {}
    unmatched_regexes = set()
    for side, segments in info_by_side.items():
        for segment_n, side_info in enumerate(segments):

            pin_placement_segment = []
        
            for pin in side_info.pins:
                if isinstance(pin, int):  # Virtual pins
                    pin_placement[side].append(pin)
                    continue

                anchored_regex = f"^{pin}$"  # anchor
                matched = False
                collected = []
                for bterm in bterms:
                    pin_name = bterm.getName()
                    if re.match(anchored_regex, pin_name) is None:
                        continue
                    if bterm in regex_by_bterm:
                        print(
                            f"[ERROR] Multiple regexes matched {pin_name}. Those are {regex_by_bterm[bterm]} and {pin}",
                            file=sys.stderr,
                        )
                        sys.exit(os.EX_DATAERR)
                    regex_by_bterm[bterm] = pin
                    collected.append(bterm)
                    matched = True
                collected.sort(key=partial(sorter, order=side_info.sort_mode))
                pin_placement_segment += collected
                if not matched:
                    unmatched_regexes.add(pin)
            
            pin_placement[side].append(pin_placement_segment)

    print(f'pin_placement: {pin_placement}')

    # check for extra or missing pins
    not_in_design = unmatched_regexes
    not_in_config = set(
        [bterm.getName() for bterm in bterms if bterm not in regex_by_bterm]
    )
    mismatches_found = False
    for is_in, not_in, pins in [
        ("config", "design", not_in_design),
        ("design", "config", not_in_config),
    ]:
        for name in pins:
            if (
                is_in == "config"
                and (unmatched_error in {"unmatched_cfg", "both"})
                or is_in == "design"
                and (unmatched_error in {"unmatched_design", "both"})
            ):
                mismatches_found = True
                print(
                    f"[ERROR] {name} not found in {not_in} but found in {is_in}.",
                    file=sys.stderr,
                )
            else:
                print(
                    f"[WARNING] {name} not found in {not_in} but found in {is_in}.",
                    file=sys.stderr,
                )

    if mismatches_found:
        print("Critical mismatches found.")
        exit(os.EX_DATAERR)

    if len(not_in_config) > 0:
        print("Assigning random sides to unmatched pins…")
        for bterm in not_in_config:
            random_side = random.choice(list(pin_placement.keys()))
            
            num_segments = len(random_side)
            random_segment = random.randint(0, num_segments-1)
            
            pin_placement[random_side][random_segment].append(bterm)

    # generate slots
    DIE_AREA = reader.block.getDieArea()
    BLOCK_LL_X = DIE_AREA.xMin()
    BLOCK_LL_Y = DIE_AREA.yMin()
    BLOCK_UR_X = DIE_AREA.xMax()
    BLOCK_UR_Y = DIE_AREA.yMax()

    print("Block boundaries:", BLOCK_LL_X, BLOCK_LL_Y, BLOCK_UR_X, BLOCK_UR_Y)

    # H-tracks

    origin, count, h_step = reader.block.findTrackGrid(H_LAYER).getGridPatternY(0)
    print(f"Horizontal Tracks Origin: {origin}, Count: {count}, Step: {h_step}")
    
    h_tracks_E = []
    
    for segments_n, _ in enumerate(pin_placement['E']):
    
        if count % len(pin_placement['E']) != 0:
            print(f"Error: Number of pins {count} can't be divided by {len(pin_placement['E'])}")
    
        h_tracks_E.append(grid_to_tracks(origin + int((DIE_AREA.yMax() - DIE_AREA.yMin()) * segments_n / len(pin_placement['E'])), count // len(pin_placement['E']), h_step))

    h_tracks_W = []

    for segments_n, _ in enumerate(pin_placement['W']):
    
        if count % len(pin_placement['W']) != 0:
            print(f"Error: Number of pins {count} can't be divided by {len(pin_placement['W'])}")
    
        h_tracks_W.append(grid_to_tracks(origin + int((DIE_AREA.yMax() - DIE_AREA.yMin()) * segments_n / len(pin_placement['W'])), count // len(pin_placement['W']), h_step))

    # V-tracks

    origin, count, v_step = reader.block.findTrackGrid(V_LAYER).getGridPatternX(0)
    print(f"Vertical Tracks Origin: {origin}, Count: {count}, Step: {v_step}")
    
    v_tracks_N = []
    
    for segments_n, _ in enumerate(pin_placement['N']):
    
        if count % len(pin_placement['N']) != 0:
            print(f"Error: Number of pins {count} can't be divided by {len(pin_placement['N'])}")
    
        v_tracks_N.append(grid_to_tracks(origin + int((DIE_AREA.xMax() - DIE_AREA.xMin()) * segments_n / len(pin_placement['N'])), count // len(pin_placement['N']), v_step))

    v_tracks_S = []

    for segments_n, _ in enumerate(pin_placement['S']):
    
        if count % len(pin_placement['S']) != 0:
            print(f"Error: Number of pins {count} can't be divided by {len(pin_placement['S'])}")
    
        v_tracks_S.append(grid_to_tracks(origin + int((DIE_AREA.xMax() - DIE_AREA.xMin()) * segments_n / len(pin_placement['S'])), count // len(pin_placement['S']), v_step))


    """
    print(len(h_tracks[0:len(h_tracks)//2]))
    print(len(h_tracks[len(h_tracks)//2:]))
    
    print(h_tracks[0:len(h_tracks)//2][0])
    print(h_tracks[0:len(h_tracks)//2][-1])
    
    print(h_tracks[len(h_tracks)//2:][0])
    print(h_tracks[len(h_tracks)//2:][-1])
    
    
    origin, count, h_step = reader.block.findTrackGrid(H_LAYER).getGridPatternY(0)
    h_tracks_0 = grid_to_tracks(origin, count//2, h_step)
    h_tracks_1 = grid_to_tracks(origin + (DIE_AREA.xMax() - DIE_AREA.xMin())//2, count//2, h_step)

    print(h_tracks_0)
    print(h_tracks_1)

    print(len(h_tracks_0))
    print(len(h_tracks_1))

    origin, count, v_step = reader.block.findTrackGrid(V_LAYER).getGridPatternX(0)
    v_tracks_0 = grid_to_tracks(origin, count//2, v_step)
    v_tracks_1 = grid_to_tracks(origin + (DIE_AREA.yMax() - DIE_AREA.yMin())//2, count//2, v_step)

    print(v_tracks_0)
    print(v_tracks_1)

    print(len(v_tracks_0))
    print(len(v_tracks_1))
    """

    pin_tracks = {"N": [], "E": [], "W": [], "S": []}
    for side, segments in pin_placement.items():
    
        for segment_n, segment in enumerate(segments):
            min_distance = info_by_side[side][segment_n].min_distance * micron_in_units

            print(side)
            #print(len(h_tracks[segment_n]))

            if side == "N":
                pin_tracks[side].append([
                    v_tracks_N[segment_n][i]
                    for i in range(len(v_tracks_N[segment_n]))
                    if (i % (math.ceil(min_distance / v_step))) == 0
                ])
            if side == "S":
                pin_tracks[side].append([
                    v_tracks_S[segment_n][i]
                    for i in range(len(v_tracks_S[segment_n]))
                    if (i % (math.ceil(min_distance / v_step))) == 0
                ])

            elif side == 'E':
                pin_tracks[side].append([
                    h_tracks_E[segment_n][i]
                    for i in range(len(h_tracks_E[segment_n]))
                    if (i % (math.ceil(min_distance / h_step))) == 0
                ])
            elif side == 'W':
                pin_tracks[side].append([
                    h_tracks_W[segment_n][i]
                    for i in range(len(h_tracks_W[segment_n]))
                    if (i % (math.ceil(min_distance / h_step))) == 0
                ])
    
    print(pin_tracks)

    # reversals (including randomly-assigned pins, if needed)
    for side, segments in info_by_side.items():
        for segment_n, side_info in enumerate(segments):
            if side_info.reverse_result:
                pin_placement[side][segment_n].reverse()

    # create the pins
    for side, segments in pin_placement.items():
    
        for segment_n, segment in enumerate(segments):
        
            print(side)
            print(pin_placement[side][segment_n])
            print(pin_tracks[side][segment_n])
        
            slots, pin_placement[side][segment_n] = equally_spaced_sequence(
                side, pin_placement[side][segment_n], pin_tracks[side][segment_n]
            )
            
            print(slots)

            assert len(slots) == len(pin_placement[side][segment_n])

            for i in range(len(pin_placement[side][segment_n])):
                bterm = pin_placement[side][segment_n][i]
                slot = slots[i]
                print(slot)
                pin_name = bterm.getName()
                pins = bterm.getBPins()
                if len(pins) > 0:
                    print(
                        f"[WARNING] {pin_name} already has shapes. The shapes will be modified.",
                        file=sys.stderr,
                    )
                    assert len(pins) == 1
                    pin_bpin = pins[0]
                else:
                    pin_bpin = odb.dbBPin_create(bterm)

                pin_bpin.setPlacementStatus("PLACED")

                if side in ["N", "S"]:
                
                    offset = int((DIE_AREA.xMax() - DIE_AREA.xMin()) * segments_n / len(pin_placement['N']))

                    rect = odb.Rect(0, 0, V_WIDTH, V_LENGTH + V_EXTENSION)
                    if side == "N":
                        y = BLOCK_UR_Y - V_LENGTH
                    else:
                        y = BLOCK_LL_Y - V_EXTENSION
                    rect.moveTo(slot - V_WIDTH // 2, y)
                    odb.dbBox_create(pin_bpin, V_LAYER, *rect.ll(), *rect.ur())
                else:
                
                    offset = int((DIE_AREA.yMax() - DIE_AREA.yMin()) * segments_n / len(pin_placement['E']))

                    rect = odb.Rect(0, 0, H_LENGTH + H_EXTENSION, H_WIDTH)
                    if side == "E":
                        x = BLOCK_UR_X - H_LENGTH
                    else:
                        x = BLOCK_LL_X - H_EXTENSION
                    rect.moveTo(x, slot - H_WIDTH // 2)
                    odb.dbBox_create(pin_bpin, H_LAYER, *rect.ll(), *rect.ur())

if __name__ == "__main__":
    io_place()
