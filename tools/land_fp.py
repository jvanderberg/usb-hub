"""Project footprints whose JLC land pattern is corrected to the datasheet's (origin, rotation and pad numbers kept, so
JLC places them exactly as its own footprint).

TPS259470ARPWR (U8, RPW0010A): TPS25947 datasheet p73 "Land pattern example" puts IN (pad 5) 0.3 mm wide at x -0.25
and OUT (pad 6) 0.25 mm wide at x +0.25 (side pads from |x| 0.6). JLC's footprint has both strips 0.3 mm wide at
-0.235 / +0.265, which leaves 0.19 mm from OUT to pins 8 / 9 (DRC 0.2). The strips are set to TI's numbers: 0.205 mm
(IN) and 0.23 mm (OUT) to the side pads, 0.225 mm between the strips.

Writes hw/usb-hub.pretty/<JLC name>_TILand.kicad_mod; tools/gen_sch.py points the symbol at it (FP_OVERRIDE).
Run: python3 tools/land_fp.py   (from anywhere; tools/build.sh runs it before the schematic)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kskills  # noqa: E402,F401  (pins kicad-skills; must come first)
from kicad_sexpr import load, save  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, 'hw')
OUT_LIB = os.path.join(HW, 'usb-hub.pretty')

# JLC footprint: {pad number: ((x, y) from JLC, (x, y) datasheet, (w, h) from JLC, (w, h) datasheet)}
FIXES = {
    'TPS259470ARPWR': {
        '5': ((-0.235, 0.0), (-0.25, 0.0), (0.3, 2.4), (0.3, 2.4)),
        '6': ((0.265, 0.0), (0.25, 0.0), (0.3, 2.4), (0.25, 2.4)),
    },
}


def build(name):
    fp = load(os.path.join(HW, 'JLCImport.pretty', name + '.kicad_mod'))
    out_name = name + '_TILand'
    fp[1] = out_name
    for num, (at0, at1, sz0, sz1) in FIXES[name].items():
        pads = [p for p in fp.nodes('pad') if str(p[1]) == num]
        assert len(pads) == 1, '%s: %d pads numbered %s' % (name, len(pads), num)
        at, size = pads[0].need('at'), pads[0].need('size')
        # the JLC pad must still be the one these numbers were read from
        got = ((at.number(1), at.number(2)), (size.number(1), size.number(2)))
        assert got == (at0, sz0), '%s pad %s is %s, expected %s' % (name, num, got, (at0, sz0))
        at[1], at[2] = at1
        size[1], size[2] = sz1
        print('%s pad %s: at %s size %s -> at %s size %s' % (name, num, at0, sz0, at1, sz1))
    dst = os.path.join(OUT_LIB, out_name + '.kicad_mod')
    save(fp, dst)
    print('wrote %s' % dst)


def main():
    os.makedirs(OUT_LIB, exist_ok=True)
    for name in FIXES:
        build(name)


if __name__ == '__main__':
    main()
