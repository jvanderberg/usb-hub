"""Hub A (USB2517-JZX, U4) routing: fan-out, straps, crystal Y1, RBIAS, VDD18 / VDD18PLL, reset supervisor U6 and
the whole HUB_RESET_N net, HOST pair and VBUS_DET, ports 1-6 DP/DM/EN/OCS_N from tools/route_ports.py PORT_HANDOFF,
PRTPWR7 -> HUBB_VBUS_DET and the hub A DN7 -> hub B upstream pair. Called from tools/route_plan.py build().

Entry corridor into hub B (U5), kept to the copper hub B's module leaves free (route_hub_b.py docstring):
  - DN7 pair (U5 pins 30/31): from the west along y 164.0 (lines 163.794 / 164.206, south of TP42's and R70's GND
    vias, below C63), 45 degrees up into x 157.25 (lines 157.044 / 157.456) between the pin-29 3V3 stub and
    XTALOUT, straight north to the pins (0.044 mm jog onto the 0.5 mm pitch). Its crossover hop is at x ~148.
  - HUB_RESET_N (pin 26): west off the pad to x 154.1 in the strip x 153.95-154.48, down to a via at (154.1, 159.35),
    then L4 west at y 158.5 (under R67 / R68) to U6.
  - HUBB_VBUS_DET (pin 27): west to x 154.6, down to y 159.5, 45 degrees to y 159.8 and west under R68 (L1) to a via
    between R62 / R75 at (151.03, 159.8), which also takes the L4 run from R63.
  No other hub A copper east of x 151 on L1; on L4 only the RESET run to (154.1, 159.35).

Layer use (docs/layout-plan.md): pairs on L1 over the solid L2, 0.26 / 0.15 mm, 45 degree bends; slow lines leave
U4 on L1 to 0.45 / 0.2 vias and run on L4 (0.2 mm); crystal, PLL, RBIAS and straps on L1 (0.15 mm).

Pair polarity: every hub A pair arrives crossed relative to its U4 pins (the port handoffs and U4's pin order have
opposite handedness). The USB2517 PRT_SWP straps would swap DN1-DN7 in silicon, but they are a schematic change;
the HOST pair has no strap. So each pair crosses over once: one line hops to L4 for ~1 mm under the other, with a
GND via within 1 mm of each hop via, and the other line gets the serpentine that matches the two barrels.
Pair.crossed() decides it from the nets, so a later strap / label swap removes the hop by itself.
"""
import math

F, B = 'F.Cu', 'B.Cu'
USB_W = 0.26
H = (USB_W + 0.15) / 2 + 0.0005     # line offset from the pair centre line (gap 0.151)
SIG = 0.2                           # L4 lanes, EN / OCS_N / RESET / VBUS_DET
NARROW = 0.15                       # fan-out, crystal, straps
SV = (0.45, 0.2)
XO = 0.4                            # hop vias 0.4 mm off the pair centre line
VIA_LEN = 1.53                      # F.Cu -> B.Cu barrel (0.2104 + 1.065 + 0.2104 + inner Cu + outer Cu / 2)
BUMP = dict(h=1.0, c=0.2, w=0.3, g=0.5)
MATCH = 0.02
NECK_W, NECK_H = 0.2, 0.1755      # <= 1.5 mm neck through a via pinch (layout-plan s3 allows short 0.2 mm necks)

# U4 pad centres the coordinates below were drawn against (placement change -> stop, re-derive)
EXPECT = {'1': (123.5, 153.25), '16': (123.5, 160.75), '17': (124.25, 161.5), '32': (131.75, 161.5),
          '33': (132.5, 160.75), '48': (132.5, 153.25), '49': (131.75, 152.5), '64': (124.25, 152.5)}


def T(r, layer, w, *pts, net=None):
    return r.track(layer, w, *pts, net=net)


def U(n):
    return ('U4', str(n))


