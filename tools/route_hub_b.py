"""Hub B (USB2514B, U5) routing: fan-out, straps, crystal Y2, RBIAS, CRFILT/PLLFILT, ports 7-10 DP/DM/EN/OCS_N from
tools/route_ports.py PORT_HANDOFF. Called from tools/route_plan.py build() (after the ports and hub A).

Not routed here (hub A's module routes them into U5): HUB_RESET_N (pin 26), HUBB_VBUS_DET (pin 27) and the hub A
DN7 -> U5 upstream pair (pins 30/31). Copper this module keeps OFF, so hub A has an entry:
  - pins 30/31 (UP pair): straight south between the pin-29 3V3 stub to C63 (x <= 156.6, route_hub_power) and
    XTALOUT (x 158.0 from the pin down to y 162.26, then east), then west below C63 (y > 162.8). This module puts
    nothing west of x 157.8 below the bottom pin row except the pin-28 strap (y 160.55 from x 156.0 west to 155.1,
    then down x 154.85 into R70 at x 154.58-155.12, y 161.28-161.85).
  - pins 26/27: they cannot leave straight west (R68 sits level with pin 27, and the pin-25 strap crosses to it at
    x 153.6-154.13, y 158.0-158.9). They leave south off the pad ends through the strip x 153.95-154.48 from
    y 158.3, then west below R68 through the free corner x < 154.5, y 159.5-161.2.

Layer use (docs/layout-plan.md): pairs on L1 over the solid L2, 0.26 / 0.15 mm, 45 degree bends. Slow lines leave
U5 on L1 to 0.45/0.2 vias and run on L4 (0.2 mm). Crystal, RBIAS and the filter caps on L1 only (0.15 mm), nothing
of this module on L4 under Y2 or its traces.

Pair polarity. Every port handoff (route_ports.py) has D- on the left of the pair's travel into the board, and U5
has D+ on the left of the travel into its pins, and the USB2514B has no D+/D- swap strap (hub-design.md s1, EEPROM
only). A pair keeps its handedness on one layer, so each of the four pairs crosses over once: one line hops to L4
for 1.1 mm (two vias, 0.4 mm off the centre line) under the other, with a GND via within 1 mm of each signal via.
The hop line's two barrels (VIA_LEN each, counted in KiCad's net length) and the bends are matched by a serpentine
on the other line, near the crossover.
"""
import math

F, B = 'F.Cu', 'B.Cu'
USB_W, USB_GAP = 0.26, 0.15     # route_ports.py USB_W / USB_GAP (layout-plan s3 estimate)
H = (USB_W + USB_GAP) / 2 + 0.0005    # line offset from the centre line: gap 0.151 (4-decimal coordinates on the
                                      # 45 degree runs would otherwise round a 0.150 gap to 0.1499); the last
                                      # segment closes onto the handoff's exact 0.41 pitch
SIG = 0.2                       # slow lines (EN / OCS_N), L4 lanes
NARROW = 0.15                   # crystal / filter / bias / strap lines in the 0.5 mm pitch fan-out
SV = (0.45, 0.2)
XO = 0.4                        # crossover: hop vias 0.4 mm off the pair centre line
VIA_LEN = 1.53                  # F.Cu -> B.Cu barrel (JLC04161H-7628: 0.2104 + 1.065 + 0.2104 + inner Cu + outer Cu/2)
BUMP = dict(h=1.0, c=0.2, w=0.3, g=0.5)
MATCH = 0.02                    # pair length match target (mm), well inside the 0.15 mm brief

# U5 pad centres the coordinates below were drawn against (placement change -> stop, re-derive)
EXPECT = {'1': (160.97, 159.0), '9': (160.97, 155.0), '12': (159.0, 154.03), '18': (156.0, 154.03),
          '19': (155.03, 155.0), '27': (155.03, 159.0), '28': (156.0, 159.97), '36': (160.0, 159.97)}


# ---------------------------------------------------------------- geometry
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


def _rect_extra(h, c):
    return 2 * h - 4 * c * (2 - math.sqrt(2))


