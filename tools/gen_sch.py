"""Generate the usb-hub schematic (KiCad 10, hierarchical) from the design docs.

Sheets: root (blocks, mounting holes), power_in (PD input, TPS25730, VIN bulk, TPS54202 3V3, status LEDs),
buck_5v (LM5148 5V_BUS stage), hubs (USB2517 + USB2514B, crystals, reset supervisor, HOST receptacle),
port (one downstream USB-C port, placed 10 times: port1..port10, references offset by 100 x k).
Intended connectivity: tools/nets.json (netspec template form); every sheet is checked against it with
find_merges() and collisions() before anything is written.
Run: python3 tools/gen_sch.py   (from anywhere)"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kskills  # noqa: F401,E402  (pins kicad-skills; must come first)
from schgen import Sch, SymLib, find_merges, kicad_symbol_dir, snap  # noqa: E402
import symbols  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, 'hw')
NETS = json.load(open(os.path.join(ROOT, 'tools', 'nets.json')))
DATE = '2026-11-16'
G = 2.54

# ------------------------------------------------------------------ parts: JLC data for Device symbols
JLC = SymLib('JLCImport', os.path.join(HW, 'JLCImport.kicad_sym'))
BY_LCSC = {}
for _n in JLC.names():
    _p = {str(q[1]): str(q[2]) for q in JLC.get(_n).nodes('property')}
    BY_LCSC[_p.get('LCSC')] = (_n, _p)

VAL = {  # value shown on the sheet, per LCSC part (one part per value/package)
    'C17168': '0R', 'C11702': '1k', 'C25867': '1.5k', 'C270633': '1.87k', 'C25890': '3.3k', 'C25905': '5.1k',
    'C2933105': '5.23k', 'C25744': '10k', 'C25752': '12k', 'C62740': '15.4k', 'C25768': '22k', 'C26978': '41.2k',
    'C25792': '47k', 'C53398': '53.6k', 'C25741': '100k', 'C25764': '200k', 'C26083': '1M', 'C2904234': '2.5m',
    'C138687': '10u/50V', 'C525654': '47u/10V', 'C2836438': '22u/50V', 'C29823': '4.7u/50V', 'C15850': '10u/25V',
    'C45783': '22u/25V', 'C59461': '22u/10V', 'C19702': '10u/10V', 'C15849': '1u/50V', 'C23630': '2.2u/16V', 'C52923': '1u/25V',
    'C1525': '100n/16V', 'C307331': '100n/50V', 'C15195': '10n/50V', 'C47118429': '5.1n/50V', 'C1664': '330p/50V',
    'C576704': '110p/50V', 'C1567': '47p/50V', 'C1549': '18p/50V', 'C1548': '15p/50V',
    'C6753479': '1.5u', 'C167223': '10u', 'C12624': 'green', 'C8678': 'SS34', 'C123790': 'SMF6.0A',
    'C477994': 'PESD24VS1UL', 'C70590': '24MHz',
}
DEVSYM = {'R': 'Device:R', 'C': 'Device:C', 'CP': 'Device:C_Polarized', 'L': 'Device:L', 'LED': 'Device:LED',
          'DZ': 'Device:D_Zener', 'DS': 'Device:D_Schottky', 'XTAL': 'Device:Crystal_GND24'}


def dev(s, kind, ref, c, x, y, rot=0, value=None, **kw):
    """A Device-library symbol carrying the JLC part's footprint, LCSC number, maker, MPN and description."""
    name, p = BY_LCSC[c]
    f = {'Datasheet': symbols.lcsc_ds(c), 'Description': p.get('Description', ''),
         'Manufacturer': p.get('Manufacturer', ''), 'Manufacturer Part': p.get('Manufacturer Part', '')}
    f.update(kw.pop('fields', {}))
    return s.add(DEVSYM[kind], ref, value or VAL[c], x, y, rot, footprint='JLCImport:' + name, lcsc=c, fields=f, **kw)


def ic(s, sym, ref, value, x, y, lcsc, **kw):
    return s.add('usb-hub:' + sym, ref, value, x, y, lcsc=lcsc, **kw)


def tp(s, ref, x, y, rot=0, label=None, **fields):
    """Bare test pad (not assembled, not in BOM / position file)."""
    f = {'Description': 'Test pad %s' % (label or ''), '_hide_value': True}
    if rot == 0:                                  # pad up: ref centred above it
        f.update({'_ref_at': (x, y - 6.35), '_just': 'center'})
    f.update(fields)
    p = s.add('Connector:TestPoint', ref, label or 'TP', x, y, rot, footprint='TestPoint:TestPoint_Pad_D1.0mm',
              fields=f, in_bom=False)
    return p


def flag(s, x, y, rot=0):
    s.pwr_n += 1
    return s.add('power:PWR_FLAG', '#FLG%03d' % s.pwr_n, 'PWR_FLAG', x, y, rot, in_bom=False, on_board=False)


# ------------------------------------------------------------------ drawing helpers
def eq(a, b):
    return all(abs(u - v) < 1e-6 for u, v in zip(a, b))


def hang(s, kind, ref, c, x, y, bottom='GND', tap=True, **kw):
    """Vertical two-pin part hanging from (x, y) (its pin 1 there); bottom: 'GND', ('label', name),
    ('pwr', net) (power symbol pointing down), or None."""
    x, y = snap(x), snap(y)
    p = dev(s, kind, ref, c, x, y + 3.81, **kw)
    assert eq(p.p(1), (x, y)), (ref, p.p(1), (x, y))
    if tap:
        s.tap(p.p(1))
    end(s, p.p(2), bottom)
    return p


def end(s, pt, bottom):
    if bottom == 'GND':
        s.power('GND', *pt)
    elif bottom is None:
        pass
    elif bottom[0] == 'label':
        s.wire(pt, (pt[0], pt[1] + G))
        s.label(bottom[1], pt[0], pt[1] + G, 270)
    elif bottom[0] == 'pwr':
        s.power(bottom[1], pt[0], pt[1], rot=180)
    elif bottom[0] == 'to':                      # down to a rail drawn later at y = bottom[1]
        s.wire(pt, (pt[0], bottom[1]))
    else:
        raise ValueError(bottom)


# bank items: (width, draw(s, x, y)); branches are drawn left to right from the column end (x, y) and joined by a
# horizontal wire along y, so every hanging part sits below the staircase and never on another signal's wire
def br_part(kind, ref, c, bottom='GND', **kw):
    return (10.16 if kind == 'R' else 15.24, lambda s, x, y: hang(s, kind, ref, c, x, y, bottom, **kw))


def br_gnd():
    return (5.08, lambda s, x, y: s.power('GND', x, y))