# ---------------------------------------------------------------- crystal, PLL, RBIAS, VDD18, straps (L1)
def route_local(r):
    # XTAL1 (61): up, NW 45 degrees into Y1 pad 1; on to C60 and R40 pad 1
    T(r, F, NARROW, U(61), (125.75, 151.9), (123.2, 149.35), ('Y1', '1'))
    T(r, F, NARROW, ('Y1', '1'), (121.95, 148.85), (121.32, 148.22), ('C60', '1'))
    T(r, F, NARROW, ('C60', '1'), (121.32, 147.9), (120.47, 147.05), ('R40', '1'))
    # XTAL2 (60): straight north past Y1's east side into pad 3 (Y1's GND via sits between pads 1 / 2); pad 3 ->
    # C61, and over pad 4 to R40 pad 2
    xt2 = r.net('Y1', '3')
    T(r, F, NARROW, U(60), (126.25, 151.9), (126.35, 151.8), (126.35, 147.15), ('Y1', '3'))
    T(r, F, NARROW, (125.02, 146.8), (125.02, 146.2), (121.73, 146.2), ('R40', '2'), net=xt2)
    T(r, F, NARROW, ('C61', '1'), (125.02, 146.2), net=xt2)
    # GND guard on L1 round Y1, C60, C61 and R40 (stitched by Y1's, C60's and C61's GND vias); nothing of hub A runs
    # on L4 under it (VBUS_DET passes north of C61 at y 143.6)
    r.zone(r.net('Y1', '2'), F, [(119.6, 144.15), (126.2, 144.15), (126.2, 149.9), (119.6, 149.9)], prio=5,
           name='F_GND_XTAL_A', clearance=0.2)
    # VDD18PLL (62) -> C59, RBIAS (63) -> R41
    T(r, F, NARROW, U(62), (125.25, 151.9), (123.55, 150.2), (121.55, 150.2), ('C59', '1'))
    T(r, F, NARROW, U(63), (124.75, 151.9), (124.2, 151.35), (122.25, 151.35), ('R41', '1'))
    # VDD18 (25) -> C58
    T(r, F, SIG, U(25), (128.25, 163.85), ('C58', '1'))
    # PRT_SWP7 (15) -> R55, PRT_SWP6 (17) -> R54, PRT_SWP5 (31) -> R53
    T(r, F, NARROW, U(15), (123.1, 160.25), (122.65, 160.7), ('R55', '1'))
    T(r, F, NARROW, U(17), (124.25, 163.9), ('R54', '1'))
    T(r, F, NARROW, U(31), (131.25, 163.5), (131.6, 163.85), ('R53', '1'))
    # top-right corner straps. PRT_SWP2 (49) -> R50 and BOOST1 (48) -> R48 on L1; PRT_SWP3 (47), BOOST0 (50) and
    # PRT_SWP1 (51) are boxed in (pin 46's and pin 52's 3V3 runs, C54): vias, L4, vias beside the col 2 resistors
    T(r, F, NARROW, U(49), (134.07, 152.5), ('R50', '1'))
    T(r, F, NARROW, U(48), (133.6, 153.25), (134.25, 153.9), ('R48', '1'))
    hop(r, U(47), [(133.35, 153.75)], [(136.87, 153.7)], ('R51', '1'))
    hop(r, U(50), [(131.25, 151.65)], [(135.0, 151.65), (135.75, 152.4), (136.87, 152.4)], ('R47', '1'))
    hop(r, U(51), [(130.75, 151.1)], [(131.25, 150.6), (136.52, 150.6), (136.87, 150.95)],
        ('R49', '1'))


def hop(r, pad, l1, l4, dst=None, l1b=(), w=NARROW):
    """pad -(L1 l1, last point a via)- L4 l4 (last point a via) -(L1 l1b)- dst pad. dst None: the L4 run ends at a
    via the caller continues from (e.g. a port handoff via, which already exists: pass dst='handoff')."""
    net = r.net(*pad)
    T(r, F, w, pad, *l1, net=net)
    r.via(l1[-1], net, *SV)
    T(r, B, SIG, l1[-1], *l4, net=net)
    if dst == 'handoff':
        return
    r.via(l4[-1], net, *SV)
    if dst:
        T(r, F, w, l4[-1], *l1b, dst, net=net)


# ---------------------------------------------------------------- bottom row: PRTPWR / OCS_N escape vias
# Port 1-3 lines (22, 23, 26-29) leave their vias north under the chip, so the vias of 22 / 27 / 29 sit 0.3 mm lower
# than their neighbours' and their lines pass between those (1.0 mm apart); ports 4 / 5 (20, 21, 30) leave south.
BOT_VIA = {20: (125.7, 162.6), 21: (126.2, 163.3), 22: (126.7, 162.75), 23: (127.2, 162.4),
           26: (128.75, 162.4), 27: (129.25, 162.75), 28: (129.75, 162.4), 29: (130.25, 162.75),
           30: (130.75, 163.4)}


def bottom_escapes(r):
    for pin, at in BOT_VIA.items():
        net = r.net(*U(pin))
        T(r, F, NARROW, U(pin), at, net=net)
        r.via(at, net, *SV)


def lane(r, net_pin, pts):
    T(r, B, SIG, *pts, net=r.net(*U(net_pin)))


