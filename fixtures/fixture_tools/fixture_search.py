#!/usr/bin/env python3
"""
Fixture Search & MA2 Converter
Searches Open Fixture Library (OFL) and converts to grandMA2 XML profiles.

Usage:
  python fixture_search.py search "robe" "LEDWash"
  python fixture_search.py download "robe" "ledwash-600" output_dir/
  python fixture_search.py convert /path/to/ofl_fixture.json [output_dir/]

Sources checked:
  - Open Fixture Library (OFL): open-fixture-library.org  — 5000+ fixtures
  - Light Sky direct URLs: en.lightsky.com.cn (see LIGHTSKY_URLS below)

MA Share / GDTF Share require login — use their websites manually.
"""

import sys
import json
import os
import urllib.request
from xml.dom import minidom
import xml.etree.ElementTree as ET
from datetime import date

OFL_RAW = "https://raw.githubusercontent.com/OpenLightingProject/open-fixture-library/master"
OFL_WEB = "https://open-fixture-library.org"

# Known Light Sky MA2 direct download URLs (proxy-blocked, for manual download)
LIGHTSKY_URLS = {
    "super-scope-color": "https://en.lightsky.com.cn/wp-content/uploads/2026/06/MA2-4.rar",
    "super-scope-ii":    "https://en.lightsky.com.cn/wp-content/uploads/2025/04/0103-SUPER-SCOPE-II.rar",
    "super-scope-pro":   "https://en.lightsky.com.cn/wp-content/uploads/2023/11/light_sky@super_scope_pro@33ch@36.rar",
    "super-scope-plus":  "https://en.lightsky.com.cn/wp-content/uploads/2023/11/light_sky@super_scope_plus@42ch@54.rar",
}

CAPABILITY_TO_MA2 = {
    "Pan": "PAN", "Tilt": "TILT", "PanTiltSpeed": "PTSPEED",
    "Intensity": "DIM", "ShutterStrobe": "SHUTTER",
    "Zoom": "ZOOM", "Focus": "FOCUS",
    "ColorIntensity": None,  # resolved per color
    "ColorTemperature": "CTO",
    "WheelSlot": "CW1", "WheelRotation": "EFFECTS", "WheelShake": "EFFECTS",
    "Prism": "EFFECTS", "PrismRotation": "EFFECTS",
    "Frost": "FROST1", "FrostEffect": "FROST1",
    "Effect": "EFFECTS", "EffectParameter": "EFFECTS",
    "Maintenance": "DUMMY", "NoFunction": "DUMMY",
}

COLOR_TO_MA2 = {
    "Red": "R", "Green": "G", "Blue": "B", "White": "W",
    "Cyan": "CYAN", "Magenta": "MAGENTA", "Yellow": "YELLOW",
    "Amber": "AMBER", "UV": "UV", "Lime": "LIME",
    "Warm White": "W", "Cold White": "CW", "Indigo": "B",
}


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FixtureSearch/1.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"  [fetch error] {e}", file=sys.stderr)
        return None


def v8(val):
    return str(int(val) * 65536)

def d24(val8):
    return str(int(val8) * 65536)


def get_ma2_attr(cap_type, cap_data=None):
    if cap_type == "ColorIntensity" and cap_data:
        return COLOR_TO_MA2.get(cap_data.get("color", ""), "DUMMY")
    return CAPABILITY_TO_MA2.get(cap_type, "DUMMY")


