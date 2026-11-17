"""Project footprints with the thermal vias of each exposed pad built in, and paste windows clear of every drill.

User decision 2026-11-16 (docs/requirements.md s9, "Thermal vias in exposed pads"): no filled / capped vias; the paste
is split into windows that avoid the holes. For each part below this script
  1. copies its JLC footprint (hw/JLCImport.pretty),
  2. adds one plated through-hole pad per thermal via, numbered like the exposed pad (so it joins the pad's net and the
     planes connect to it solidly: router zones are solid=True), at the board positions the router used to place
     in_pad vias (VIAS below, absolute board mm; converted to footprint-local mm through tools/place.json),
  3. takes F.Paste off the exposed pad and gives it paste-only windows, one per cell of the grid the via rows and
     columns cut the pad into,
  4. runs kicad-skills paste_clear.py, which cuts every window clear of the drills (0.05 mm) and prints the paste
     coverage of the pad (PROBLEM under 30 %),
and writes hw/usb-hub.pretty/<JLC name>_ThermalVias.kicad_mod. tools/gen_sch.py points the symbols at them (FP_OVERRIDE).
Run: python3 tools/thermal_fp.py   (from anywhere; tools/build.sh runs it before the schematic)"""
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kskills  # noqa: E402  (pins kicad-skills; must come first)
from kicad_sexpr import Node, Sym, load, save  # noqa: E402
from kicad_sexpr.board import fp_item_key  # noqa: E402
from kicad_sexpr.common import Uuids  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, 'hw')
OUT_LIB = os.path.join(HW, 'usb-hub.pretty')
TMP = os.path.join(ROOT, 'build', 'thermal_fp')
ORIGIN = (100.0, 100.0)                       # tools/build.sh new_board.py --origin
PLACE = json.load(open(os.path.join(ROOT, 'tools', 'place.json')))

SV = (0.45, 0.2)    # small via (TPS25730 / ESTVS2200 class), same as tools/route_plan.py
PV = (0.6, 0.3)     # power via
GAP = 0.2           # paste-free gap between neighbouring windows (mm)
# smaller pads / tighter grids get a smaller gap so their coverage stays near 40-60 % (0.2 mm: D1 25 %, U1 33 %, U30 39 %)
GAP_PART = {'D1': 0.05, 'U1': 0.1, 'U30': 0.1}


def grid(x0, y0, x1, y1, pitch):
    """the points router.via_field(x0, y0, x1, y1, pitch) visits, row by row"""
    pts, y = [], y0
    while y <= y1 + 1e-6:
        x = x0
        while x <= x1 + 1e-6:
            pts.append((round(x, 4), round(y, 4)))
            x += pitch
        y += pitch
    return pts


# ref: (JLC footprint, exposed pad number, via (size, drill), via centres in board mm)
PARTS = {
    'D1': ('ESTVS2200DRVR', '7', SV, grid(164.6, 110.6, 165.4, 110.6, 0.8)),
    'U1': ('TPS25730DREFR', '39', PV, grid(153.1, 112.335, 154.9, 114.135, 0.9)),
    'Q30': ('CSD17505Q5A', '9', PV, grid(144.7, 122.2, 148.3, 124.6, 1.2)),
    'U30': ('LM5148RGYR', '25', PV, grid(154.0, 132.1, 156.0, 133.1, 1.0)),
    'U4': ('USB2517-JZX', '65', PV, grid(126.5, 155.5, 129.5, 158.5, 1.0)),
    'U5': ('USB2514B-AEZC-TR', '37', PV, grid(157.0, 156.0, 159.0, 158.0, 1.0)),
}


def to_local(ref, pt):
    """board mm -> footprint-local mm for the part's placement in tools/place.json (top side)"""
    x, y, rot = PLACE[ref]
    dx, dy = pt[0] - (ORIGIN[0] + x), pt[1] - (ORIGIN[1] + y)
    a = math.radians(rot or 0)
    # KiCad: board = pos + (lx cos a + ly sin a, -lx sin a + ly cos a)
    return (round(dx * math.cos(a) - dy * math.sin(a), 4), round(dx * math.sin(a) + dy * math.cos(a), 4))