def lanes_west(r, H_):
    """L4, ports 1-3: north off the vias, west under the chip at y 159.45-161.2 (nested: the line of the
    eastern-most via runs northern-most), ports 1 / 2 north up the x 114.65-115.7 corridor (west of the L4 3V3
    trunk), port 3 straight on west. Port 2 arrives from the north (OCS2 sits south-west of EN2), OCS1 from the east,
    EN1 from the south."""
    e1, e2, e3 = H_[1], H_[2], H_[3]
    o3, p3 = e3['OCS_N'], e3['EN']
    # OCS3: up to y 160.6 before the port's GND via at (110.15, 161.4)
    lane(r, 22, [BOT_VIA[22], (126.7, 161.2), (o3[0] + 2.35, 161.2), (o3[0] + 1.75, o3[1]), o3])
    lane(r, 23, [BOT_VIA[23], (127.2, 160.85), (p3[0], 160.85), p3])
    p2, o2 = e2['EN'], e2['OCS_N']
    # corridor x 114.65-115.7: over L3's 5V_BUS plane, clear of the 3V3 island A gap at x 116.5
    lane(r, 26, [BOT_VIA[26], (128.75, 160.5), (114.65, 160.5), (114.65, 135.0), (p2[0], 135.0), p2])
    lane(r, 27, [BOT_VIA[27], (129.25, 160.15), (115.0, 160.15), (115.0, 134.65), (o2[0], 134.65), o2])
    o1, p1 = e1['OCS_N'], e1['EN']
    lane(r, 28, [BOT_VIA[28], (129.75, 159.8), (115.35, 159.8), (115.35, o1[1]), o1])
    lane(r, 29, [BOT_VIA[29], (130.25, 159.45), (115.7, 159.45), (115.7, p1[1]), p1])


def lanes_south(r, H_):
    """L4, ports 4-6. Port 4: west off the vias, then SW (EN4 from the east, OCS4 from the north). Port 5: PRTPWR5
    straight down and SW; OCS5 from its channel via straight down x 133.19 and SW. Port 6: from the channel vias
    SE, down x 133.9 / 134.3, east at y 167.9 / 167.5; OCS6 drops south first and passes under the EN6 via."""
    e4, e5, e6 = H_[4], H_[5], H_[6]
    p4, o4 = e4['EN'], e4['OCS_N']
    # west, down x 119.5 / 120.0 (clear of the DN4 crossover at y 164.5-166), west at y 167.5 / 167.9, down
    lane(r, 20, [BOT_VIA[20], (119.5, 162.6), (119.5, 167.5), (113.0, 167.5), (113.0, 168.5),
                 (p4[0], 168.5 + 113.0 - p4[0]), p4])
    lane(r, 21, [BOT_VIA[21], (120.0, 163.3), (120.0, 167.9), (113.6, 167.9), (113.6, 169.5), (o4[0], 170.5), o4])
    p5, o5 = e5['EN'], e5['OCS_N']
    lane(r, 30, [BOT_VIA[30], (130.75, 169.25), (128.0, 172.0), p5])
    lane(r, 35, [CH[35], (133.19, 171.3), (o5[0], 171.3 + 133.19 - o5[0]), o5])
    p6, o6 = e6['EN'], e6['OCS_N']
    lane(r, 39, [CH[39], (133.7, 157.72), (134.3, 158.32), (134.3, 167.5), (p6[0], 167.5), p6])
    lane(r, 38, [CH[38], (133.9, 159.02), (133.9, 167.9), (144.0, 167.9), (144.0, 173.6), (o6[0], 173.6), o6])


VBUS_DET_VIAS = ((120.0, 143.6), (119.3, 113.3))


def route_vbus_det(r, H_):
    """HUBA_VBUS_DET, U4 pin 44 -> HOST handoff via: L4 west under the top pins and north at x 130.0 (west of the
    PRT_SWP1 / BOOST0 vias), west at y 143.6 (north of the crystal), up to L1 west of the HOST pair, north beside it
    at x 118.55 / 119.3, back to L4 east of the 3V3 trunk and east at y 113.3 to the handoff via"""
    net = r.net(*U(44))
    a, b = VBUS_DET_VIAS
    T(r, B, SIG, CH[44], (132.5, 155.25), (132.1, 154.85), (130.0, 154.85), (130.0, 144.6), (129.0, 143.6), a, net=net)
    r.via(a, net, *SV)
    T(r, F, SIG, a, (118.55, 143.6), (118.55, 122.75), (119.3, 122.0), b, net=net)
    r.via(b, net, *SV)
    T(r, B, SIG, b, H_['HOST']['VBUS_DET'], net=net)