def br_label(name):
    def d(s, x, y):
        s.wire((x, y), (x, y + G))
        s.label(name, x, y + G, 270)
    return (7.62, d)                              # the label text runs down on the left of its wire


def br_tp(ref, label):
    def d(s, x, y):
        s.wire((x, y), (x, y + G))
        tp(s, ref, x, y + G, 180, label, _ref_at=(x, y + G + 6.35), _just='center')
    return (7.62, d)


def br_drop(y_to):
    return (5.08, lambda s, x, y: s.wire((x, y), (x, y_to)))


def vdio(s, kind, ref, c, x, y, top='K', bottom='GND', tap=True):
    """vertical two-pin diode/LED (Device symbol, 1 = K) hanging from (x, y) with the named pin on top"""
    rot = 270 if top == 'K' else 90
    dx = 5.08 if kind == 'LED' else 2.54          # clear of the LED's emission arrows
    d = dev(s, kind, ref, c, x, y + 3.81, rot=rot, fields={'_ref_at': (x + dx, y + 2.54),
                                                          '_val_at': (x + dx, y + 5.08),
                                                          '_just': 'left' if rot == 270 else 'right'})  # rot-relative
    pin_top, pin_bot = (1, 2) if top == 'K' else (2, 1)
    assert eq(d.p(pin_top), (snap(x), snap(y))), (ref, d.p(pin_top), (x, y))
    if tap:
        s.tap(d.p(pin_top))
    end(s, d.p(pin_bot), bottom)
    return d


def XF(cx, y1):
    """crystal fields: ref above the body, value under its GND symbol"""
    return {'_ref_at': (cx, y1 - 5.08), '_val_at': (cx, y1 + 10.16), '_just': 'center'}


def br_chain(parts, bottom='GND', node=None):
    """series chain hanging from (x, y): [(kind, ref, c), ...]; node names the first joint with a label stub to the
    right (the chain then needs the width for it)"""
    def d(s, x, y):
        yy = y
        for i, (kind, ref, c) in enumerate(parts):
            kw = {'fields': {'_ref_at': (x + 2.54, yy + 1.27), '_val_at': (x + 2.54, yy + 3.81),
                             '_just': 'left'}} if i == 0 and node else {}   # clear of the node label below
            p = hang(s, kind, ref, c, x, yy, bottom if i == len(parts) - 1 else None, tap=i == 0, **kw)
            yy = p.p(2)[1]
            if i == 0 and node:
                s.wire((x, yy), (x + G, yy))
                s.label(node, x + G, yy, 0)
    return (17.78 if node else 12.7, d)


def item(*branches):
    w = sum(b[0] for b in branches)

    def d(s, x, y):
        bx, last = x, x
        for bw, fn in branches:
            fn(s, bx, y)
            last = bx
            bx += bw
        if last != x:
            s.wire((x, y), (last, y))
    return (w, d)


def bank(s, rows, x0, y_bank, side='L'):
    """Fan out a column of IC pins (top to bottom) into hanging items below y_bank. Left side: the top pin's column is
    at x0 and the others step right by each item's width; right side: the top pin's column is at x0 and the others
    step left. Upper pins turn further out, so no staircase wire crosses another or a hanging part."""
    xs = []
    if side == 'L':
        x = x0
        for pt, (w, d) in rows:
            xs.append(x)
            x += w
        assert x <= rows[-1][0][0] + 0.01, 'bank overlaps its IC: %s > %s' % (x, rows[-1][0][0])
    else:
        x = x0
        for i, (pt, (w, d)) in enumerate(rows):
            if i:
                x -= w
            xs.append(x)
        assert xs[-1] >= rows[-1][0][0] + 2.53, 'bank overlaps its IC'
    for (pt, (w, d)), x in zip(rows, xs):
        assert pt[1] < y_bank
        s.wire(pt, (x, pt[1]), (x, y_bank))
        d(s, x, y_bank)
    return xs


def stub_label(s, pt, name, side='L', n=1):
    """short wire away from a pin and a local label at its end"""
    dx = -G * n if side == 'L' else G * n
    q = (pt[0] + dx, pt[1])
    s.wire(pt, q)
    s.label(name, q[0], q[1], 180 if side == 'L' else 0)
    return q


def hstub(s, pt, name, side='R', n=2, shape='bidirectional'):
    dx = -G * n if side == 'L' else G * n
    q = (pt[0] + dx, pt[1])
    s.wire(pt, q)
    s.hlabel(name, q[0], q[1], 180 if side == 'L' else 0, shape=shape)
    return q