def _bumps(extra):
    """bump heights adding `extra` mm: full rectangular bumps (45 degree corners), then one smaller one"""
    h, c = BUMP['h'], BUMP['c']
    full = _rect_extra(h, c)
    out = [h] * int(extra // full)
    rest = extra - full * len(out)
    if rest > 1e-4:
        if rest >= _rect_extra(2 * c, c):
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


def _chamfer(pts, c=0.4):
    """45 degree corners (size c) on the right-angle corners of a lane"""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        (t1, l1), (t2, l2) = _unit(pts[i - 1], pts[i]), _unit(pts[i], pts[i + 1])
        if abs(t1[0] * t2[0] + t1[1] * t2[1]) > 1e-6:
            out.append(pts[i])
            continue
        k = min(c, l1 / 2, l2 / 2)
        out += [(pts[i][0] - k * t1[0], pts[i][1] - k * t1[1]), (pts[i][0] + k * t2[0], pts[i][1] + k * t2[1])]
    return out + [pts[-1]]


# ---------------------------------------------------------------- coupled pair with one crossover
class Pair:
    """A D+/D- pair from U5's pins (east) to a port handoff, drawn as a centre line C (travel hub -> port, first
    segment due east) with the two lines at +-H. swap = (segment, u, net that hops); serp = (segment, u, net that
    gets the serpentine: it must be the shorter one, and it bumps away from its partner)."""

    def __init__(self, r, name, dp_pad, dm_pad, C, dp_side, swap, serp, ends, lead=None):
        self.r, self.name, self.C = r, name, C
        self.lead = lead or {}          # {'DP'/'DM': mm}: that line's pad jog ends this far before the start point
        self.dp, self.dm = r.net(*dp_pad), r.net(*dm_pad)
        self.pads = {self.dp: dp_pad, self.dm: dm_pad}
        self.dp_side, self.swap, self.serp, self.ends = dp_side, swap, serp, ends
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

    def geom(self, extra):
        C, r = self.C, self.r
        side = {self.dp: self.dp_side, self.dm: -self.dp_side}
        self.paths, self.vias = {}, []
        for net in (self.dp, self.dm):
            p = r.P(*self.pads[net])
            s = _off(C, 0, side[net] * H)
            dy = s[1] - p[1]
            k = self.lead.get('DP' if net == self.dp else 'DM', 0.0)
            pts = [p] + ([(s[0] - k - abs(dy), p[1]), (s[0] - k, s[1])] if abs(dy) > 1e-6 else []) + [s]
            self.paths[net] = [[F, pts]]
        feats = [(self.swap[0], self.swap[1], 'swap', self.net_of(self.swap[2])),
                 (self.serp[0], self.serp[1], 'serp', self.net_of(self.serp[2]))]
        for i in range(len(C) - 1):
            if i:
                for net in side:
                    self.paths[net][-1][1].append(_off(C, i, side[net] * H))
            t, _ = _unit(C[i], C[i + 1])
            n = _rn(t)

            def P(u, v, i=i, t=t, n=n):
                return (C[i][0] + u * t[0] + v * n[0], C[i][1] + u * t[1] + v * n[1])
            for seg, u0, kind, net in sorted(f for f in feats if f[0] == i):
                if kind == 'swap':
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
                    self.swap_span = (P(u0, 0), P(u0 + lb, 0))
                elif extra > 0:
                    s = side[net]
                    self.paths[net][-1][1] += [P(u0 + du, s * (H + dv)) for du, dv in _bump_pts(_bumps(extra))]
        for net in side:
            end = _off(C, len(C) - 1, side[net] * H)
            want = self.ends[net]
            assert math.dist(end, want) < 2e-3, '%s: %s ends at %s, handoff %s' % (self.name, net, end, want)
            self.paths[net][-1][1].append(want)
        assert side[self.dp] != self.dp_side, self.name

    def lengths(self):
        return {net: sum(_plen(p) for _, p in self.paths[net]) + VIA_LEN * sum(1 for v in self.vias if v[1] == net)
                for net in self.paths}

    def draw(self):
        r = self.r
        for net, pieces in self.paths.items():
            for k, (layer, pts) in enumerate(pieces):
                pts = list(pts)
                if k == 0:
                    pts[0] = self.pads[net]
                r.track(layer, USB_W, *pts, net=net)
        for v in self.vias:
            r.via(v[0], v[1], *SV)
        L = self.lengths()
        r.log.append('hub B %s: %s %.3f / %s %.3f mm (U5 pin -> handoff, %d vias x %.2f mm counted), serpentine +%.3f '
                     'on %s' % (self.name, self.dp, L[self.dp], self.dm, L[self.dm], len(self.vias), VIA_LEN,
                                self.extra, self.net_of(self.serp[2])))

    def gnd_vias(self, gnd):
        """a GND via within 1 mm of each hop via, outside the pair"""
        r = self.r
        for at, net, P, u, v, s in self.vias:
            cands = [(0.0, d) for d in (0.6, 0.65, 0.7, 0.75, 0.8, 0.9)]
            cands += [(du, d) for d in (0.55, 0.6, 0.7) for du in (0.25, -0.25, 0.4, -0.4, 0.55, -0.55)]
            for du, d in cands:
                q = P(u + du, v + s * d)
                if math.dist(q, at) <= 1.0 and r.via(q, gnd, *SV, quiet=True):
                    break
            else:
                r.rejected += 1
                r.log.append('REJECTED hub B %s: no GND via within 1 mm of the hop via %s' % (self.name, at))


def _pairs(r, H_):
    """ports 7..10 <- U5 DN1..DN4. Centre lines: hub -> port; numbers in board mm (docs/layout-plan.md s5 lanes:
    DN1/DN2 down the x 168-171 side to ports 7/8, DN3/DN4 up the x 164-167 corridor to ports 9/10)."""
    def ends(k):
        h = H_[k]
        return h['DP'], h['DM'], ((h['DP'][0] + h['DM'][0]) / 2, (h['DP'][1] + h['DM'][1]) / 2)
    out = []
    # DN1 -> port 7 (front, x 168.2): east at y 159.13 (between C64 and C62), down x 168.205 straight into the handoff.
    # Hop: D- on the vertical, right after the turn; serpentine on D+ (west side) below it.
    dp, dm, c = ends(7)
    C = [(162.0, 159.13), (c[0] - 0.8, 159.13), (c[0], 159.93), c]
    out.append(Pair(r, 'DN1/port 7', ('U5', '2'), ('U5', '1'), C, -1, (2, 0.4, 'DM'), (2, 3.0, 'DP'),
                    {r.net('U5', '2'): dp, r.net('U5', '1'): dm}, lead={'DM': 0.25}))
    # DN2 -> port 8 (right, y 164.8): east at y 157.86, down x 169.975, east into the handoff.
    # Serpentine on D+ (east side) on the vertical, then the D- hop, then the left turn.
    dp, dm, c = ends(8)
    x2 = 169.975
    C = [(162.0, 157.86), (x2 - 0.8, 157.86), (x2, 158.66), (x2, c[1] - 0.8), (x2 + 0.8, c[1]), c]
    out.append(Pair(r, 'DN2/port 8', ('U5', '4'), ('U5', '3'), C, -1, (2, 3.85, 'DM'), (2, 0.25, 'DP'),
                    {r.net('U5', '4'): dp, r.net('U5', '3'): dm}, lead={'DM': 0.35}))
    # DN3 -> port 9 (right, y 143.3): NE off the pins (clear of C64's 3V3 via), up x 166.375, east into the handoff.
    # Serpentine on D- (east side) on the vertical; the D+ hop on the last straight (L4 there is free of lanes).
    dp, dm, c = ends(9)
    x3 = 166.375
    C = [(161.5, 156.25), (162.2, 156.25), (x3, 156.25 - (x3 - 162.2)), (x3, c[1] + 1.0), (x3 + 1.0, c[1]), c]
    out.append(Pair(r, 'DN3/port 9', ('U5', '7'), ('U5', '6'), C, -1, (4, 1.6, 'DP'), (2, 0.8, 'DM'),
                    {r.net('U5', '7'): dp, r.net('U5', '6'): dm}))
    # DN4 -> port 10 (right, y 121.8): NE off the pins inside DN3, up x 164.605, east into the handoff.
    # D+ hop on the vertical at y 145 (north of the L4 lane bundle), serpentine on D- (west side) at y 136-133.
    dp, dm, c = ends(10)
    x4 = 164.605
    x1 = 318.45 - 1.584 - 155.25           # DN3's diagonal x + y = 318.45 less a 0.45 mm gap
    C = [(161.5, 155.25), (x1, 155.25), (x4, 155.25 - (x4 - x1)), (x4, c[1] + 1.0), (x4 + 1.0, c[1]), c]
    y_top = 155.25 - (x4 - x1)
    out.append(Pair(r, 'DN4/port 10', ('U5', '9'), ('U5', '8'), C, -1, (2, y_top - 145.2, 'DP'),
                    (2, y_top - 136.4, 'DM'), {r.net('U5', '9'): dp, r.net('U5', '8'): dm}))
    return out


# ---------------------------------------------------------------- crystal, filters, bias, straps (L1)
def route_local(r):
    # crystal: XTALOUT (pin 32) down x 158.0, under XTALIN, down between Y2's pads into pad 3, on to C72;
    # XTALIN (pin 33) across to pad 1 from above, on to C71. Lanes under pin 36's 3V3 run (y 161.0), 0.31 pitch.
    r.track(F, NARROW, ('U5', '32'), (158.0, 162.26), (160.4, 162.26), (160.4, 163.85), (159.3, 164.95), ('Y2', '3'))
    r.track(F, NARROW, ('Y2', '3'), (159.92, 165.47), ('C72', '1'))
    r.track(F, NARROW, ('U5', '33'), (158.5, 161.95), (161.5, 161.95), ('Y2', '1'))
    r.track(F, NARROW, ('Y2', '1'), (162.25, 163.9), (162.9, 163.9), (163.35, 164.35), ('C71', '1'))
    # GND guard pour round the crystal and its caps on L1 (Y2 / C71 / C72 GND pads and their vias stitch it to L2);
    # west edge x 158.3 keeps it off hub A's UP-pair entry under pins 30/31; the corner west of XTALOUT round pad 2
    # is left out (it would be a piece with one via)
    gnd = r.net('U5', '37')
    r.zone(gnd, F, [(160.55, 162.45), (165.5, 162.45), (165.5, 168.0), (158.3, 168.0), (158.3, 165.6), (160.55, 165.6)],
           prio=5, name='F_GND_XTAL_B')
    # PLLFILT (pin 34) -> C69, RBIAS (pin 35) -> R66
    r.track(F, NARROW, ('U5', '34'), (159.0, 161.64), (162.27, 161.64), (162.65, 162.02), (162.65, 163.5), ('C69', '1'))
    r.track(F, NARROW, ('U5', '35'), (159.5, 161.33), (162.4, 161.33), (163.32, 162.25), ('R66', '1'))
    # CRFILT (pin 14) -> C68 above it
    r.track(F, SIG, ('U5', '14'), (158.0, 152.15), (158.6, 151.55), ('C68', '1'))
    # straps: CFG_SEL0 (24) -> R67, CFG_SEL1 (25) -> R68 across the channel (pins 26/27 leave south, see top),
    # NON_REM0 (28) -> R70 south-west
    r.track(F, NARROW, ('U5', '24'), (153.95, 157.5), (153.6, 157.85), ('R67', '1'))
    r.track(F, NARROW, ('U5', '25'), (154.13, 158.0), (153.6, 158.53), ('R68', '1'))
    r.track(F, NARROW, ('U5', '28'), (156.0, 160.55), (155.1, 160.55), (154.85, 160.8), ('R70', '1'))
    # NON_REM1 (22) -> R69 (moved 0.75 mm west for this): west under the pin-21 stub, then 45 degrees north-west
    # through the gap between the pin-21 chamfer (0.15 mm) and C67 / the pin-23 3V3 link, west of the pin-20/21
    # lanes (route_slow) into R69 pad 1
    r.track(F, NARROW, ('U5', '22'), (154.25, 156.5), (153.15, 155.4), ('R69', '1'))


# ---------------------------------------------------------------- EN / OCS_N: L1 escapes, vias, L4 lanes
def route_slow(r, H_):
    def esc(pin, pts, via, w=SIG):
        net = r.net('U5', pin)
        r.track(F, w, ('U5', pin), *pts, via, net=net)
        r.via(via, net, *SV)
        return net

    # top row: P1 (12), O1 (13), P2 (16), O2 (17), P3 (18) to vias in the channel under the cap row
    p1 = esc('12', [(159.0, 153.4)], (159.5, 152.9))
    o1 = esc('13', [], (158.5, 152.4))
    p2 = esc('16', [], (157.0, 152.9))
    o2 = esc('17', [], (156.5, 152.3))
    p3 = esc('18', [(156.0, 153.0)], (155.9, 152.9))
    # left side: O3 (19) straight up off its pad; P4 (20), O4 (21) up the channel beside the pad ends (0.15 mm)
    o3 = esc('19', [], (155.03, 154.2))
    # P4 lane hard against the pad ends (x 154.25), O4 0.31 mm west of it with its corner chamfered so the pin-22
    # strap (route_local) passes 0.15 mm south-west of it. Needs C67's 3V3 via at (153.32, 157.25) (route_plan).
    p4 = esc('20', [(154.25, 155.5)], (154.25, 154.0), NARROW)
    o4 = esc('21', [(154.175, 156.0), (153.94, 155.765), (153.94, 154.94)], (153.45, 154.45), NARROW)

    # L4. Port 7/8 lanes go round the top (P1/O1 east in the channel band, P2/O2 north round the cap row), then
    # south at x 165.55-166.6 east of the cap column; port 9/10 lanes north to a bundle at y 145.7-146.9.
    def lane(net, pts):
        r.track(B, SIG, *_chamfer(pts), net=net)
    e7, e8, e9, e10 = (H_[k] for k in (7, 8, 9, 10))
    lane(p1, [(159.5, 152.9), (165.55, 152.9), (165.55, 170.2), (e7['EN'][0], 170.2), e7['EN']])
    lane(o1, [(158.5, 152.4), (165.9, 152.4), (165.9, 174.6), (e7['OCS_N'][0], 174.9), e7['OCS_N']])
    lane(p2, [(157.0, 152.9), (158.2, 151.7), (158.2, 149.3), (166.25, 149.3), (166.25, e8['EN'][1]), e8['EN']])
    lane(o2, [(156.5, 152.3), (156.4, 152.2), (156.4, 148.9), (166.6, 148.9), (166.6, e8['OCS_N'][1]),
              e8['OCS_N']])
    lane(p3, [(155.9, 152.9), (155.9, 146.9), (170.5, 146.9), (e9['EN'][0] - 0.566, e9['EN'][1]), e9['EN']])
    lane(o3, [(155.03, 154.2), (155.03, 146.5), (174.6, 146.5), (175.2, e9['OCS_N'][1]), e9['OCS_N']])
    lane(p4, [(154.25, 154.0), (154.25, 146.1), (168.15, 146.1), (168.15, e10['EN'][1]), e10['EN']])
    lane(o4, [(153.45, 154.45), (153.45, 145.7), (167.75, 145.7), (167.75, e10['OCS_N'][1]), e10['OCS_N']])
    # the L4 GND piece between the O2 and P2 lanes under the cap row has only C66's GND via: a second one
    # (pour_check: every piece keeps 2 vias to its plane)
    gnd = r.net('U5', '37')
    assert any(r.via(q, gnd, *SV, quiet=True) for q in ((157.0, 151.95), (157.05, 152.0), (156.95, 151.9))), \
        'hub B: no spot for the L4 GND stitch via under C66'


# ---------------------------------------------------------------- entry
def route(r):
    import route_ports
    H_ = route_ports.PORT_HANDOFF
    for k in (7, 8, 9, 10):
        assert k in H_, 'route_ports has not run (PORT_HANDOFF[%d])' % k
    for num, want in EXPECT.items():
        assert math.dist(r.P('U5', num), want) < 0.02, ('U5 moved: pad %s at %s, expected %s: re-derive '
                                                       'route_hub_b.py' % (num, r.P('U5', num), want))
    gnd = r.net('U5', '37')
    route_local(r)
    route_slow(r, H_)
    pairs = _pairs(r, H_)
    for p in pairs:
        p.draw()
    for p in pairs:
        p.gnd_vias(gnd)