# ---------------------------------------------------------------- right column (pins 33-45)
# The strap resistors sit 1.25-2 mm below their pins and C53's 3V3 via (route_plan.route_hub_power) fills the
# channel at y 156. On L1: 42 -> R43, 40 -> R44, 36 -> R63, 34 -> R46, 33 -> R52. The rest drop to vias in the
# channel (x 133.175 / 133.55, staggered) and leave on L4: 45 -> R45 (via NE of it, L1 between the C53 / R45 rows),
# 44 VBUS_DET west under the chip, 43 RESET east, 41 -> R42 (via under it), 39 / 38 south to port 6, 35 west then
# south to port 5.
CH = {45: (133.19, 154.75), 44: (133.55, 155.25), 43: (133.19, 155.75), 41: (133.19, 156.75),
      39: (133.19, 157.72), 38: (133.2, 158.32), 35: (133.19, 159.75)}
R45_VIA, R42_VIA, HUBB_VIA_A, HUBB_VIA_B = (136.75, 156.125), (136.87, 158.6), (136.5, 160.5), (151.03, 159.8)
RESET_VIA_U6, RESET_VIA_U5 = (144.9, 158.9), (154.1, 159.35)


def right_column(r):
    for pin, at in CH.items():
        net = r.net(*U(pin))
        T(r, F, NARROW, U(pin), at, net=net)
        r.via(at, net, *SV)
    T(r, F, NARROW, U(42), (133.6, 156.25), (134.0, 156.65), (134.0, 157.65), (134.3, 157.95), ('R43', '1'))
    T(r, F, NARROW, U(40), (133.66, 157.25), (133.66, 158.9), (134.0, 159.24), ('R44', '1'))
    T(r, F, NARROW, U(36), (133.5, 159.25), (134.4, 160.15), ('R63', '1'))
    T(r, F, NARROW, U(34), (133.0, 160.25), (133.5, 160.75), (133.5, 161.4), (133.85, 161.75), ('R46', '1'))
    T(r, F, NARROW, U(33), (132.9, 160.75), (133.05, 160.9), (133.05, 162.6), (133.45, 163.0), ('R52', '1'))
    # R45: L4 from the channel through the col 1 GND via line (gap at y 154.875) to a via NE of R45, back on L1
    # between the C53 and R45 rows
    n45 = r.net(*U(45))
    T(r, B, SIG, CH[45], (135.6, 154.75), (135.725, 154.875), (136.5, 154.875), (136.75, 155.125), R45_VIA, net=n45)
    r.via(R45_VIA, n45, *SV)
    T(r, F, NARROW, R45_VIA, (134.9, 156.125), (134.567, 156.458), ('R45', '1'), net=n45)
    # R42 (col 2): under the RESET lane, through the col 1 gap at y 158.625 to a via under R42
    n41 = r.net(*U(41))
    T(r, B, SIG, CH[41], (134.6, 156.75), (134.9, 157.05), (134.9, 158.1), (135.4, 158.6), R42_VIA, net=n41)
    r.via(R42_VIA, n41, *SV)
    T(r, F, NARROW, R42_VIA, ('R42', '1'), net=n41)
    # PRTPWR7 strap's far side: R63 pad 2 (HUBB_VBUS_DET) -> via -> L4 east under U6's row -> via between R62 / R75
    hubb = r.net('R63', '2')
    T(r, F, SIG, ('R63', '2'), HUBB_VIA_A, net=hubb)
    r.via(HUBB_VIA_A, hubb, *SV)
    T(r, B, SIG, HUBB_VIA_A, (148.4, 160.5), (149.1, 159.8), HUBB_VIA_B, net=hubb)
    r.via(HUBB_VIA_B, hubb, *SV)
    T(r, F, NARROW, ('R62', '1'), HUBB_VIA_B, ('R75', '1'), net=hubb)
    # U5 pin 27 (hub B VBUS_DET): west into the strip, down, west under R68 to the same via
    T(r, F, NARROW, ('U5', '27'), (154.6, 159.0), (154.6, 159.5), (154.3, 159.8), HUBB_VIA_B, net=hubb)