# ================================================================== port sheet (x10)
def port_sheet(root):
    s = root.sub('port.kicad_sch', paper='A4', title='Downstream USB-C port (placed 10x)')
    yV = 50.8
    J = ic(s, 'TYPE-C-31-M-12', 'J1', 'TYPE-C-31-M-12', 205.74, yV + 16.51, 'C165948', mirror='y',
           fields={'_ref_at': (203.2, 46.99), '_val_at': (203.2, 88.9)})
    xJ, y0 = J.p('A4B9')
    assert abs(y0 - yV) < 1e-6, J.p('A4B9')
    yCC1, yCC2, yDP, yDM = J.p('A5')[1], J.p('B5')[1], J.p('A6')[1], J.p('A7')[1]
    xU = xJ - 30.48
    U2 = ic(s, 'TPD4E05U06', 'U2', 'TPD4E05U06DQAR', xU - 8.89, yCC1 + 5.08, 'C138714', mirror='y',
            fields={'_ref_at': (xU - 12.7, yCC1 - 5.08), '_val_at': (xU - 12.7, yDM + 10.16)})
    assert eq(U2.p('4'), (xU, yCC1)) and eq(U2.p('1'), (xU, yDP)), (U2.p('4'), U2.p('1'))
    for a, b in (('4', 'A5'), ('5', 'B5')):
        s.wire(U2.p(a), J.p(b))
    stub_label(s, J.p('A6'), 'DP', side='L', n=2)     # same name as the sheet's hierarchical label: one net
    stub_label(s, J.p('A7'), 'DM', side='L', n=2)
    g = U2.p('3')
    s.wire(g, (g[0] - G, g[1]), (g[0] - G, yDM + 5.08))
    s.power('GND', g[0] - G, yDM + 5.08)
    yG, yS = J.p('A1B12')[1], J.p('1')[1]
    s.wire(J.p('A1B12'), (xJ - G, yG), (xJ - G, yS + 5.08))
    s.wire(J.p('1'), (xJ - G, yS))
    s.power('GND', xJ - G, yS + 5.08)
    # switch
    U1 = ic(s, 'SY6863B3ABC', 'U1', 'SY6863B3ABC', 66.04, yV + 6.35, 'C2687365',
            fields={'_val_at': (55.88, yV + 22.86), '_just': 'left'})
    assert eq(U1.p('1'), (76.2, yV)), U1.p('1')
    s.wire((27.94, yV), U1.p('6'))
    s.power('5V_BUS', 27.94, yV)
    hang(s, 'C', 'C1', 'C19702', 38.1, yV)
    en, ocb = U1.p('4'), U1.p('3')
    s.wire((20.32, yV + 25.4), (50.8, yV + 25.4), (50.8, en[1]), en)
    s.hlabel('EN', 20.32, yV + 25.4, 180, shape='input')
    s.wire((20.32, yV + 27.94), (53.34, yV + 27.94), (53.34, ocb[1]), ocb)
    s.hlabel('OCS_N', 20.32, yV + 27.94, 180, shape='output')
    s.power('GND', *U1.p('2'))
    iset = U1.p('5')
    s.wire(iset, (81.28, iset[1]))
    hang(s, 'R', 'R1', 'C270633', 81.28, iset[1])
    # VBUS rail: OUT -> receptacle, shunts hanging below it
    s.wire(U1.p('1'), J.p('A4B9'))
    hang(s, 'C', 'C2', 'C59461', 91.44, yV)
    hang(s, 'C', 'C3', 'C1525', 104.14, yV)
    # no VBUS TVS per port (dropped 2026-11-16 to fit 80x80: SY6863 OUT withstands 28 V, TPD4E05U06 covers data/CC)
    r4 = hang(s, 'R', 'R4', 'C25867', 132.08, yV, bottom=None)
    vdio(s, 'LED', 'D2', 'C12624', 132.08, r4.p(2)[1], top='A', tap=False)
    s.wire((142.24, yV), (142.24, yV - 5.08))
    s.label('VBUS', 142.24, yV - 5.08, 90)
    # Rp to the switched VBUS (Type-C "3.0 A" Rp)
    r2 = hang(s, 'R', 'R2', 'C25744', xU + 5.08, yV, bottom=None)
    s.wire(r2.p(2), (xU + 5.08, yCC1))
    hang(s, 'R', 'R3', 'C25744', xU + 12.7, yCC2, bottom=('label', 'VBUS'))   # CC2's Rp hangs below: no crossing
    # data from the hub into the ESD array; the receptacle side joins by the same-named labels
    yl = yV + 40.64
    s.wire(U2.p('2'), (xU + 2.54, yDM), (xU + 2.54, yl), (20.32, yl))
    s.hlabel('DM', 20.32, yl, 180)
    s.wire(U2.p('1'), (xU + 7.62, yDP), (xU + 7.62, yl + G), (20.32, yl + G))
    s.hlabel('DP', 20.32, yl + G, 180)
    s.text('Rp 10k to switched VBUS = Type-C 3.0 A advertisement. RSET 1.87k: ILIM = 7100/RSET = 3.8 A '
           '(3.47-4.08 A, SY6863 p4).', 20.32, 160.02)
    return s


