"""Footprint pad / outline dump for tools/place_gen.py.

  python3 tools/fpdump.py hw/usb-hub.kicad_pcb OUT_DIR       -> OUT_DIR/fp.json, OUT_DIR/boxes.json

fp.json:    {ref: {'lib', 'val', 'at', 'rot', 'pads': [[num, lx, ly, w, h, type, net], ...]}} in footprint-local mm
            (unrotated), as place_gen.py reads them (pad(), netof(), facing()).
boxes.json: {ref: [kind, x0, y0, x1, y1]} local placement boundary: 'crt' = courtyard, else 'out' = the silk outline
            grown by half its stroke (EasyEDA footprints have no courtyard; the silk outline is the boundary).
Run it on a board built from the current netlist (tools/build.sh stages parts that place.json does not list off the
outline), then place_gen.py, then build.sh again.
"""
import json
import math
import os
import sys

import kskills  # noqa: F401  (pins kicad-skills; must come first)
from kicad_sexpr import load


def atom(n, i, default=None):
    try:
        return n[i]
    except (IndexError, TypeError):
        return default


def child(n, name):
    hits = n.nodes(name)
    return hits[0] if hits else None


def num(v):
    return float(str(v))


def main(pcb, out):
    root = load(pcb)
    fp, boxes = {}, {}
    for f in root.nodes('footprint'):
        ref = val = None
        for p in f.nodes('property'):
            if str(atom(p, 1)) == 'Reference':
                ref = str(atom(p, 2))
            elif str(atom(p, 1)) == 'Value':
                val = str(atom(p, 2))
        at = child(f, 'at')
        x, y = num(at[1]), num(at[2])
        rot = num(atom(at, 3, 0))
        pads = []
        for p in f.nodes('pad'):
            pa, sz = child(p, 'at'), child(p, 'size')
            net = child(p, 'net')
            name = ''
            if net is not None:
                name = str(net[2]) if len(net) > 2 else str(net[1])
            pads.append([str(p[1]), round(num(pa[1]), 6), round(num(pa[2]), 6), round(num(sz[1]), 6),
                         round(num(sz[2]), 6), str(p[2]), name])
        fp[ref] = {'lib': str(f[1]), 'val': val, 'at': [x, y], 'rot': rot, 'pads': pads}
        # placement boundary from the footprint's own graphics (local coordinates)
        ext = {'F.CrtYd': [], 'F.SilkS': []}
        for kind in ('fp_line', 'fp_rect', 'fp_circle', 'fp_arc', 'fp_poly'):
            for g in f.nodes(kind):
                lay = child(g, 'layer')
                lname = str(lay[1]) if lay is not None else ''
                lname = 'F.SilkS' if lname == 'F.Silkscreen' else lname
                if lname not in ext:
                    continue
                st = child(g, 'stroke')
                w = num(child(st, 'width')[1]) if st is not None and child(st, 'width') is not None else 0.0
                pts = []
                for key in ('start', 'end', 'mid', 'center'):
                    c = child(g, key)
                    if c is not None:
                        pts.append((num(c[1]), num(c[2])))
                pl = child(g, 'pts')
                if pl is not None:
                    pts += [(num(q[1]), num(q[2])) for q in pl.nodes('xy')]
                if kind == 'fp_circle':
                    (cx, cy), (ex, ey) = pts[0], pts[1]
                    rr = math.hypot(ex - cx, ey - cy)
                    pts = [(cx - rr, cy - rr), (cx + rr, cy + rr)]
                ext[lname] += [(px - w / 2, py - w / 2) for px, py in pts] + [(px + w / 2, py + w / 2) for px, py in pts]
        pick = ('crt', ext['F.CrtYd']) if ext['F.CrtYd'] else ('out', ext['F.SilkS'])
        if pick[1]:
            xs, ys = [q[0] for q in pick[1]], [q[1] for q in pick[1]]
            boxes[ref] = [pick[0], round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]
        else:                                       # no graphics: the pad extent
            xs = [p[1] - p[3] / 2 for p in pads] + [p[1] + p[3] / 2 for p in pads]
            ys = [p[2] - p[4] / 2 for p in pads] + [p[2] + p[4] / 2 for p in pads]
            boxes[ref] = ['out', round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]
    os.makedirs(out, exist_ok=True)
    json.dump(fp, open(os.path.join(out, 'fp.json'), 'w'), indent=0)
    json.dump(boxes, open(os.path.join(out, 'boxes.json'), 'w'), indent=0)
    print('wrote %s (%d footprints)' % (os.path.join(out, 'fp.json'), len(fp)))


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(sys.argv[1], sys.argv[2])