def route_reset(r):
    """HUB_RESET_N: U6 (TPS3809) pin 2 -> R76 / TP40 on L1; L4 from U4 pin 43's channel via, through the col 1 gap
    at y 157.375, east to a via on the U6 - R76 run, on east under R67 / R68 to a via in hub B's strip -> U5 pin 26"""
    rst = r.net('U6', '2')
    T(r, F, NARROW, ('U6', '2'), (145.4, 156.05), (144.9, 156.55), (144.9, 159.67), ('R76', '1'))
    T(r, F, NARROW, ('R76', '1'), (143.567, 161.0), (143.0, 161.567), ('TP40', '1'))
    T(r, B, SIG, CH[43], (133.75, 155.75), (134.05, 155.45), (135.3, 155.45), (135.3, 156.95), (135.725, 157.375),
      (144.4, 157.375), (144.9, 157.875), RESET_VIA_U6, net=rst)
    r.via(RESET_VIA_U6, rst, *SV)
    T(r, B, SIG, RESET_VIA_U6, (145.3, 158.5), (153.6, 158.5), (154.1, 159.0), RESET_VIA_U5, net=rst)
    r.via(RESET_VIA_U5, rst, *SV)
    T(r, F, NARROW, ('U5', '26'), (154.1, 158.5), RESET_VIA_U5, net=rst)


# ---------------------------------------------------------------- USB pairs
def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    return (dx / n, dy / n), n


def _rn(t):
    """right-hand normal of travel direction t (board axes, y down: east -> south)"""
    return (-t[1], t[0])


def _off(C, i, d):
    """vertex i of the polyline C offset by d to the right of travel (mitred corners)"""
    if i == 0 or i == len(C) - 1:
        t, _ = _unit(C[0], C[1]) if i == 0 else _unit(C[-2], C[-1])
        n = _rn(t)
        return (C[i][0] + d * n[0], C[i][1] + d * n[1])
    n1, n2 = _rn(_unit(C[i - 1], C[i])[0]), _rn(_unit(C[i], C[i + 1])[0])
    mx, my = n1[0] + n2[0], n1[1] + n2[1]
    m = math.hypot(mx, my)
    mx, my = mx / m, my / m
    c = mx * n1[0] + my * n1[1]
    return (C[i][0] + d * mx / c, C[i][1] + d * my / c)