# ================================================================== power_in sheet
def power_in_sheet(root):
    s = root.sub('power_in.kicad_sch', paper='A3', title='PD input, VIN, 3V3 buck, LEDs')
    # --- PD receptacle
    J = ic(s, 'USB4105-GF-A', 'J1', 'USB4105-GF-A', 30.48, 76.2, 'C3020560')
    yV0, yC1, yC2 = J.p('A4')[1], J.p('A5')[1], J.p('B5')[1]
    xJ = J.p('A4')[0]
    yG, yS = J.p('A1')[1], J.p('1')[1]
    s.wire(J.p('A1'), (xJ + G, yG), (xJ + G, yS + 5.08))
    s.wire(J.p('1'), (xJ + G, yS))
    s.power('GND', xJ + G, yS + 5.08)
    # --- TPS25730, VBUS row level with the receptacle's
    U = ic(s, 'TPS25730D', 'U1', 'TPS25730DREFR', 248.92, 0, 'C22438973')
    U.y += yV0 - U.p('23')[1]
    xu = U.p('23')[0]
    # PD_VBUS: up from the receptacle, along the top, down into U1; protection and HF caps hang from the top run
    yv = snap(yV0 - 20.32)
    s.wire(J.p('A4'), (xJ + 5.08, yV0), (xJ + 5.08, yv), (xu - 5.08, yv), (xu - 5.08, yV0), U.p('23'))
    tvs = ic(s, 'ESTVS2200', 'D1', 'ESTVS2200DRVR', 55.88, yv + 5.08, 'C42400188', rot=270,
             fields={'_ref_at': (59.69, yv + 3.81), '_val_at': (59.69, yv + 6.35), '_just': 'left'})
    assert eq(tvs.p('4'), (55.88, yv)), tvs.p('4')
    s.tap(tvs.p('4'))
    s.power('GND', *tvs.p('1'))
    vdio(s, 'DS', 'D2', 'C8678', 88.9, yv)
    hang(s, 'C', 'C1', 'C29823', 106.68, yv)
    for i, ref in enumerate(('C2', 'C3', 'C4', 'C5')):
        hang(s, 'C', ref, 'C15195', 121.92 + 15.24 * i, yv)
    f = flag(s, 193.04, yv)
    s.tap(f.p(1))
    s.wire((205.74, yv), (205.74, yv - 5.08))
    s.label('PD_VBUS', 205.74, yv - 5.08, 90)
    # CC1 straight; CC2 dips under CC1's shunts (no crossings)
    xa, xb = xJ + 7.62, xJ + 55.88
    s.wire(J.p('A5'), U.p('28'))
    hang(s, 'C', 'C6', 'C1664', xJ + 17.78, yC1)
    vdio(s, 'DZ', 'D3', 'C477994', xJ + 33.02, yC1)
    yd = snap(yC1 + 15.24)
    s.wire(J.p('B5'), (xa, yC2), (xa, yd), (xb, yd), (xb, yC2), U.p('29'))
    hang(s, 'C', 'C7', 'C1664', xJ + 17.78, yd)
    vdio(s, 'DZ', 'D4', 'C477994', xJ + 33.02, yd)
    # --- U1 straps (left) and outputs (right); PD_LDO3V3 runs as one rail under both banks
    yb = snap(U.p('38')[1] + 7.62)
    yr = snap(yb + 15.24)
    T = ('to', yr)
    rows = [(U.p('2'), item(br_part('R', 'R2', 'C25744'), br_part('R', 'R1', 'C25764', T))),
            (U.p('3'), br_drop(yr)),
            (U.p('5'), item(br_part('R', 'R4', 'C25744'), br_part('R', 'R3', 'C25764', T))),
            (U.p('7'), item(br_part('R', 'R6', 'C25792'), br_part('R', 'R5', 'C25764', T))),
            (U.p('18'), br_part('R', 'R12', 'C25744', T)),
            (U.p('26'), br_part('R', 'R7', 'C25744')),
            (U.p('27'), br_part('R', 'R8', 'C25744')),
            (U.p('36'), br_part('R', 'R9', 'C25744')),
            (U.p('38'), item(br_part('C', 'C11', 'C15850'),
                             br_part('R', 'R13', 'C17168', ('pwr', '3V3'), dnp=True)))]
    xl = bank(s, rows, xu - 134.62, yb)
    s.power('GND', *U.p('11'))
    xr = U.p('20')[0]
    rrows = [(U.p('1'), item(br_part('C', 'C9', 'C15850'), br_drop(yr))),
             (U.p('4'), br_part('C', 'C10', 'C15850')),
             (U.p('8'), item(br_part('R', 'R10', 'C25890', T), br_tp('TP4', 'PD_SDA'))),
             (U.p('9'), item(br_part('R', 'R11', 'C25890', T), br_tp('TP3', 'PD_SCL'))),
             (U.p('19'), br_tp('TP5', 'SINK_EN')),
             (U.p('6'), br_tp('TP6', 'CAP_MIS')),
             (U.p('37'), br_tp('TP7', 'PLUG_EVENT')),
             (U.p('15'), br_label('PD_DRAIN'))]
    xrr = bank(s, rrows, xr + 86.36, yb, side="R")
    for p in ('13', '10'):
        s.nc(U.p(p))
    x_rail_r = xrr[0] + 15.24                    # C9 item's drop to the rail
    s.wire((xl[0] - 5.08, yr), (x_rail_r, yr))
    s.label('PD_LDO3V3', xl[0] - 5.08, yr, 180)
    # VIN: PPHV up and along above the right bank: local cap, bulk, test pad
    pp = U.p('20')
    yvin = snap(pp[1] - 20.32)
    xv = pp[0] + 17.78
    s.wire(pp, (pp[0] + G, pp[1]), (pp[0] + G, yvin), (xv + 40.64, yvin))
    s.wire((xv + 40.64, yvin), (xv + 40.64, yvin - 5.08))
    s.power('VIN', xv + 40.64, yvin - 5.08)
    hang(s, 'C', 'C8', 'C138687', xv, yvin)
    cp = dev(s, 'CP', 'C12', 'C2836438', xv + 15.24, yvin + 3.81)
    s.tap(cp.p(1))
    s.power('GND', *cp.p(2))
    t1 = tp(s, 'TP1', xv + 30.48, yvin, 0, 'VIN')
    s.tap(t1.p(1))
    # --- 3V3 buck TPS54202 (lower band; VIN by its power symbol)
    U2 = ic(s, 'TPS54202', 'U2', 'TPS54202DDCR', 91.44, 213.36, 'C191884')
    vi = U2.p('3')
    s.wire((30.48, vi[1]), vi)
    s.power('VIN', 30.48, vi[1])
    hang(s, 'C', 'C13', 'C138687', 40.64, vi[1])
    hang(s, 'C', 'C14', 'C307331', 58.42, vi[1])
    s.nc(U2.p('5'))
    s.power('GND', *U2.p('1'))
    # BOOT cap from BOOT (above) down onto the SW run; SW -> L1 -> 3V3
    bt, sw, fb = U2.p('6'), U2.p('2'), U2.p('4')
    xc = snap(bt[0] + 7.62)
    s.wire(bt, (bt[0] + G, bt[1]), (bt[0] + G, sw[1] - 7.62), (xc, sw[1] - 7.62))
    c15 = dev(s, 'C', 'C15', 'C1525', xc, sw[1] - 3.81)
    assert eq(c15.p(2), (xc, sw[1])), (c15.p(2), xc, sw)
    s.tap(c15.p(2))
    L1 = dev(s, 'L', 'L1', 'C167223', xc + 20.32, sw[1], rot=90)
    s.wire(sw, L1.p(1))
    y3 = sw[1]
    xo = L1.p(2)[0]
    xend = xo + 111.76
    s.wire(L1.p(2), (xend, y3))
    s.wire((xend, y3), (xend, y3 - 5.08))
    s.power('3V3', xend, y3 - 5.08)
    # FB divider R14 / R15 and feed-forward C19
    xd = xo + 10.16
    r14 = hang(s, 'R', 'R14', 'C25741', xd, y3, bottom=None)
    hang(s, 'R', 'R15', 'C25768', xd, r14.p(2)[1], tap=False)
    c19 = hang(s, 'C', 'C19', 'C1567', xd + 12.7, y3, bottom=None)
    s.wire(c19.p(2), (xd + 12.7, r14.p(2)[1]), r14.p(2))
    s.wire(fb, (fb[0] + G, fb[1]), (fb[0] + G, r14.p(2)[1]), r14.p(2))
    for i, ref in enumerate(('C16', 'C17', 'C18')):
        hang(s, 'C', ref, 'C45783', xd + 33.02 + 15.24 * i, y3)
    t2 = tp(s, 'TP2', xd + 78.74, y3, 0, '3V3')
    s.tap(t2.p(1))
    f = flag(s, xd + 91.44, y3)
    s.tap(f.p(1))
    # --- status LEDs (rail-based, power-design-pd-3v3.md s2.3 D3)
    yl = 205.74
    s.power('5V_BUS', 274.32, yl)
    r16 = hang(s, 'R', 'R16', 'C25867', 274.32, yl, bottom=None, tap=False)
    vdio(s, 'LED', 'D5', 'C12624', 274.32, r16.p(2)[1], top='A', tap=False)
    q1 = ic(s, 'AO3401A', 'Q1', 'AO3401A', 320.04, yl + 7.62, 'C15127', mirror='x')
    gq, sq, dq = q1.p('1'), q1.p('2'), q1.p('3')
    s.power('3V3', *sq)
    s.wire((294.64, yl), (294.64, gq[1]), gq)
    s.power('5V_BUS', 294.64, yl)
    hang(s, 'R', 'R17', 'C25741', 302.26, gq[1])
    r18 = hang(s, 'R', 'R18', 'C11702', dq[0], dq[1], bottom=None, tap=False)
    d6 = ic(s, 'KT-0603R', 'D6', 'KT-0603R', 0, 0, 'C2286', rot=270)
    d6.x += r18.p(2)[0] - d6.p('1')[0]
    d6.y += r18.p(2)[1] - d6.p('1')[1]
    d6.fields.update({'_ref_at': (d6.x + 5.08, d6.y - 1.27), '_val_at': (d6.x + 5.08, d6.y + 1.27), '_just': 'left'})
    s.power('GND', *d6.p('2'))
    s.text('PD OK (green D5): 5V_BUS up.\nLOW POWER (red D6): 3V3 up and 5V_BUS down\n(Q1 Vgs = 5V_BUS - 3V3).',
           264.16, 182.88)
    # GND flag and GND test pad
    t8 = tp(s, 'TP8', 365.76, 213.36, 0, 'GND')
    s.power('GND', *t8.p(1))
    f = flag(s, 378.46, 213.36)
    s.power('GND', *f.p(1))
    s.text('TPS25730 straps (Table 8-1..8-6, p31-37): ADCIN1 = 1 (9 V min), ADCIN2 = 7 (20 V max, tied to LDO_3V3), '
           'ADCIN3 = 1 (1 A operating), ADCIN4 = 3 (5 A max).  RESERVED: 10k to GND.  I2C 0x21 on test pads.',
           20.32, 266.7)
    s.text('VIN bulk <= 22 uF so PPHV stays under 100 uF (power-design-pd-3v3.md s5).  VIN_3V3 on its cap only, '
           'R13 DNP (s2.4).  3V3: 0.596 V x (1 + 100k/22k) = 3.31 V.', 20.32, 271.78)
    return s


