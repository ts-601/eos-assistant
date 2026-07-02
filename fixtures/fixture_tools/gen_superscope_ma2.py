#!/usr/bin/env python3
"""
Generate grandMA2 XML profiles for Light Sky Super Scope series.

Fixtures:
  - Super Scope Color  : 600W RGBAL, CMY+CTO virtual, 35CH / 60CH
  - Super Scope II     : 520W White LED + CMY, 42CH / 54CH
  - Super Scope Pro    : 450W White LED + CMY, 33CH / 36CH
  - Super Scope Plus   : 880W White LED + CMY, 43CH / 55CH

All are 4-in-1 (beam/spot/wash/profile) moving head profile spots.
Pan 540°, Tilt 270°.
"""

import xml.etree.ElementTree as ET
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "MA2_Profiles", "LightSky")


def v8(val: int) -> str:
    """8-bit DMX value → MA2 string format."""
    return str(val * 65536)


MAX = "16777215"


# ─────────────────────────────────────────────────────────────
# XML helpers
# ─────────────────────────────────────────────────────────────

def _indent(elem, level=0):
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    if not elem.tail or not elem.tail.strip():
        elem.tail = indent if level else "\n"


def build_ma2(fixture_name: str, manufacturer: str, modes: dict[str, list]) -> ET.Element:
    """
    Build MA2 XML element.

    modes = {
        "42CH": [
            # (attribute, coarse_ch, fine_ch_or_None, name_or_None)
            ("PAN",    1, 2, None),
            ("TILT",   3, 4, None),
            ...
        ],
        "54CH": [ ... ],
    }
    Each fine_ch in a tuple refers to the DMX channel number that carries the fine 8 bits.
    Channels listed with fine_ch != None ARE fine channels – they are skipped as top-level
    ChannelType entries (the coarse ChannelType references them via `fine=`).
    """
    root = ET.Element("MA")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("majorVersion", "3")
    root.set("minorVersion", "9")

    ft = ET.SubElement(root, "FixtureType")
    ft.set("Name", fixture_name)
    ft.set("Manufacturer", manufacturer)
    ft.set("Type", "Movinglight")

    modules_el = ET.SubElement(ft, "Modules")

    for mode_name, channels in modes.items():
        module = ET.SubElement(modules_el, "Module")
        module.set("Name", mode_name)

        # Collect which channels are "fine" references so we can skip them
        fine_channels = set()
        for attr, coarse, fine, label in channels:
            if fine is not None:
                fine_channels.add(fine)

        for attr, coarse, fine, label in channels:
            if coarse in fine_channels:
                continue  # skip – referenced from its coarse partner
            ct = ET.SubElement(module, "ChannelType")
            ct.set("attribute", attr)
            ct.set("coarse", str(coarse))
            if fine is not None:
                ct.set("fine", str(fine))
            if label:
                ct.set("name", label)
            cf = ET.SubElement(ct, "ChannelFunction")
            cf.set("From", "0")
            cf.set("To", MAX)

    _indent(root)
    return root