def _plen(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _bumps(extra, h=None):
    """bump heights adding `extra` mm: full rectangular bumps (45 degree corners, height h), then one smaller one"""
    h, c = h or BUMP['h'], BUMP['c']
    rect = lambda hh: 2 * hh - 4 * c * (2 - math.sqrt(2))
    out = [h] * int(extra // rect(h))
    rest = extra - rect(h) * len(out)
    if rest > 1e-4:
        if rest >= rect(2 * c):
            out.append((rest + 4 * c * (2 - math.sqrt(2))) / 2)
        else:
            out.append(-rest / (2 * (math.sqrt(2) - 1)))      # negative: a trapezoid bump of that height
    return out


def _bump_pts(hs):
    """local (du, dv) points of the bumps (dv outward), starting and ending on the line (dv 0)"""
    c, w, g = BUMP['c'], BUMP['w'], BUMP['g']
    pts, u = [], 0.0
    for k, hb in enumerate(hs):
        if k:
            u += g
        if hb > 0:
            shape = [(0, 0), (c, c), (c, hb - c), (2 * c, hb), (2 * c + w, hb), (3 * c + w, hb - c), (3 * c + w, c),
                     (4 * c + w, 0)]
        else:
            hb = -hb
            shape = [(0, 0), (hb, hb), (hb + w, hb), (2 * hb + w, 0)]
        pts += [(u + a, b) for a, b in shape]
        u += shape[-1][0]
    return pts


class Pair:
    """A D+/D- pair drawn as a centre line C (travel hub A -> far end) with the two lines at +-H (+-NECK_H, 0.2 mm
    wide, on the segments listed in `neck`: their first and last segments taper). dp_side: D+ to the right (+1) or
    left (-1) of travel at the start. hop = (segment, u, 'DP'/'DM'): that line crosses under the other on L4 (one
    crossover: the pair's two ends have opposite handedness); serp = (segment, u, 'DP'/'DM'): the serpentine on the
    shorter line, bumping away from its partner. start / end: {'DP': pad or point, 'DM': ...}; a pad end gets a 45
    degree jog from the pad pitch to the line pitch, a point end must sit on the line (a port handoff)."""

    def __init__(self, r, name, C, dp_side, start, end, hop, serp, neck=(), lead=0.0, bump_h=None):
        self.r, self.name, self.C, self.neck, self.lead = r, name, C, set(neck), lead
        self.bump_h = bump_h
        self.dp, self.dm = r.net(*start['DP']), r.net(*start['DM'])
        self.start = {self.dp: start['DP'], self.dm: start['DM']}
        self.end = {self.dp: end['DP'], self.dm: end['DM']}
        self.dp_side, self.hop, self.serp = dp_side, hop, serp
        self.geom(0.0)
        L = self.lengths()
        short = min(L, key=L.get)
        assert self.net_of(serp[2]) == short, '%s: serpentine on %s but %s is the shorter line (%s)' % (
            name, serp[2], short, {k: round(v, 3) for k, v in L.items()})
        self.extra = abs(L[self.dp] - L[self.dm])
        self.geom(self.extra)
        L = self.lengths()
        assert abs(L[self.dp] - L[self.dm]) < MATCH, (name, L)

    def net_of(self, which):
        return self.dp if which == 'DP' else self.dm

    def h(self, i):
        """line offset at vertex i"""
        segs = {i - 1, i} & set(range(len(self.C) - 1))
        inner = all(s in self.neck for s in segs) and segs
        return NECK_H if inner else H

    def w(self, seg):
        return NECK_W if seg in self.neck else USB_W

    def _jog(self, pad, at, t, inward, lead=0.0):
        """points from pad `pad` to lane point `at` (travel t at that end): straight along t at the pad's offset, then
        45 degrees onto the lane, `lead` mm short of `at` (per line at the start, so that neighbouring lines step
        one after the other and never close up); inward: the pad lies behind `at` (start) or after (end)"""
        r = self.r
        p = r.P(*pad) if isinstance(pad[0], str) else pad
        n = _rn(t)
        dv = (at[0] - p[0]) * n[0] + (at[1] - p[1]) * n[1]
        if abs(dv) < 1e-6:
            return [p]
        k = lead + abs(dv)
        sg = -1 if inward else 1
        q1 = (at[0] + sg * k * t[0] - dv * n[0], at[1] + sg * k * t[1] - dv * n[1])
        q2 = (at[0] + sg * lead * t[0], at[1] + sg * lead * t[1])
        return [p, q1] + ([q2] if lead else [])

    def geom(self, extra):
        C, r = self.C, self.r
        side = {self.dp: self.dp_side, self.dm: -self.dp_side}
        self.paths, self.vias = {}, []
        t0, _ = _unit(C[0], C[1])
        for net in (self.dp, self.dm):
            s = _off(C, 0, side[net] * self.h(0))
            sp = self.start[net]
            lead = self.lead.get('DP' if net == self.dp else 'DM', 0.0) if isinstance(self.lead, dict) else self.lead
            pts = self._jog(sp, s, t0, True, lead) if isinstance(sp[0], str) else []
            self.paths[net] = [[F, pts + [s], [0]]]           # [layer, points, segment index per point]
        feats = [(self.hop[0], self.hop[1], 'hop', self.net_of(self.hop[2])),
                 (self.serp[0], self.serp[1], 'serp', self.net_of(self.serp[2]))]
        for i in range(len(C) - 1):
            if i:
                for net in side:
                    self.paths[net][-1][1].append(_off(C, i, side[net] * self.h(i)))
            t, _ = _unit(C[i], C[i + 1])
            n = _rn(t)

            def P(u, v, i=i, t=t, n=n):
                return (C[i][0] + u * t[0] + v * n[0], C[i][1] + u * t[1] + v * n[1])
            for seg, u0, kind, net in sorted(f for f in feats if f[0] == i):
                if kind == 'hop':
                    a, b = net, (self.dm if net == self.dp else self.dp)
                    sa = side[a]
                    j = XO - H
                    lb = 2 * j + 2 * XO
                    ub = lb / 2 - H
                    v1, v2 = P(u0 + j, sa * XO), P(u0 + j + 2 * XO, -sa * XO)
                    self.paths[a][-1][1] += [P(u0, sa * H), v1]
                    self.paths[a] += [[B, [v1, v2]], [F, [v2, P(u0 + lb, -sa * H)]]]
                    self.paths[b][-1][1] += [P(u0, -sa * H), P(u0 + ub, -sa * H), P(u0 + ub + 2 * H, sa * H),
                                             P(u0 + lb, sa * H)]
                    side[a], side[b] = -sa, sa
                    self.vias += [(v1, a, P, u0 + j, sa * XO, sa), (v2, a, P, u0 + j + 2 * XO, -sa * XO, -sa)]
                elif extra > 0:
                    s = side[net]
                    self.paths[net][-1][1] += [P(u0 + du, s * (H + dv)) for du, dv in _bump_pts(_bumps(extra, self.bump_h))]
        tn, _ = _unit(C[-2], C[-1])
        for net in side:
            e = _off(C, len(C) - 1, side[net] * self.h(len(C) - 1))
            want = self.end[net]
            if isinstance(want[0], str):
                self.paths[net][-1][1] += [e] + list(reversed(self._jog(want, e, tn, False)))
            else:
                assert math.dist(e, want) < 2e-3, '%s: %s ends at %s, handoff %s' % (self.name, net, e, want)
                self.paths[net][-1][1].append(want)
        assert side[self.dp] == 1, '%s: D+ must end on the right of travel (crossover count is wrong)' % self.name

    def lengths(self):
        return {net: sum(_plen(p[1]) for p in self.paths[net]) + VIA_LEN * sum(1 for v in self.vias if v[1] == net)
                for net in self.paths}

    def _widths(self, pts):
        """per-segment width: a segment is necked if both its ends lie on a necked centre-line segment's span"""
        if not self.neck:
            return [USB_W] * (len(pts) - 1)
        out = []
        for a, b in zip(pts, pts[1:]):
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            k = min(range(len(self.C) - 1), key=lambda s: _seg_dist(m, self.C[s], self.C[s + 1]))
            out.append(self.w(k))
        return out

    def draw(self):
        r = self.r
        for net, pieces in self.paths.items():
            for layer, pts, *_ in pieces:
                pts = [r.P(*q) if isinstance(q[0], str) else q for q in pts]
                ws = self._widths(pts) if layer == F else [USB_W] * (len(pts) - 1)
                for (a, b), wd in zip(zip(pts, pts[1:]), ws):
                    if math.dist(a, b) > 1e-6:
                        r.track(layer, wd, a, b, net=net)
        for v in self.vias:
            r.via(v[0], v[1], *SV)
        L = self.lengths()
        r.log.append('hub A %s: %s %.3f / %s %.3f mm (%d hop vias x %.2f mm counted), serpentine +%.3f on %s, '
                     'mismatch %.3f' % (self.name, self.dp, L[self.dp], self.dm, L[self.dm], len(self.vias), VIA_LEN,
                                        self.extra, self.net_of(self.serp[2]), abs(L[self.dp] - L[self.dm])))

    def gnd_vias(self, gnd):
        """a GND via within 1 mm of each hop via, outside the pair (an existing one counts)"""
        r = self.r
        have = [(v['x'], v['y']) for v in r.B.get('vias', []) if v['net'] == gnd]
        have += [tuple(v['at']) for v in r.vias if v['net'] == gnd]
        for at, net, P, u, v, s in self.vias:
            if any(math.dist(q, at) <= 1.0 for q in have):
                continue
            cands = [(0.0, d) for d in (0.6, 0.65, 0.7, 0.75, 0.8, 0.9)]
            cands += [(du, d) for d in (0.55, 0.6, 0.7) for du in (0.25, -0.25, 0.4, -0.4, 0.55, -0.55)]
            for du, d in cands:
                q = P(u + du, v + s * d)
                if math.dist(q, at) <= 1.0 and r.via(q, gnd, *SV, quiet=True):
                    have.append(q)
                    break
            else:
                r.rejected += 1
                r.log.append('REJECTED hub A %s: no GND via within 1 mm of the hop via %s' % (self.name, at))


def _seg_dist(p, a, b):
    (t, L) = _unit(a, b)
    u = max(0.0, min(L, (p[0] - a[0]) * t[0] + (p[1] - a[1]) * t[1]))
    return math.dist(p, (a[0] + u * t[0], a[1] + u * t[1]))


def pairs(r, H_):
    """Centre lines, hub A -> far end (docs/layout-plan.md s5 lanes). Left pins: DN1 / DN2 west through the C56 / C50
    via pinch (necked 0.2 / 0.15 mm for 1.4 mm), north up x 117.5 / 116.4; DN3 / DN4 west under C50, south down
    x 116.95 / 117.8; DN5 south down x 121.2, east at y 167.8 to port 5. Top pins: HOST north, west at y 142.6, north
    up x 119.6 then x 120.795; DN7 / DN6 north-east, east at y 148.275 / 149.395, south at x 140.62 / 139.5; DN7 east
    at y 164.0 and north into U5 pins 30 / 31; DN6 east at y 169.2 to port 6."""
    def pins(dp, dm, ref='U4'):
        return {'DP': (ref, str(dp)), 'DM': (ref, str(dm))}

    def hand(k):
        return {'DP': H_[k]['DP'], 'DM': H_[k]['DM']}
    out = []
    C = [(127.0, 151.6), (127.0, 143.0), (126.6, 142.6), (120.0, 142.6), (119.6, 142.2), (119.6, 124.6),
         (120.795, 123.405), (120.795, H_['HOST']['DP'][1])]
    out.append(Pair(r, 'HOST', C, -1, pins(59, 58), hand('HOST'), (6, 5.5, 'DM'), (2, 1.0, 'DP')))
    C = [(128.5, 151.6), (128.5, 149.69), (129.915, 148.275), (140.22, 148.275), (140.62, 148.675), (140.62, 163.6),
         (141.02, 164.0), (156.85, 164.0), (157.25, 163.6), (157.25, 160.9)]
    out.append(Pair(r, 'DN7 -> U5', C, -1, pins(56, 55), pins(31, 30, 'U5'), (6, 7.0, 'DM'), (4, 3.0, 'DP')))
    C = [(129.5, 151.6), (129.5, 150.27), (130.375, 149.395), (139.1, 149.395), (139.5, 149.795), (139.5, 168.8),
         (139.9, 169.2), (150.105, 169.2), (150.505, 169.6), (150.505, H_[6]['DP'][1])]
    out.append(Pair(r, 'DN6 -> port 6', C, -1, pins(54, 53), hand(6), (6, 7.5, 'DM'), (6, 1.0, 'DP')))
    C = [(122.6, 158.5), (121.6, 158.5), (121.2, 158.9), (121.2, 167.4), (121.6, 167.8), (132.505, 167.8),
         (132.905, 168.2), (132.905, H_[5]['DP'][1])]
    out.append(Pair(r, 'DN5 -> port 5', C, -1, pins(12, 11), hand(5), (4, 5.0, 'DP'), (4, 0.3, 'DM')))
    # left pins 1-9: the lines step from the 0.5 mm pin pitch onto their lanes one after the other (leads), the line
    # moving away from its neighbour first
    C = [(122.4, 156.15), (117.35, 156.15), (116.95, 156.55), (116.95, 162.805), (116.55, 163.205),
         (H_[3]['DP'][0], 163.205)]
    out.append(Pair(r, 'DN3 -> port 3', C, -1, pins(7, 6), hand(3), (4, 1.5, 'DP'), (2, 1.0, 'DM'),
                    lead={'DM': 0.3555, 'DP': 0.55}))
    C = [(122.4, 156.976), (118.2, 156.976), (117.8, 157.376), (117.8, 169.2), (117.4, 169.6), (115.605, 169.6),
         (115.205, 170.0), (115.205, H_[4]['DP'][1])]
    out.append(Pair(r, 'DN4 -> port 4', C, -1, pins(9, 8), hand(4), (2, 7.3, 'DP'), (2, 9.0, 'DM'),
                    lead={'DM': 0.88, 'DP': 0.8315}))
    # DN1 passes the C56 GND via at full width (0.2 mm to spare); DN2 necks under it, past C50's 3V3 via
    C = [(122.0, 153.16), (117.9, 153.16), (117.5, 152.76), (117.5, 120.605), (117.1, 120.205),
         (H_[1]['DP'][0], 120.205)]
    out.append(Pair(r, 'DN1 -> port 1', C, -1, pins(2, 1), hand(1), (4, 3.2, 'DM'), (4, 0.3, 'DP'),
                    bump_h=1.5, lead={'DM': 0.9045, 'DP': 0.52}))
    C = [(121.5, 153.99), (121.25, 153.99), (121.05, 153.921), (119.85, 153.921), (119.65, 153.99), (116.8, 153.99),
         (116.4, 153.59), (116.4, 142.105), (116.0, 141.705), (H_[2]['DP'][0], 141.705)]
    out.append(Pair(r, 'DN2 -> port 2', C, -1, pins(4, 3), hand(2), (8, 2.2, 'DM'), (6, 2.0, 'DP'), neck=(1, 2, 3),
                    lead={'DM': 0.5545, 'DP': 0.0}))
    return out


def route(r):
    import route_ports
    H_ = route_ports.PORT_HANDOFF
    for k in (1, 2, 3, 4, 5, 6, 'HOST'):
        assert k in H_, 'route_ports has not run (PORT_HANDOFF[%r])' % (k,)
    for num, want in EXPECT.items():
        assert math.dist(r.P('U4', num), want) < 0.02, ('U4 moved: pad %s at %s, expected %s: re-derive '
                                                       'route_hub_a.py' % (num, r.P('U4', num), want))
    route_local(r)
    bottom_escapes(r)
    right_column(r)
    route_reset(r)
    lanes_west(r, H_)
    lanes_south(r, H_)
    route_vbus_det(r, H_)
    gnd = r.net('U4', '13')
    ps = pairs(r, H_)
    for p in ps:
        p.draw()
    for p in ps:
        p.gnd_vias(gnd)