# ================================================================== buck_5v sheet
def buck_sheet(root):
    s = root.sub('buck_5v.kicad_sch', paper='A3', title='5V_BUS buck (LM5148)')
    U = ic(s, 'LM5148', 'U30', 'LM5148RGYR', 0, 0, 'C7470701')
    U.x, U.y = 180.34, 127.0
    ho, cb, sw, lo = U.p('13'), U.p('15'), U.p('14'), U.p('11')
    isn, vo = U.p('20'), U.p('21')
    xp = ho[0]
    r = lambda k: ho[1] + G * k  # noqa: E731  (right-side row k, from HO)
    # half bridge: Q30 gate level with row 1, SW node at row 4 (between S of Q30 and D of Q31), Q31 gate at row 7
    xq = xp + 50.8
    q30 = ic(s, 'CSD17505Q5A', 'Q30', 'CSD17505Q5A', xq, r(1), 'C553150',
             fields={'_ref_at': (xq + 3.81, r(1) - 7.62), '_val_at': (xq + 3.81, r(1) - 5.08), '_just': 'left'})
    q31 = ic(s, 'CSD17573Q5B', 'Q31', 'CSD17573Q5B', xq, r(7), 'C202231')
    assert eq(q30.p('4'), (xq - 5.08, r(1))) and eq(q31.p('4'), (xq - 5.08, r(7))), (q30.p('4'), q31.p('4'))
    xh, xb, xs, xl = xp + 30.48, xp + 22.86, xp + 12.7, xp + 7.62
    s.wire(ho, (xh, ho[1]), (xh, r(1)), q30.p('4'))
    s.wire(cb, (xb, cb[1]))
    c46 = dev(s, 'C', 'C46', 'C1525', xb, r(1) + 3.81)
    assert eq(c46.p(1), (xb, r(1))) and eq(c46.p(2), (xb, r(4)))
    s.tap(c46.p(2))
    s.wire(sw, (xs, sw[1]), (xs, r(4)), (xq + G, r(4)))
    s.wire((xs, r(4)), (xs, r(6)))                    # names the switch node (HighCurrent net class)
    s.label('5V_SW', xs, r(6), 0)
    s.wire(lo, (xl, lo[1]), (xl, r(7)), q31.p('4'))
    s.wire(q30.p('1'), q31.p('5'))
    s.power('GND', *q31.p('1'))
    # SW -> L30 -> 5V_ISNS -> R30 shunt -> 5V_BUS
    L30 = dev(s, 'L', 'L30', 'C6753479', xq + 15.24, r(3), rot=90)
    s.wire(q30.p('1'), L30.p(1))
    s.wire(L30.p(2), (xq + 33.02, r(3)))
    R30 = dev(s, 'R', 'R30', 'C2904234', xq + 36.83, r(3), rot=90)
    s.wire((xq + 33.02, r(3)), R30.p(1))
    xn = xq + 30.48
    xo = R30.p(2)[0] + 5.08
    yb = r(3)
    s.wire((xq + 33.02, r(3) - 0), (xq + 33.02, r(3) - 5.08))
    s.label('5V_ISNS', xq + 33.02, r(3) - 5.08, 90)
    # Kelvin sense lines, under the bridge
    xi, xvv = xp + 5.08, xp + 2.54
    ys = r(14)
    s.wire(isn, (xi, isn[1]), (xi, ys), (xn, ys), (xn, r(3)))
    s.wire(vo, (xvv, vo[1]), (xvv, ys + G), (xo, ys + G), (xo, yb))
    s.wire(R30.p(2), (xo + 7.62 + 13.97 * 7, yb))
    cx = [xo + 7.62 + 13.97 * i for i in range(8)]     # 13.97 pitch clears the '47u/10V' values
    for i, x in enumerate(cx):
        hang(s, 'C', 'C%d' % (36 + i), 'C525654', x, yb)
    s.wire((xo, yb), (xo, yb - 5.08))
    s.power('5V_BUS', xo, yb - 5.08)
    f = flag(s, (cx[4] + cx[5]) / 2, yb)
    s.tap(f.p(1))
    t = tp(s, 'TP30', (cx[5] + cx[6]) / 2, yb, 0, '5V_BUS')
    s.tap(t.p(1))
    s.power('GND', *U.p('7'))
    s.power('GND', *U.p('10'))
    # VIN: rail above the bridge, input caps hanging from it, Q30 drain up to it
    yvin = q30.p('5')[1] - 20.32
    s.wire((xq - 81.28, yvin), (xq + G, yvin), q30.p('5'))
    s.power('VIN', xq - 81.28, yvin)
    for i, ref in enumerate(('C30', 'C31', 'C32', 'C33')):
        hang(s, 'C', ref, 'C138687', xq - 71.12 + 12.7 * i, yvin)
    hang(s, 'C', 'C34', 'C307331', xq - 20.32, yvin)
    hang(s, 'C', 'C35', 'C307331', xq - 7.62, yvin)
    # left side of U30
    vin = U.p('12')
    s.wire(vin, (vin[0] - G, vin[1]))
    s.power('VIN', vin[0] - G, vin[1])
    en = U.p('19')
    V5 = ('pwr', '5V_BUS')
    VD = ('label', '5V_VDDA')
    rows = [(U.p('4'), br_part('R', 'R31', 'C53398')),
            (U.p('3'), br_part('R', 'R32', 'C26978')),
            (U.p('18'), br_label('5V_VDDA')),
            (U.p('6'), item(br_part('R', 'R35', 'C25744'), br_part('R', 'R34', 'C53398', V5))),
            (U.p('5'), item(br_part('C', 'C48', 'C576704'),
                            br_chain([('R', 'R33', 'C2933105'), ('C', 'C47', 'C47118429')], node='5V_RC'))),
            (U.p('9'), br_part('C', 'C44', 'C23630')),
            (U.p('8'), item(br_part('C', 'C45', 'C1525'), br_label('5V_VDDA'))),
            (U.p('16'), br_gnd()),
            (U.p('17'), item(br_part('R', 'R38', 'C25741', VD), br_tp('TP31', 'PG')))]
    x0 = U.p('17')[0] - sum(w for _, (w, _) in rows)
    xe = x0 - 10.16
    assert xe >= 15.23, 'buck bank does not fit: xe = %s' % xe
    bank(s, rows, x0, U.p('17')[1] + 7.62)
    s.wire(en, (xe, en[1]))
    r36 = dev(s, 'R', 'R36', 'C25741', xe, en[1] - 3.81)
    assert eq(r36.p(2), (xe, en[1]))
    s.power('VIN', *r36.p(1))
    hang(s, 'R', 'R37', 'C62740', xe, en[1])
    t = tp(s, 'TP32', 63.5, 233.68, 0, 'GND')
    s.power('GND', *t.p(1))
    s.text('405 kHz (RT 53.6k), DRSS spread spectrum primary (CNFG 41.2k), diode-emulation PFM (PFM/SYNC = VDDA), '
           'internal VCC (VCCX = GND).', 20.32, 266.7)
    s.text('Vout = 0.8 V x (1 + 53.6k/10k) = 5.09 V.  EN/UVLO 100k/15.4k: on 7.49 V, off 6.49 V.  '
           'Peak limit 60 mV / 2.5 mOhm = 24 A typ (19.6-29.2 A).', 20.32, 271.78)
    return s