def save(root: ET.Element, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    with open(path, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)
    print(f"  Saved: {path}")


# ═══════════════════════════════════════════════════════════════
# SUPER SCOPE COLOR  — 600W RGBAL, 4-in-1 Profile Spot
# Modes: 35CH (standard), 60CH (extended/16-bit)
# DMX source: Light Sky User Manual 2026
# ═══════════════════════════════════════════════════════════════
#
# Color system: Virtual CMY (3 channels) + Virtual CTO (CTC channel).
# Physically it's RGBAL but the fixture maps to virtual CMY internally
# through iCC calibration.  MA2 attributes: CYAN/MAGENTA/YELLOW/CTO.
#
# 35CH layout:
#  1  Pan              2  Pan Fine      → 16-bit PAN
#  3  Tilt             4  Tilt Fine     → 16-bit TILT
#  5  Speed            6  Functions(ctrl)
#  7  Colour functions  8  Virtual CW
#  9  Cyan            10  Magenta       11  Yellow
# 12  CTC             13  Effect        14  Effect Rotation
# 15  Gobo1           16  Gobo1 Rot     17  Gobo2  18  Gobo2 Rot
# 19  Prism           20  Prism Rot     21  Frost  22  Iris
# 23  Zoom            24  Focus
# 25  Frame Rot   26  Blade1A  27  Blade1B  28  Blade2A  29  Blade2B
# 30  Blade3A  31  Blade3B  32  Blade4A  33  Blade4B
# 34  Shutter/Strobe  35  Dimmer
#
# 60CH layout adds: fine channels for CMY, Iris, Zoom, Focus, DimmerFine
# Plus: Freq sel(7), Freq fine(8), Green correction(19), Colour mix(20),
#       Gobo speed(21), timing(22), effect animations(25), gobo2 fine(31/28)

SSC_35CH = [
    # attr,        coarse, fine, label
    ("PAN",          1,   2, None),
    ("PAN",          2, None, "Pan Fine"),      # fine – will be skipped
    ("TILT",         3,   4, None),
    ("TILT",         4, None, "Tilt Fine"),
    ("PTSPEED",      5, None, "Speed Pan/Tilt"),
    ("DUMMY",        6, None, "Functions"),
    ("DUMMY",        7, None, "Colour Functions"),
    ("CW1",          8, None, "Virtual Colour Wheel"),
    ("CYAN",         9, None, "Cyan/Red"),
    ("MAGENTA",     10, None, "Magenta/Green"),
    ("YELLOW",      11, None, "Yellow/Blue"),
    ("CTO",         12, None, "CTC"),
    ("EFFECTS",     13, None, "Effect Wheel"),
    ("EFFECTS",     14, None, "Effect Rotation"),
    ("GOBO1",       15, None, "Gobo Wheel 1"),
    ("GOBO1POS",    16, None, "Gobo 1 Rotation"),
    ("GOBO2",       17, None, "Gobo Wheel 2"),
    ("GOBO2POS",    18, None, "Gobo 2 Rotation"),
    ("PRISM1",      19, None, "Prism"),
    ("EFFECTS",     20, None, "Prism Rotation"),
    ("FROST1",      21, None, "Frost"),
    ("IRIS",        22, None, "Iris"),
    ("ZOOM",        23, None, "Zoom"),
    ("FOCUS",       24, None, "Focus"),
    ("EFFECTS",     25, None, "Frame Rotation"),
    ("DUMMY",       26, None, "Blade 1A"),
    ("DUMMY",       27, None, "Blade 1B Swivel"),
    ("DUMMY",       28, None, "Blade 2A"),
    ("DUMMY",       29, None, "Blade 2B Swivel"),
    ("DUMMY",       30, None, "Blade 3A"),
    ("DUMMY",       31, None, "Blade 3B Swivel"),
    ("DUMMY",       32, None, "Blade 4A"),
    ("DUMMY",       33, None, "Blade 4B Swivel"),
    ("SHUTTER",     34, None, "Shutter/Strobe"),
    ("DIM",         35, None, "Dimmer"),
]

SSC_60CH = [
    ("PAN",          1,   2, None),
    ("PAN",          2, None, "Pan Fine"),
    ("TILT",         3,   4, None),
    ("TILT",         4, None, "Tilt Fine"),
    ("PTSPEED",      5, None, "Speed Pan/Tilt"),
    ("DUMMY",        6, None, "Functions"),
    ("DUMMY",        7, None, "Freq Selection"),
    ("DUMMY",        8, None, "Freq Fine"),
    ("DUMMY",        9, None, "Colour Functions"),
    ("CW1",         10, None, "Virtual Colour Wheel"),
    ("DUMMY",       11, None, "Colour Wheel (49CH only)"),
    ("CYAN",        12,  13, "Cyan/Red"),
    ("CYAN",        13, None, "Cyan Fine"),
    ("MAGENTA",     14,  15, "Magenta/Green"),
    ("MAGENTA",     15, None, "Magenta Fine"),
    ("YELLOW",      16,  17, "Yellow/Blue"),
    ("YELLOW",      17, None, "Yellow Fine"),
    ("CTO",         18, None, "CTC"),
    ("DUMMY",       19, None, "Green Correction"),
    ("DUMMY",       20, None, "Colour Mix Control"),
    ("DUMMY",       21, None, "Gobo Speed"),
    ("DUMMY",       22, None, "Movement Timing"),
    ("EFFECTS",     23, None, "Effect Wheel"),
    ("EFFECTS",     24, None, "Effect Rotation"),
    ("DUMMY",       25, None, "Effect Animations"),
    ("GOBO1",       26, None, "Gobo Wheel 1"),
    ("GOBO1POS",    27,  28, "Gobo 1 Rotation"),
    ("GOBO1POS",    28, None, "Gobo 1 Fine"),
    ("GOBO2",       29, None, "Gobo Wheel 2"),
    ("GOBO2POS",    30, None, "Gobo 2 Rotation"),
    ("DUMMY",       31, None, "Gobo 2 Fine"),
    ("PRISM1",      32, None, "Prism"),
    ("EFFECTS",     33, None, "Prism Rotation"),
    ("FROST1",      34, None, "Frost"),
    ("IRIS",        35,  36, "Iris"),
    ("IRIS",        36, None, "Iris Fine"),
    ("ZOOM",        37,  38, "Zoom"),
    ("ZOOM",        38, None, "Zoom Fine"),
    ("FOCUS",       39,  40, "Focus"),
    ("FOCUS",       40, None, "Focus Fine"),
    ("EFFECTS",     41, None, "Frame Rotation"),
    ("DUMMY",       42, None, "Blade 1A"),
    ("DUMMY",       43, None, "Blade 1A Fine"),
    ("DUMMY",       44, None, "Blade 1B Swivel"),
    ("DUMMY",       45, None, "Blade 1B Fine"),
    ("DUMMY",       46, None, "Blade 2A"),
    ("DUMMY",       47, None, "Blade 2A Fine"),
    ("DUMMY",       48, None, "Blade 2B Swivel"),
    ("DUMMY",       49, None, "Blade 2B Fine"),
    ("DUMMY",       50, None, "Blade 3A"),
    ("DUMMY",       51, None, "Blade 3A Fine"),
    ("DUMMY",       52, None, "Blade 3B Swivel"),
    ("DUMMY",       53, None, "Blade 3B Fine"),
    ("DUMMY",       54, None, "Blade 4A"),
    ("DUMMY",       55, None, "Blade 4A Fine"),
    ("DUMMY",       56, None, "Blade 4B Swivel"),
    ("DUMMY",       57, None, "Blade 4B Fine"),
    ("SHUTTER",     58, None, "Shutter/Strobe"),
    ("DIM",         59,  60, "Dimmer"),
    ("DIM",         60, None, "Dimmer Fine"),
]

SSC_MODES = {"35CH": SSC_35CH, "60CH": SSC_60CH}


# ═══════════════════════════════════════════════════════════════
# SUPER SCOPE II  — 520W White LED + CMY, 4-in-1 Profile Spot
# Modes: 42CH (standard), 54CH (16-bit fine)
# DMX source: Light Sky User Channel PDF 0103, 2025
# ═══════════════════════════════════════════════════════════════
#
# Color system: CMY + CTO + Color wheel (6 colors+CRI+blank)
#
# 42CH layout:
#  1  Pan   2  PanFine   3  Tilt   4  TiltFine   5  Speed
#  6  Functions   7  Cyan   8  Magenta   9  Yellow
# 10  CTO  11  Colour Wheel
# 12  Gobo1  13  Gobo1 Rot  14  Gobo2  15  Gobo2 Rot
# 16  Blade1A  17  Blade1B  18  Blade2A  19  Blade2B
# 20  Blade3A  21  Blade3B  22  Blade4A  23  Blade4B
# 24  Frame Rot  25  Frame Macro  26  Frame Macro Zoom
# 27  Prism  28  Prism Rot  29  Effect  30  Effect Rot
# 31  Frost  32  Iris
# 33  Zoom  34  ZoomFine(16-bit)  35  Focus  36  FocusFine(16-bit)
# 37  Autofocus Dist  38  Autofocus Adj
# 39  Strobe  40  Dimmer  41  DimmerFine(16-bit)
# 42  Gobo Macro
#
# 54CH adds: Cyan Fine(8), Magenta Fine(10), Yellow Fine(12), CTO Fine(14)
# and Blade fine channels for each of the 8 blades → +12 channels extra

SSII_42CH = [
    ("PAN",      1,  2, None),
    ("PAN",      2, None, "Pan Fine"),
    ("TILT",     3,  4, None),
    ("TILT",     4, None, "Tilt Fine"),
    ("PTSPEED",  5, None, "Speed Pan/Tilt"),
    ("DUMMY",    6, None, "Functions"),
    ("CYAN",     7, None, "Cyan"),
    ("MAGENTA",  8, None, "Magenta"),
    ("YELLOW",   9, None, "Yellow"),
    ("CTO",     10, None, "CTO"),
    ("CW1",     11, None, "Colour Wheel"),
    ("GOBO1",   12, None, "Gobo Wheel 1"),
    ("GOBO1POS",13, None, "Gobo 1 Rotation"),
    ("GOBO2",   14, None, "Gobo Wheel 2"),
    ("GOBO2POS",15, None, "Gobo 2 Rotation"),
    ("DUMMY",   16, None, "Blade 1A"),
    ("DUMMY",   17, None, "Blade 1B"),
    ("DUMMY",   18, None, "Blade 2A"),
    ("DUMMY",   19, None, "Blade 2B"),
    ("DUMMY",   20, None, "Blade 3A"),
    ("DUMMY",   21, None, "Blade 3B"),
    ("DUMMY",   22, None, "Blade 4A"),
    ("DUMMY",   23, None, "Blade 4B"),
    ("EFFECTS", 24, None, "Frame Rotation"),
    ("DUMMY",   25, None, "Frame Macro"),
    ("DUMMY",   26, None, "Frame Macro Zoom"),
    ("PRISM1",  27, None, "Prism"),
    ("EFFECTS", 28, None, "Prism Rotation"),
    ("EFFECTS", 29, None, "Effect/Animation"),
    ("EFFECTS", 30, None, "Effect Rotation"),
    ("FROST1",  31, None, "Frost"),
    ("IRIS",    32, None, "Iris"),
    ("ZOOM",    33,  34, "Zoom"),
    ("ZOOM",    34, None, "Zoom Fine"),
    ("FOCUS",   35,  36, "Focus"),
    ("FOCUS",   36, None, "Focus Fine"),
    ("DUMMY",   37, None, "Autofocus Distance"),
    ("DUMMY",   38, None, "Autofocus Adjustment"),
    ("SHUTTER", 39, None, "Strobe"),
    ("DIM",     40,  41, "Dimmer"),
    ("DIM",     41, None, "Dimmer Fine"),
    ("DUMMY",   42, None, "Gobo Macro"),
]

SSII_54CH = [
    ("PAN",      1,  2, None),
    ("PAN",      2, None, "Pan Fine"),
    ("TILT",     3,  4, None),
    ("TILT",     4, None, "Tilt Fine"),
    ("PTSPEED",  5, None, "Speed Pan/Tilt"),
    ("DUMMY",    6, None, "Functions"),
    ("CYAN",     7,  8, "Cyan"),
    ("CYAN",     8, None, "Cyan Fine"),
    ("MAGENTA",  9, 10, "Magenta"),
    ("MAGENTA", 10, None, "Magenta Fine"),
    ("YELLOW",  11, 12, "Yellow"),
    ("YELLOW",  12, None, "Yellow Fine"),
    ("CTO",     13, 14, "CTO"),
    ("CTO",     14, None, "CTO Fine"),
    ("CW1",     15, None, "Colour Wheel"),
    ("GOBO1",   16, None, "Gobo Wheel 1"),
    ("GOBO1POS",17, None, "Gobo 1 Rotation"),
    ("GOBO2",   18, None, "Gobo Wheel 2"),
    ("GOBO2POS",19, None, "Gobo 2 Rotation"),
    ("DUMMY",   20, None, "Blade 1A"),
    ("DUMMY",   21, None, "Blade 1A Fine"),
    ("DUMMY",   22, None, "Blade 1B"),
    ("DUMMY",   23, None, "Blade 1B Fine"),
    ("DUMMY",   24, None, "Blade 2A"),
    ("DUMMY",   25, None, "Blade 2A Fine"),
    ("DUMMY",   26, None, "Blade 2B"),
    ("DUMMY",   27, None, "Blade 2B Fine"),
    ("DUMMY",   28, None, "Blade 3A"),
    ("DUMMY",   29, None, "Blade 3A Fine"),
    ("DUMMY",   30, None, "Blade 3B"),
    ("DUMMY",   31, None, "Blade 3B Fine"),
    ("DUMMY",   32, None, "Blade 4A"),
    ("DUMMY",   33, None, "Blade 4A Fine"),
    ("DUMMY",   34, None, "Blade 4B"),
    ("DUMMY",   35, None, "Blade 4B Fine"),
    ("EFFECTS", 36, None, "Frame Rotation"),
    ("DUMMY",   37, None, "Frame Macro"),
    ("DUMMY",   38, None, "Frame Macro Zoom"),
    ("PRISM1",  39, None, "Prism"),
    ("EFFECTS", 40, None, "Prism Rotation"),
    ("EFFECTS", 41, None, "Effect/Animation"),
    ("EFFECTS", 42, None, "Effect Rotation"),
    ("FROST1",  43, None, "Frost"),
    ("IRIS",    44, None, "Iris"),
    ("ZOOM",    45,  46, "Zoom"),
    ("ZOOM",    46, None, "Zoom Fine"),
    ("FOCUS",   47,  48, "Focus"),
    ("FOCUS",   48, None, "Focus Fine"),
    ("DUMMY",   49, None, "Autofocus Distance"),
    ("DUMMY",   50, None, "Autofocus Adjustment"),
    ("SHUTTER", 51, None, "Strobe"),
    ("DIM",     52,  53, "Dimmer"),
    ("DIM",     53, None, "Dimmer Fine"),
    ("DUMMY",   54, None, "Gobo Macro"),
]

SSII_MODES = {"42CH": SSII_42CH, "54CH": SSII_54CH}


# ═══════════════════════════════════════════════════════════════
# SUPER SCOPE PRO  — 450W White LED + CMY, 4-in-1 Profile Spot
# Modes: 33CH (standard), 36CH (16-bit zoom/focus + speed)
# DMX source: Light Sky User Channel PDF 0081, 2023
# ═══════════════════════════════════════════════════════════════
#
# Color system: CMY + CTO + Color wheel (5 colors+CRI+white)
# Gobo: 1 rotation gobo wheel (7 gobos) + 1 animation/CTO disc
# Framing: 4 blades × 2 positions each, ±45° rotation
# Effects: 4-facet prism, 1 frost, iris
#
# 33CH layout:
#  1  Pan   2  PanFine   3  Tilt   4  TiltFine  (no Speed in 33CH)
#  5  DeviceSet   6  Cyan   7  Magenta   8  Yellow
#  9  Virtual ColorWheel   10  RotGoboWheel   11  GoboRot
# 12  CTO   13  Animation Wheel
# 14  BladeA1  15  BladeA2  16  BladeB1  17  BladeB2
# 18  BladeC1  19  BladeC2  20  BladeD1  21  BladeD2
# 22  Frame Rotation   23  Iris   24  Prism+PrismRot
# 25  Frost   26  [Effect Macro]
# 27  Focus   28  Zoom
# 29  Strobe  30  Dimmer  31  DimmerFine(16-bit)
# 32  AutoFocus  33  AutoFocusFine
#
# 36CH adds:
#  - ch5 = Speed Pan/Tilt (new; others shift +1 for 33CH compat)
#  - ch29 = Focus Fine (makes Focus 16-bit)
#  - ch31 = Zoom Fine (makes Zoom 16-bit)

SSPR_33CH = [
    ("PAN",      1,  2, None),
    ("PAN",      2, None, "Pan Fine"),
    ("TILT",     3,  4, None),
    ("TILT",     4, None, "Tilt Fine"),
    ("DUMMY",    5, None, "DeviceSet/Functions"),
    ("CYAN",     6, None, "Cyan"),
    ("MAGENTA",  7, None, "Magenta"),
    ("YELLOW",   8, None, "Yellow"),
    ("CW1",      9, None, "Virtual Colour Wheel"),
    ("GOBO1",   10, None, "Gobo Wheel"),
    ("GOBO1POS",11, None, "Gobo Rotation"),
    ("CTO",     12, None, "CTO"),
    ("EFFECTS", 13, None, "Animation Wheel"),
    ("DUMMY",   14, None, "Blade A1"),
    ("DUMMY",   15, None, "Blade A2"),
    ("DUMMY",   16, None, "Blade B1"),
    ("DUMMY",   17, None, "Blade B2"),
    ("DUMMY",   18, None, "Blade C1"),
    ("DUMMY",   19, None, "Blade C2"),
    ("DUMMY",   20, None, "Blade D1"),
    ("DUMMY",   21, None, "Blade D2"),
    ("EFFECTS", 22, None, "Frame Rotation"),
    ("IRIS",    23, None, "Iris"),
    ("PRISM1",  24, None, "Prism"),
    ("FROST1",  25, None, "Frost"),
    ("EFFECTS", 26, None, "Effect Macro"),
    ("FOCUS",   27, None, "Focus"),
    ("ZOOM",    28, None, "Zoom"),
    ("SHUTTER", 29, None, "Strobe"),
    ("DIM",     30,  31, "Dimmer"),
    ("DIM",     31, None, "Dimmer Fine"),
    ("DUMMY",   32, None, "AutoFocus Distance"),
    ("DUMMY",   33, None, "AutoFocus Fine"),
]

SSPR_36CH = [
    ("PAN",      1,  2, None),
    ("PAN",      2, None, "Pan Fine"),
    ("TILT",     3,  4, None),
    ("TILT",     4, None, "Tilt Fine"),
    ("PTSPEED",  5, None, "Speed Pan/Tilt"),
    ("DUMMY",    6, None, "DeviceSet/Functions"),
    ("CYAN",     7, None, "Cyan"),
    ("MAGENTA",  8, None, "Magenta"),
    ("YELLOW",   9, None, "Yellow"),
    ("CW1",     10, None, "Virtual Colour Wheel"),
    ("GOBO1",   11, None, "Gobo Wheel"),
    ("GOBO1POS",12, None, "Gobo Rotation"),
    ("CTO",     13, None, "CTO"),
    ("EFFECTS", 14, None, "Animation Wheel"),
    ("DUMMY",   15, None, "Blade A1"),
    ("DUMMY",   16, None, "Blade A2"),
    ("DUMMY",   17, None, "Blade B1"),
    ("DUMMY",   18, None, "Blade B2"),
    ("DUMMY",   19, None, "Blade C1"),
    ("DUMMY",   20, None, "Blade C2"),
    ("DUMMY",   21, None, "Blade D1"),
    ("DUMMY",   22, None, "Blade D2"),
    ("EFFECTS", 23, None, "Frame Rotation"),
    ("IRIS",    24, None, "Iris"),
    ("PRISM1",  25, None, "Prism"),
    ("FROST1",  26, None, "Frost"),
    ("EFFECTS", 27, None, "Effect Macro"),
    ("FOCUS",   28,  29, "Focus"),
    ("FOCUS",   29, None, "Focus Fine"),
    ("ZOOM",    30,  31, "Zoom"),
    ("ZOOM",    31, None, "Zoom Fine"),
    ("SHUTTER", 32, None, "Strobe"),
    ("DIM",     33,  34, "Dimmer"),
    ("DIM",     34, None, "Dimmer Fine"),
    ("DUMMY",   35, None, "AutoFocus Distance"),
    ("DUMMY",   36, None, "AutoFocus Fine"),
]

SSPR_MODES = {"33CH": SSPR_33CH, "36CH": SSPR_36CH}


# ═══════════════════════════════════════════════════════════════
# SUPER SCOPE PLUS  — 880W White LED + CMY, 4-in-1 Profile Spot
# Modes: 43CH (standard), 55CH (16-bit fine for CMY/blades)
# DMX source: Light Sky User Channel PDF 0078, 2023
# ═══════════════════════════════════════════════════════════════
#
# Color system: CMY + CTO + Color wheel (5+CRI+blank)
# Gobo: 2 rotation gobo wheels (7 gobos each) + animation wheel
# Framing: 4 blades × 2 positions each, ±55° rotation
# Effects: 4-facet + 4-linear prism (dual), 2 frosts, iris
#
# 43CH layout:
#  1  Pan   2  PanFine   3  Tilt   4  TiltFine   5  Speed
#  6  Functions   7  Cyan   8  Magenta   9  Yellow
# 10  CTO  11  Colour Wheel
# 12  Gobo1  13  Gobo1 Rot  14  Gobo2  15  Gobo2 Rot
# 16  Blade1A  17  Blade1B  18  Blade2A  19  Blade2B
# 20  Blade3A  21  Blade3B  22  Blade4A  23  Blade4B
# 24  Frame Rot  25  Frame Macro  26  Frame Macro Zoom
# 27  Prism  28  Prism Rot  29  Effect  30  Effect Rot
# 31  Frost1  32  Frost2  33  Iris
# 34  Zoom  35  ZoomFine(16-bit)  36  Focus  37  FocusFine(16-bit)
# 38  Autofocus Dist  39  Autofocus Adj
# 40  Strobe  41  Dimmer  42  DimmerFine(16-bit)
# 43  Gobo Macro

SSPL_43CH = [
    ("PAN",      1,  2, None),
    ("PAN",      2, None, "Pan Fine"),
    ("TILT",     3,  4, None),
    ("TILT",     4, None, "Tilt Fine"),
    ("PTSPEED",  5, None, "Speed Pan/Tilt"),
    ("DUMMY",    6, None, "Functions"),
    ("CYAN",     7, None, "Cyan"),
    ("MAGENTA",  8, None, "Magenta"),
    ("YELLOW",   9, None, "Yellow"),
    ("CTO",     10, None, "CTO"),
    ("CW1",     11, None, "Colour Wheel"),
    ("GOBO1",   12, None, "Gobo Wheel 1"),
    ("GOBO1POS",13, None, "Gobo 1 Rotation"),
    ("GOBO2",   14, None, "Gobo Wheel 2"),
    ("GOBO2POS",15, None, "Gobo 2 Rotation"),
    ("DUMMY",   16, None, "Blade 1A"),
    ("DUMMY",   17, None, "Blade 1B"),
    ("DUMMY",   18, None, "Blade 2A"),
    ("DUMMY",   19, None, "Blade 2B"),
    ("DUMMY",   20, None, "Blade 3A"),
    ("DUMMY",   21, None, "Blade 3B"),
    ("DUMMY",   22, None, "Blade 4A"),
    ("DUMMY",   23, None, "Blade 4B"),
    ("EFFECTS", 24, None, "Frame Rotation"),
    ("DUMMY",   25, None, "Frame Macro"),
    ("DUMMY",   26, None, "Frame Macro Zoom"),
    ("PRISM1",  27, None, "Prism"),
    ("EFFECTS", 28, None, "Prism Rotation"),
    ("EFFECTS", 29, None, "Effect/Animation"),
    ("EFFECTS", 30, None, "Effect Rotation"),
    ("FROST1",  31, None, "Frost 1"),
    ("FROST2",  32, None, "Frost 2"),
    ("IRIS",    33, None, "Iris"),
    ("ZOOM",    34,  35, "Zoom"),
    ("ZOOM",    35, None, "Zoom Fine"),
    ("FOCUS",   36,  37, "Focus"),
    ("FOCUS",   37, None, "Focus Fine"),
    ("DUMMY",   38, None, "Autofocus Distance"),
    ("DUMMY",   39, None, "Autofocus Adjustment"),
    ("SHUTTER", 40, None, "Strobe"),
    ("DIM",     41,  42, "Dimmer"),
    ("DIM",     42, None, "Dimmer Fine"),
    ("DUMMY",   43, None, "Gobo Macro"),
]

# 55CH: adds Cyan Fine(8), Magenta Fine(10), Yellow Fine(12), CTO Fine(14),
# and Blade fine channels for each blade → +12 channels
SSPL_55CH = [
    ("PAN",      1,  2, None),
    ("PAN",      2, None, "Pan Fine"),
    ("TILT",     3,  4, None),
    ("TILT",     4, None, "Tilt Fine"),
    ("PTSPEED",  5, None, "Speed Pan/Tilt"),
    ("DUMMY",    6, None, "Functions"),
    ("CYAN",     7,  8, "Cyan"),
    ("CYAN",     8, None, "Cyan Fine"),
    ("MAGENTA",  9, 10, "Magenta"),
    ("MAGENTA", 10, None, "Magenta Fine"),
    ("YELLOW",  11, 12, "Yellow"),
    ("YELLOW",  12, None, "Yellow Fine"),
    ("CTO",     13, 14, "CTO"),
    ("CTO",     14, None, "CTO Fine"),
    ("CW1",     15, None, "Colour Wheel"),
    ("GOBO1",   16, None, "Gobo Wheel 1"),
    ("GOBO1POS",17, None, "Gobo 1 Rotation"),
    ("GOBO2",   18, None, "Gobo Wheel 2"),
    ("GOBO2POS",19, None, "Gobo 2 Rotation"),
    ("DUMMY",   20, None, "Blade 1A"),
    ("DUMMY",   21, None, "Blade 1A Fine"),
    ("DUMMY",   22, None, "Blade 1B"),
    ("DUMMY",   23, None, "Blade 1B Fine"),
    ("DUMMY",   24, None, "Blade 2A"),
    ("DUMMY",   25, None, "Blade 2A Fine"),
    ("DUMMY",   26, None, "Blade 2B"),
    ("DUMMY",   27, None, "Blade 2B Fine"),
    ("DUMMY",   28, None, "Blade 3A"),
    ("DUMMY",   29, None, "Blade 3A Fine"),
    ("DUMMY",   30, None, "Blade 3B"),
    ("DUMMY",   31, None, "Blade 3B Fine"),
    ("DUMMY",   32, None, "Blade 4A"),
    ("DUMMY",   33, None, "Blade 4A Fine"),
    ("DUMMY",   34, None, "Blade 4B"),
    ("DUMMY",   35, None, "Blade 4B Fine"),
    ("EFFECTS", 36, None, "Frame Rotation"),
    ("DUMMY",   37, None, "Frame Macro"),
    ("DUMMY",   38, None, "Frame Macro Zoom"),
    ("PRISM1",  39, None, "Prism"),
    ("EFFECTS", 40, None, "Prism Rotation"),
    ("EFFECTS", 41, None, "Effect/Animation"),
    ("EFFECTS", 42, None, "Effect Rotation"),
    ("FROST1",  43, None, "Frost 1"),
    ("FROST2",  44, None, "Frost 2"),
    ("IRIS",    45, None, "Iris"),
    ("ZOOM",    46,  47, "Zoom"),
    ("ZOOM",    47, None, "Zoom Fine"),
    ("FOCUS",   48,  49, "Focus"),
    ("FOCUS",   49, None, "Focus Fine"),
    ("DUMMY",   50, None, "Autofocus Distance"),
    ("DUMMY",   51, None, "Autofocus Adjustment"),
    ("SHUTTER", 52, None, "Strobe"),
    ("DIM",     53,  54, "Dimmer"),
    ("DIM",     54, None, "Dimmer Fine"),
    ("DUMMY",   55, None, "Gobo Macro"),
]

SSPL_MODES = {"43CH": SSPL_43CH, "55CH": SSPL_55CH}


# ─────────────────────────────────────────────────────────────
# Generate all profiles
# ─────────────────────────────────────────────────────────────

FIXTURES = [
    ("Super Scope Color",  "Light Sky", SSC_MODES,  "light_sky@super_scope_color"),
    ("Super Scope II",     "Light Sky", SSII_MODES, "light_sky@super_scope_ii"),
    ("Super Scope Pro",    "Light Sky", SSPR_MODES, "light_sky@super_scope_pro"),
    ("Super Scope Plus",   "Light Sky", SSPL_MODES, "light_sky@super_scope_plus"),
]


def main():
    print(f"Output directory: {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generated = []

    for fixture_name, mfr, modes, slug in FIXTURES:
        print(f"\n► {fixture_name}")
        root = build_ma2(fixture_name, mfr, modes)

        mode_str = "@".join(m.lower() for m in modes.keys())
        filename = f"{slug}@{mode_str}.xml"
        path = os.path.join(OUTPUT_DIR, filename)
        save(root, path)
        generated.append(path)

    print(f"\n✓ Generated {len(generated)} MA2 profile files.")
    return generated


if __name__ == "__main__":
    main()