def pad_rect(p):
    at, size = p.need('at'), p.need('size')
    x, y, rot = at.number(1), at.number(2), at.number(3, 0.0)
    w, h = size.number(1), size.number(2)
    assert rot % 90 == 0, 'exposed pad rotated off 90 degrees'
    if rot % 180:
        w, h = h, w
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def build(ref):
    name, ep_num, (size, drill), vias = PARTS[ref]
    fp = load(os.path.join(HW, 'JLCImport.pretty', name + '.kicad_mod'))
    out_name = name + '_ThermalVias'
    fp[1] = out_name
    eps = [p for p in fp.nodes('pad') if str(p[1]) == ep_num]
    assert len(eps) == 1, '%s: %d pads numbered %s' % (name, len(eps), ep_num)
    ep = eps[0]
    r = pad_rect(ep)
    lay = [str(v) for v in ep.need('layers')[1:]]
    assert 'F.Paste' in lay, '%s pad %s has no paste to split' % (name, ep_num)
    ep.need('layers')[1:] = [L for L in lay if L != 'F.Paste']
    local = [to_local(ref, v) for v in vias]
    for lx, ly in local:
        # every via well inside the exposed pad copper, or the placement / grid is not the one this was derived for
        assert r[0] + size / 2 <= lx + 1e-6 and lx <= r[2] - size / 2 + 1e-6 and \
            r[1] + size / 2 <= ly + 1e-6 and ly <= r[3] - size / 2 + 1e-6, \
            '%s: via at local (%g, %g) not inside pad %s %s' % (ref, lx, ly, ep_num, r)
    u = Uuids(seed='kicad_mod:' + out_name)
    u.scan(fp)
    new = []
    for lx, ly in local:
        new.append(Node('pad', ep_num, Sym('thru_hole'), Sym('circle'), Node('at', lx, ly), Node('size', size, size),
                        Node('drill', drill), Node('layers', '*.Cu'), Node('remove_unused_layers', False)))
    xs = sorted({r[0], r[2], *(p[0] for p in local)})
    ys = sorted({r[1], r[3], *(p[1] for p in local)})
    for x0, x1 in zip(xs, xs[1:]):
        for y0, y1 in zip(ys, ys[1:]):
            # windows inset GAP/2 from each cell edge: neighbouring windows stay apart (the solder outgasses between
            # them) and the coverage lands near the usual 40-60 % instead of 70+ %
            g = GAP_PART.get(ref, GAP)
            w, h = x1 - x0 - g, y1 - y0 - g
            if w < 0.2 or h < 0.2:
                continue
            new.append(Node('pad', '', Sym('smd'), Sym('rect'), Node('at', round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4)),
                            Node('size', round(w, 4), round(h, 4)), Node('layers', 'F.Paste')))
    for n in new:
        n.append(Node('uuid', u.new(fp_item_key(n))))
        fp.insert_after_last('pad', n)
    os.makedirs(TMP, exist_ok=True)
    src = os.path.join(TMP, out_name + '.kicad_mod')
    save(fp, src)
    dst = os.path.join(OUT_LIB, out_name + '.kicad_mod')
    print('%s %s: %d thermal vias %g/%g in pad %s' % (ref, name, len(local), size, drill, ep_num))
    res = subprocess.run([sys.executable, os.path.join(kskills.SCRIPTS, 'paste_clear.py'), src, dst],
                         capture_output=True, text=True)
    sys.stdout.write(''.join(l + '\n' for l in res.stdout.splitlines() if 'exposed pad' in l or 'PROBLEM' in l
                             or l.startswith('wrote')))
    if res.returncode:
        sys.stdout.write(res.stdout + res.stderr)
        sys.exit('paste_clear.py failed for %s' % out_name)


def main():
    os.makedirs(OUT_LIB, exist_ok=True)
    for ref in PARTS:
        build(ref)


if __name__ == '__main__':
    main()