# ================================================================== hubs sheet
def hubs_sheet(root):
    s = root.sub('hubs.kicad_sch', paper='A2', title='USB hubs, HOST port, reset')
    A = ic(s, 'USB2517', 'U4', 'USB2517-JZX', 0, 0, 'C1521556')
    A.x, A.y = 254.0, 152.4
    xa_l, xa_r = A.p('59')[0], A.p('2')[0]
    # --- hub A top: 3V3 rail with decoupling to the left, 1.8 V regulator caps to the right
    yt = A.p('5')[1]
    yr = yt - 10.16
    tops3 = [A.p(p) for p in ('5', '24', '46', '64')]
    for p in tops3:
        s.wire(p, (p[0], yr))
    xr0 = xa_l - 119.38
    s.wire((xr0, yr), tops3[-1][0:1] + (yr,))
    s.power('3V3', xr0, yr)
    caps = [('C50', 'C1525'), ('C51', 'C1525'), ('C52', 'C1525'), ('C53', 'C1525'), ('C54', 'C1525'),
            ('C55', 'C1525'), ('C56', 'C1525'), ('C57', 'C19702')]
    for i, (ref, c) in enumerate(caps):
        hang(s, 'C', ref, c, xr0 + 10.16 + 15.24 * i, yr)
    v18, v18p = A.p('25'), A.p('62')
    s.wire(v18p, (v18p[0], yt - 5.08), (v18p[0] + 10.16, yt - 5.08))
    hang(s, 'C', 'C59', 'C15849', v18p[0] + 10.16, yt - 5.08)
    s.wire(v18, (v18[0], yt - 15.24), (v18p[0] + 22.86, yt - 15.24))
    hang(s, 'C', 'C58', 'C15849', v18p[0] + 22.86, yt - 15.24)
    s.power('GND', *A.p('65'))
    # --- hub A left: labels to HOST / reset, strap bank
    stub_label(s, A.p('59'), 'USB_UP_DP')
    stub_label(s, A.p('58'), 'USB_UP_DM')
    stub_label(s, A.p('44'), 'HUBA_VBUS_DET')
    stub_label(s, A.p('43'), 'HUB_RESET_N')
    xt = []

    def xtal_a(s, x, y):
        xt.append(x)

    def xtal_b(s, x, y):
        x1, x2 = xt[0], x
        y1 = y + G
        Y = dev(s, 'XTAL', 'Y1', 'C70590', (x1 + x2) / 2, y1, fields=XF((x1 + x2) / 2, y1))
        s.wire((x1, y), (x1, y1), Y.p(1))
        s.wire((x2, y), (x2, y1), Y.p(3))
        s.power('GND', *Y.p(2))
        hang(s, 'C', 'C60', 'C1549', x1, y1)
        hang(s, 'C', 'C61', 'C1549', x2, y1)
        r40 = dev(s, 'R', 'R40', 'C26083', (x1 + x2) / 2, y - 7.62, rot=90)
        s.wire((x1, y - 7.62), r40.p(1))
        s.wire(r40.p(2), (x2, y - 7.62))
    straps = [('41', 'R42'), ('42', 'R43'), ('40', 'R44'), ('45', 'R45'), ('34', 'R46'), ('50', 'R47'), ('48', 'R48'),
              ('51', 'R49'), ('49', 'R50'), ('47', 'R51'), ('33', 'R52'), ('31', 'R53'), ('17', 'R54'), ('15', 'R55')]
    rows = [(A.p('61'), (30.48, xtal_a)), (A.p('60'), (10.16, xtal_b)),
            (A.p('63'), br_part('R', 'R41', 'C25752')),
            (A.p('13'), br_gnd())]
    rows += [(A.p(p), br_part('R', ref, 'C25792')) for p, ref in straps]
    rows += [(A.p('19'), br_gnd())]
    yba = A.p('19')[1] + 10.16
    bank(s, rows, xa_l - sum(w for _, (w, _) in rows), yba)
    for p in ('32', '18', '16', '14', '37'):
        s.nc(A.p(p))
    # --- hub A right: ports 1-6 to hierarchical labels; PRTPWR pull-downs hang beyond the shorter labels
    for n, (dp, dm, pw, oc, rpd) in enumerate([(2, 1, 29, 28, 'R56'), (4, 3, 26, 27, 'R57'), (7, 6, 23, 22, 'R58'),
                                               (9, 8, 20, 21, 'R59'), (12, 11, 30, 35, 'R60'),
                                               (54, 53, 39, 38, 'R61')], 1):
        hstub(s, A.p(str(dp)), 'HUBA_DN%d_DP' % n)
        hstub(s, A.p(str(dm)), 'HUBA_DN%d_DM' % n)
        hstub(s, A.p(str(oc)), 'HUBA_OCS%d_N' % n, shape='input')
        q = A.p(str(pw))
        s.wire(q, (q[0] + 33.02, q[1]))
        s.hlabel('HUBA_PRTPWR%d' % n, q[0] + 33.02, q[1], 0, shape='output')
        hang(s, 'R', rpd, 'C25744', q[0] + 25.4, q[1])
    # --- hub B
    B = ic(s, 'USB2514B', 'U5', 'USB2514B-AEZC-TR', 0, 0, 'C16251')
    B.x = xa_r + 190.5
    B.y = 0
    B.y += A.p('56')[1] - B.p('31')[1]
    assert eq(B.p('31')[1:], A.p('56')[1:]) and eq(B.p('27')[1:], A.p('36')[1:]), (B.p('27'), A.p('36'))
    xb_l = B.p('31')[0]
    for a, b, name in (('56', '31', 'HUBA_DN7_DP'), ('55', '30', 'HUBA_DN7_DM')):   # named for the USB net class
        stub_label(s, A.p(a), name, side='R', n=4)
        stub_label(s, B.p(b), name, side='L', n=4)
    # PRTPWR7 -> R63 (0R) -> HUBB_VBUS_DET; R62 10k to GND; R75 DNP 0R from 3V3
    pw7 = A.p('36')
    r63 = dev(s, 'R', 'R63', 'C17168', pw7[0] + 7.62, pw7[1], rot=90)
    s.wire(pw7, r63.p(1))
    s.wire(r63.p(2), B.p('27'))
    hang(s, 'R', 'R62', 'C25744', pw7[0] + 17.78, pw7[1])
    hang(s, 'R', 'R75', 'C17168', pw7[0] + 27.94, pw7[1], bottom=('pwr', '3V3'), dnp=True)
    s.wire((pw7[0] + 38.1, pw7[1]), (pw7[0] + 38.1, pw7[1] + 5.08))
    s.label('HUBB_VBUS_DET', pw7[0] + 38.1, pw7[1] + 5.08, 270)
    stub_label(s, B.p('26'), 'HUB_RESET_N')
    # hub B top: 3V3 rail from the left with decoupling (CRFILT / PLLFILT caps are in the left bank)
    ytb = B.p('5')[1]
    yrb = ytb - 10.16
    for p in (B.p('5'), B.p('15')):
        s.wire(p, (p[0], yrb))
    xrb = B.p('5')[0] - 116.84
    s.wire((xrb, yrb), (B.p('15')[0], yrb))
    s.power('3V3', xrb, yrb)
    capsb = [('C62', 'C1525'), ('C63', 'C1525'), ('C64', 'C1525'), ('C65', 'C1525'), ('C66', 'C1525'),
             ('C67', 'C1525'), ('C70', 'C19702')]
    for i, (ref, c) in enumerate(capsb):
        hang(s, 'C', ref, c, xrb + 10.16 + 15.24 * i, yrb)
    s.power('GND', *B.p('37'))
    xtb = []

    def xtal_c(s, x, y):
        xtb.append(x)

    def xtal_d(s, x, y):
        x1, x2 = xtb[0], x
        y1 = y + G
        Y = dev(s, 'XTAL', 'Y2', 'C70590', (x1 + x2) / 2, y1, fields=XF((x1 + x2) / 2, y1))
        s.wire((x1, y), (x1, y1), Y.p(1))
        s.wire((x2, y), (x2, y1), Y.p(3))
        s.power('GND', *Y.p(2))
        hang(s, 'C', 'C71', 'C1548', x1, y1)
        hang(s, 'C', 'C72', 'C1548', x2, y1)
    rowsb = [(B.p('33'), (30.48, xtal_c)), (B.p('32'), (10.16, xtal_d)),
             (B.p('35'), br_part('R', 'R66', 'C25752'))]
    rowsb += [(B.p(p), br_part('R', ref, 'C25792')) for p, ref in (('24', 'R67'), ('25', 'R68'), ('22', 'R69'),
                                                                   ('28', 'R70'))]
    rowsb += [(B.p('14'), br_part('C', 'C68', 'C1525')), (B.p('34'), br_part('C', 'C69', 'C1525'))]
    x0b = xb_l - sum(w for _, (w, _) in rowsb)
    assert x0b > pw7[0] + 40.64, ('hub B bank reaches hub A port 7 parts', x0b, pw7)
    bank(s, rowsb, x0b, B.p('34')[1] + 10.16)
    s.nc(B.p('11'))
    for n, (dp, dm, pw, oc, rpd) in enumerate([(2, 1, 12, 13, 'R71'), (4, 3, 16, 17, 'R72'), (7, 6, 18, 19, 'R73'),
                                               (9, 8, 20, 21, 'R74')], 1):
        hstub(s, B.p(str(dp)), 'HUBB_DN%d_DP' % n)
        hstub(s, B.p(str(dm)), 'HUBB_DN%d_DM' % n)
        hstub(s, B.p(str(oc)), 'HUBB_OCS%d_N' % n, shape='input')
        q = B.p(str(pw))
        s.wire(q, (q[0] + 33.02, q[1]))
        s.hlabel('HUBB_PRTPWR%d' % n, q[0] + 33.02, q[1], 0, shape='output')
        hang(s, 'R', rpd, 'C25744', q[0] + 25.4, q[1])
    # --- HOST receptacle (UFP drawing); D+/D- leave by labels on both sides of the ESD array (no crossings);
    # CC2 straight with its Rd, CC1 dips under it to its own Rd
    J = ic(s, 'TYPE-C-31-M-12_UFP', 'J2', 'TYPE-C-31-M-12', 40.64, 330.2, 'C165948')
    xJ, yV = J.p('A4B9')
    yDM, yDP, yC2, yC1 = J.p('A7')[1], J.p('A6')[1], J.p('B5')[1], J.p('A5')[1]
    xU = xJ + 48.26
    E = ic(s, 'TPD4E05U06', 'U7', 'TPD4E05U06DQAR', xU + 8.89, 0, 'C138714', mirror='x',
           fields={'_ref_at': (xU + 2.54, yDM - 5.08), '_val_at': (xU + 2.54, yC1 + 7.62), '_just': 'left'})
    E.y += yDM - E.p('2')[1]
    assert eq(E.p('2'), (xU, yDM)) and eq(E.p('4'), (xU, yC1)), (E.p('2'), E.p('4'))
    stub_label(s, J.p('A7'), 'USB_UP_DM', side='R', n=2)
    stub_label(s, J.p('A6'), 'USB_UP_DP', side='R', n=2)
    stub_label(s, E.p('2'), 'USB_UP_DM', side='L', n=2)
    stub_label(s, E.p('1'), 'USB_UP_DP', side='L', n=2)
    s.wire(J.p('B5'), E.p('5'))
    hang(s, 'R', 'R78', 'C25905', xJ + 22.86, yC2)
    yd = snap(yC2 + 15.24)
    s.wire(J.p('A5'), (xJ + 7.62, yC1), (xJ + 7.62, yd), (xU - 7.62, yd), (xU - 7.62, yC1), E.p('4'))
    hang(s, 'R', 'R77', 'C25905', xJ + 22.86, yd)
    g = E.p('3')
    s.wire(g, (g[0] + G, g[1]), (g[0] + G, g[1] + 5.08))
    s.power('GND', g[0] + G, g[1] + 5.08)
    yG, yS = J.p('A1B12')[1], J.p('1')[1]
    s.wire(J.p('A1B12'), (xJ + G, yG), (xJ + G, yS + 5.08))
    s.wire(J.p('1'), (xJ + G, yS))
    s.power('GND', xJ + G, yS + 5.08)
    # HOST_VBUS: rail along the top: TVS, cap, VBUS_DET divider
    xr = xU + 22.86
    s.wire(J.p('A4B9'), (xr + 45.72, yV))
    s.wire((xr, yV), (xr, yV - 5.08))
    s.label('HOST_VBUS', xr, yV - 5.08, 90)
    hang(s, 'C', 'C74', 'C52923', xr + 30.48, yV)
    r64 = hang(s, 'R', 'R64', 'C25741', xr + 45.72, yV, bottom=None)
    hang(s, 'R', 'R65', 'C25741', xr + 45.72, r64.p(2)[1], tap=False)
    nd = r64.p(2)
    s.wire(nd, (nd[0] + 20.32, nd[1]))
    t = tp(s, 'TP41', nd[0] + 12.7, nd[1], 0, 'VBUS_DET')
    s.tap(t.p(1))
    s.label('HUBA_VBUS_DET', nd[0] + 20.32, nd[1], 0)
    # --- reset supervisor (one for both hubs)
    S_ = ic(s, 'TPS3809K33', 'U6', 'TPS3809K33DBVR', 81.28, 76.2, 'C61364',
            fields={'_val_at': (73.66, 90.17), '_just': 'left'})
    vdd, rst = S_.p('3'), S_.p('2')
    s.wire((48.26, vdd[1]), vdd)
    s.power('3V3', 48.26, vdd[1])
    hang(s, 'C', 'C73', 'C1525', 58.42, vdd[1])
    s.power('GND', *S_.p('1'))
    s.wire(rst, (rst[0] + 22.86, rst[1]))
    hang(s, 'R', 'R76', 'C25741', rst[0] + 7.62, rst[1])
    t = tp(s, 'TP40', rst[0] + 15.24, rst[1], 0, 'HUB_RESET_N')
    s.tap(t.p(1))
    s.label('HUB_RESET_N', rst[0] + 22.86, rst[1], 0)
    t = tp(s, 'TP42', 27.94, 88.9, 0, 'GND')
    s.power('GND', *t.p(1))
    s.text('Straps (47k to GND): CFG_SEL = 000 / 00 internal default (individual power + OC sense, MTT, '
           'self-powered); GANG_EN, BOOST, NON_REM, PRT_SWP = 0.  PRTPWR 10k pull-downs (EN low in reset).',
           22.86, 396.24)
    s.text('Hub B upstream = hub A port 7; hub B VBUS_DET = hub A PRTPWR7 (R63 fitted, R75 DNP fallback to 3V3).',
           22.86, 401.32)
    return s