def ofl_to_ma2(fixture_data, manufacturer_name="Unknown"):
    """Convert OFL fixture JSON dict → grandMA2 XML string."""
    fx_name = fixture_data.get("name", "Unknown")
    avail_ch = fixture_data.get("availableChannels", {})
    phys = fixture_data.get("physical", {})
    lens = phys.get("lens", {})
    beam_range = lens.get("degreesMinMax", [10, 40])
    intensity = str(phys.get("bulb", {}).get("lumens", 10000))

    cats = fixture_data.get("categories", [])
    fixture_class = "Moving" if "Moving Head" in cats else "Stick" if "LED Bar" in cats else "Other"
    beamtype = "Wash" if "Wash" in " ".join(cats) or "Color Changer" in cats else "Spot"

    MA_NS = "http://schemas.malighting.de/grandma2/xml/MA"
    root = ET.Element("MA", {
        "xmlns": MA_NS,
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": f"{MA_NS} http://schemas.malighting.de/grandma2/xml/3.x.x/MA.xsd",
        "major_vers": "3", "minor_vers": "9", "stream_vers": "2"
    })

    # Fine channel alias → coarse channel name
    fine_of = {}
    for ch_name, ch_data in avail_ch.items():
        for alias in ch_data.get("fineChannelAliases", []):
            fine_of[alias] = ch_name

    for mode in fixture_data.get("modes", []):
        mode_name = mode.get("shortName") or mode.get("name", "default")
        channels_list = mode.get("channels", [])

        ft = ET.SubElement(root, "FixtureType", name=fx_name, mode=mode_name)
        ii = ET.SubElement(ft, "InfoItems")
        ET.SubElement(ii, "Info", type="Revision",
                      date=str(date.today())).text = "Auto-converted from OFL"
        ET.SubElement(ft, "short_name").text = fx_name[:12]
        ET.SubElement(ft, "manufacturer").text = manufacturer_name
        ET.SubElement(ft, "short_manufacturer").text = manufacturer_name[:8]

        mods = ET.SubElement(ft, "Modules")
        mod = ET.SubElement(mods, "Module", name="Main Module", **{
            "class": fixture_class, "beamtype": beamtype,
            "beam_angle": str(beam_range[0]), "beam_intensity": intensity
        })

        for pos, ch_name in enumerate(channels_list, start=1):
            if ch_name is None:
                ct = ET.SubElement(mod, "ChannelType",
                                   attribute="DUMMY", feature="DUMMY", preset="DUMMY",
                                   coarse=str(pos))
                cf = ET.SubElement(ct, "ChannelFunction",
                                   **{"from":"0","to":"0","min_dmx_24":"0",
                                      "max_dmx_24":v8(255),"physfrom":"0","physto":"0",
                                      "subattribute":"DUMMY","attribute":"DUMMY",
                                      "feature":"DUMMY","preset":"DUMMY"})
                ET.SubElement(cf, "ChannelSet", name="Reserved",
                              **{"from_dmx":"0","to_dmx":v8(255)})
                continue

            if ch_name in fine_of:
                continue  # Fine channels are referenced via fine=N on coarse — skip as standalone

            coarse_idx = pos  # actual DMX address = position in channel list

            ch_data = avail_ch.get(ch_name, {})
            fine_aliases = ch_data.get("fineChannelAliases", [])
            fine_idx = None
            if fine_aliases:
                try:
                    fine_idx = channels_list.index(fine_aliases[0]) + 1
                except ValueError:
                    fine_idx = None

            caps = ch_data.get("capabilities", [])
            cap_single = ch_data.get("capability")
            all_types = set()
            if cap_single:
                all_types.add(cap_single.get("type", "NoFunction"))
            for cap in caps:
                all_types.add(cap.get("type", "NoFunction"))

            # Resolve MA2 attribute
            ma2_attr = "DUMMY"
            phys_from, phys_to = "0", "100"

            if "Pan" in all_types:
                ma2_attr = "PAN"
                if cap_single:
                    a0 = cap_single.get("angleStart","0deg").replace("deg","")
                    a1 = cap_single.get("angleEnd","540deg").replace("deg","")
                    try:
                        phys_from = str(float(a0)); phys_to = str(float(a1))
                    except: pass
            elif "Tilt" in all_types:
                ma2_attr = "TILT"
                if cap_single:
                    a0 = cap_single.get("angleStart","0deg").replace("deg","")
                    a1 = cap_single.get("angleEnd","270deg").replace("deg","")
                    try:
                        phys_from = str(float(a0)); phys_to = str(float(a1))
                    except: pass
            elif "Intensity" in all_types:
                ma2_attr = "DIM"; phys_from = "0"; phys_to = "100"
            elif "ShutterStrobe" in all_types:
                ma2_attr = "SHUTTER"
            elif "Zoom" in all_types:
                ma2_attr = "ZOOM"
                phys_from = str(beam_range[0]); phys_to = str(beam_range[1])
            elif "Focus" in all_types:
                ma2_attr = "FOCUS"
            elif "ColorIntensity" in all_types:
                for cap in (caps or ([cap_single] if cap_single else [])):
                    if cap and cap.get("type") == "ColorIntensity":
                        ma2_attr = get_ma2_attr("ColorIntensity", cap)
                        break
            elif "WheelSlot" in all_types:
                ma2_attr = "CW1"
            elif "PanTiltSpeed" in all_types:
                ma2_attr = "PTSPEED"
            elif "ColorTemperature" in all_types:
                ma2_attr = "CTO"
            elif "Frost" in all_types or "FrostEffect" in all_types:
                ma2_attr = "FROST1"
            elif all_types - {"NoFunction", "Maintenance"}:
                ma2_attr = "EFFECTS"

            ct_attrs = {
                "attribute": ma2_attr, "feature": ma2_attr, "preset": ma2_attr,
                "coarse": str(coarse_idx)
            }
            if fine_idx:
                ct_attrs["fine"] = str(fine_idx)
            if ma2_attr == "DIM":
                ct_attrs["highlight_value"] = v8(255)

            ct = ET.SubElement(mod, "ChannelType", **ct_attrs)
            max_24 = "16777215" if fine_idx else v8(255)

            if ma2_attr in ("PAN","TILT","DIM","ZOOM","FOCUS","PTSPEED",
                            "R","G","B","W","CYAN","MAGENTA","YELLOW","AMBER"):
                cf = ET.SubElement(ct, "ChannelFunction",
                                   **{"from":"0","to":"100","min_dmx_24":"0",
                                      "max_dmx_24":max_24,"physfrom":phys_from,
                                      "physto":phys_to,"subattribute":ma2_attr,
                                      "attribute":ma2_attr,"feature":ma2_attr,
                                      "preset":ma2_attr})
                if ma2_attr in ("PAN","TILT"):
                    ctr = str(int(int(max_24)//2))
                    ET.SubElement(cf,"ChannelSet",name="Center",
                                  **{"from_dmx":ctr,"to_dmx":ctr})
            elif ma2_attr == "SHUTTER":
                for cap in (caps or ([cap_single] if cap_single else [])):
                    if not cap: continue
                    lo, hi = cap.get("dmxRange", [0, 255])
                    eff = cap.get("shutterEffect", "Open")
                    sub = "STROBE" if "Strobe" in eff else "SHUTTER"
                    pf = "0"; pt = "0" if sub == "SHUTTER" else "100"
                    cf = ET.SubElement(ct, "ChannelFunction",
                                       **{"from":"0","to":"100",
                                          "min_dmx_24":d24(lo),"max_dmx_24":d24(hi),
                                          "physfrom":pf,"physto":pt,
                                          "subattribute":sub,"attribute":"SHUTTER",
                                          "feature":"SHUTTER","preset":"SHUTTER"})
                    lbl = (cap.get("comment") or eff)[:32]
                    ET.SubElement(cf,"ChannelSet",name=lbl,
                                  **{"from_dmx":d24(lo),"to_dmx":d24(hi)})
            elif ma2_attr == "CW1":
                for cap in (caps or ([cap_single] if cap_single else [])):
                    if not cap: continue
                    lo, hi = cap.get("dmxRange", [0, 255])
                    ct_type = cap.get("type","")
                    if ct_type == "WheelSlot":
                        lbl = f"Slot {cap.get('slotNumber','?')}"
                    elif ct_type == "WheelRotation":
                        lbl = "Rotation"
                    else:
                        lbl = ct_type
                    cf = ET.SubElement(ct, "ChannelFunction",
                                       **{"from":"0","to":"100",
                                          "min_dmx_24":d24(lo),"max_dmx_24":d24(hi),
                                          "physfrom":"0","physto":"100",
                                          "subattribute":"CW1","attribute":"CW1",
                                          "feature":"COLOR","preset":"COLOR"})
                    ET.SubElement(cf,"ChannelSet",name=lbl[:32],
                                  **{"from_dmx":d24(lo),"to_dmx":d24(hi)})
                if not caps and not cap_single:
                    cf = ET.SubElement(ct, "ChannelFunction",
                                       **{"from":"0","to":"100","min_dmx_24":"0",
                                          "max_dmx_24":v8(255),"physfrom":"0","physto":"100",
                                          "subattribute":"CW1","attribute":"CW1",
                                          "feature":"COLOR","preset":"COLOR"})
                    ET.SubElement(cf,"ChannelSet",name="Color Wheel",
                                  **{"from_dmx":"0","to_dmx":v8(255)})
            else:
                cf = ET.SubElement(ct, "ChannelFunction",
                                   **{"from":"0","to":"100","min_dmx_24":"0",
                                      "max_dmx_24":v8(255),"physfrom":"0","physto":"100",
                                      "subattribute":ma2_attr,"attribute":ma2_attr,
                                      "feature":ma2_attr,"preset":ma2_attr})
                ET.SubElement(cf,"ChannelSet",name=(ch_name or ma2_attr)[:32],
                              **{"from_dmx":"0","to_dmx":v8(255)})

            coarse_idx += 1

        insts = ET.SubElement(ft, "Instances")
        ET.SubElement(insts, "Instance", module_index="0", patch="1", locked="true")

    raw = ET.tostring(root, encoding="unicode")
    dom = minidom.parseString(raw)
    return dom.toprettyxml(indent="  ", encoding=None)


def cmd_search(args):
    if len(args) < 2:
        print("Usage: fixture_search.py search <manufacturer> <fixture_name>")
        return
    mfr, fix = args[0], args[1]
    mq, fq = mfr.lower(), fix.lower()

    print(f"Searching OFL: manufacturer='{mq}'  fixture='{fq}'")
    mfr_raw = fetch(f"{OFL_WEB}/api/v1/manufacturers")
    if not mfr_raw:
        print("ERROR: Could not reach OFL API"); return
    manufacturers = json.loads(mfr_raw)
    matched = [(k, v["name"]) for k, v in manufacturers.items()
               if mq in k.lower() or mq in v["name"].lower()]
    if not matched:
        print(f"No manufacturers matching '{mq}'")
        print("Sample available:", list(manufacturers.keys())[:20])
        return
    print(f"Manufacturers: {[m[1] for m in matched]}")

    results = []
    for mk, mn in matched:
        tree = fetch(f"https://api.github.com/repos/OpenLightingProject/open-fixture-library/contents/fixtures/{mk}")
        if not tree: continue
        entries = json.loads(tree)
        for e in entries:
            fname = e.get("name","")
            if not fname.endswith(".json"): continue
            fk = fname[:-5]
            if fq in fk.lower():
                results.append((mk, fk, mn))

    if not results:
        print(f"No fixtures matching '{fq}'"); return
    print(f"\n{len(results)} result(s):")
    for mk, fk, mn in results:
        print(f"  {mn}  /  {fk}")
        print(f"    Page:    {OFL_WEB}/{mk}/{fk}")
        print(f"    JSON:    {OFL_RAW}/fixtures/{mk}/{fk}.json")
        print(f"    Download: python fixture_search.py download {mk} {fk} ./")


def cmd_download(args):
    if len(args) < 3:
        print("Usage: fixture_search.py download <mfr_key> <fixture_key> <output_dir>")
        return
    mk, fk, out_dir = args[0], args[1], args[2]
    os.makedirs(out_dir, exist_ok=True)

    url = f"{OFL_RAW}/fixtures/{mk}/{fk}.json"
    print(f"Downloading {url}")
    raw = fetch(url)
    if not raw:
        print("Failed to download"); return
    data = json.loads(raw)

    mfr_raw = fetch(f"{OFL_WEB}/api/v1/manufacturers")
    mfr_name = mk
    if mfr_raw:
        mfrs = json.loads(mfr_raw)
        mfr_name = mfrs.get(mk, {}).get("name", mk)

    xml_str = ofl_to_ma2(data, mfr_name)
    out_path = os.path.join(out_dir, f"{mk}@{fk}.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_str)
    print(f"Saved: {out_path}")
    for mode in data.get("modes", []):
        chs = [c for c in mode.get("channels",[]) if c is not None]
        print(f"  Mode '{mode.get('shortName', mode.get('name'))}': {len(chs)} ch")


def cmd_convert(args):
    if not args:
        print("Usage: fixture_search.py convert <ofl.json> [output_dir]")
        return
    src = args[0]
    out_dir = args[1] if len(args) > 1 else os.path.dirname(src) or "."
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    xml_str = ofl_to_ma2(data)
    fname = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(out_dir, f"{fname}.xml")
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml_str)
    print(f"Saved: {out}")


def cmd_lightsky():
    """Print Light Sky MA2 direct download URLs."""
    print("\nLight Sky MA2 direct downloads (download manually — proxy blocked):")
    for name, url in LIGHTSKY_URLS.items():
        print(f"  {name}:")
        print(f"    {url}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1].lower()
    args = sys.argv[2:]
    if cmd == "search": cmd_search(args)
    elif cmd == "download": cmd_download(args)
    elif cmd == "convert": cmd_convert(args)
    elif cmd == "lightsky": cmd_lightsky()
    else:
        print(f"Unknown command: {cmd}\n"); print(__doc__)