# ================================================================== root
def build():
    root = Sch('usb-hub', paper='A3', title='10-port USB-C bench hub', rev='0', date=DATE)
    d = kicad_symbol_dir()
    for lib in ('Device', 'power', 'Connector', 'Mechanical'):
        root.lib(lib, os.path.join(d, lib + '.kicad_sym'))
    root.lib('usb-hub', symbols.LIB)
    pin = power_in_sheet(root)
    buck = buck_sheet(root)
    hubs = hubs_sheet(root)
    port = port_sheet(root)
    root.sheet(pin, 'power_in', 30.48, 30.48, w=55.88, h=20.32)
    root.sheet(buck, 'buck_5v', 30.48, 66.04, w=55.88, h=20.32)
    hub_pins = []
    for k in range(1, 11):
        h, n = ('HUBA', k) if k <= 6 else ('HUBB', k - 6)
        hub_pins += ['%s_DN%d_DP' % (h, n), '%s_DN%d_DM' % (h, n), '%s_PRTPWR%d' % (h, n), '%s_OCS%d_N' % (h, n)]
    hb = root.sheet(hubs, 'hubs', 119.38, 30.48, w=63.5, left=[], right=hub_pins)
    for k in range(1, 11):
        b = root.sheet(port, 'port%d' % k, 279.4, 30.48 + 20.32 * (k - 1), w=33.02, refs=100 * k,
                       left=['DP', 'DM', 'EN', 'OCS_N'], right=[])
        h, n = ('HUBA', k) if k <= 6 else ('HUBB', k - 6)
        for lab, net in (('DP', '%s_DN%d_DP'), ('DM', '%s_DN%d_DM'), ('EN', '%s_PRTPWR%d'), ('OCS_N', '%s_OCS%d_N')):
            net = net % (h, n)
            a = b.p(lab)
            s_ = (a[0] - 7.62, a[1])
            root.wire(a, s_)
            root.label(net, s_[0], s_[1], 180)
            q = hb.p(net)
            root.wire(q, (q[0] + 7.62, q[1]))
            root.label(net, q[0] + 7.62, q[1], 0)
    for i in range(4):
        root.add('Mechanical:MountingHole', 'H%d' % (i + 1), 'M3', 38.1 + 15.24 * i, 248.92,
                 footprint='MountingHole:MountingHole_3.2mm_M3', in_bom=False)
    root.text('4x M3 mounting holes (heat-set inserts in the printed case); not assembled.', 30.48, 236.22)
    root.text('Port k: hub A downstream 1-6 -> port1-6, hub B downstream 1-4 -> port7-10; hub A port 7 -> hub B '
              'upstream. References in port k are offset by 100 x k.', 30.48, 241.3)
    return root, {'root': (root, NETS['nets']), 'power_in': (pin, NETS['sheets']['power_in']['nets']),
                  'buck_5v': (buck, NETS['sheets']['buck_5v']['nets']), 'hubs': (hubs, NETS['sheets']['hubs']['nets']),
                  'port': (port, NETS['sheets']['port']['nets'])}


def main():
    symbols.write()
    root, sheets = build()
    problems = []
    for name, (s, nets) in sheets.items():
        problems += ['%s: %s' % (name, m) for m in s.collisions() + find_merges(s, nets)]
    if problems:
        raise SystemExit('\n'.join(problems))
    root.write(os.path.join(HW, 'usb-hub.kicad_sch'))
    print('wrote', os.path.join(HW, 'usb-hub.kicad_sch'))


if __name__ == '__main__':
    main()
