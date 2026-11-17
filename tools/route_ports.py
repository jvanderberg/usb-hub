"""Port-cluster routing: the 10 downstream USB-C port clusters and the HOST receptacle's local parts.

Called from tools/route_plan.py (route_ports stub); router.py runs it (tools/build.sh). Every coordinate is computed
in the receptacle's own frame and mapped to the board through its position and rotation, so one function routes all
ten ports (left / front / right edges) and the same data path serves the HOST receptacle.

Receptacle frame ("local", mm): origin = the J footprint origin, the footprint's own axes (rot 0 = a front-edge port),
so +x runs along the pad row (A1B12 at x -3.2 ... B1A12 at x +3.2) and -y points into the board (pads at y -2.474,
the cluster further in). All cluster parts sit at the same local positions on every port (checked: EXPECT).

Layer use (docs/layout-plan.md s2): L1 parts, the D+/D- pair and local copper; L4 only for the receptacle's A/B-row
D+/D- tie, the CC1 crossing under the pair, the VBUS pad-group tie, and the EN / OCS_N / VBUS_DET handoff vias.
Nets always come from pads (R17); free points name the net of the pad they continue from.

PORT_HANDOFF[k] (k = 1..10, and 'HOST') is where the hub stage continues, in board mm:
  'DP', 'DM': (x, y) track ends on F.Cu of the coupled pair (0.26 / 0.15 mm), just past the ESD array;
  'dir':      direction the pair leaves in (into the board), degrees, atan2(dy, dx) in board axes (x right, y down);
  'EN', 'OCS_N' (ports): (x, y) of a 0.45/0.2 via on that net; continue on B.Cu (L4);
  'VBUS_DET' (HOST): (x, y) of the HUBA_VBUS_DET via at TP41; continue on B.Cu toward hub A.
"""
import math

F, B = 'F.Cu', 'B.Cu'
SIG = 0.2           # CC, EN, OCS, ISET, LED
NECK = 0.2          # D+/D- through the receptacle jog, the ESD pins and the A/B tie (layout-plan s3: <= 1 mm necks)
USB_W, USB_GAP = 0.26, 0.15     # coupled pair (layout-plan s3 estimate, ~90 ohm; TO CONFIRM with JLC's calculator)
SV = (0.45, 0.2)    # signal via
PV = (0.6, 0.3)     # power via
VBUS_W = 0.9        # L1 VBUS band from the switch OUT to the receptacle (+ the 1.0 mm L4 trunk in parallel)
TRUNK_W = 1.0       # L4 VBUS trunk, switch OUT vias -> A4B9 side
TIE_W = 0.6         # L4 VBUS tie, A4B9 side -> B4A9 / Rp side

PORTS = range(1, 11)
PORT_HANDOFF = {}

# Local positions every cluster is built on (pad centres, receptacle frame); route_port asserts them, so a placement
# change that breaks the offsets below stops the build instead of routing into the wrong copper.
EXPECT = {
    ('J', 'A4B9'): (-2.4, -2.474), ('J', 'A5'): (-1.25, -2.474), ('J', 'B7'): (-0.75, -2.474),
    ('J', 'A6'): (-0.25, -2.474), ('J', 'A7'): (0.25, -2.474), ('J', 'B6'): (0.75, -2.474),
    ('J', 'B5'): (1.75, -2.474), ('J', 'B4A9'): (2.4, -2.474),
    ('ESD', '1'): (-1.0, -4.466), ('ESD', '2'): (-0.5, -4.466), ('ESD', '4'): (0.5, -4.466), ('ESD', '5'): (1.0, -4.466),
    ('ESD', '10'): (-1.0, -5.266), ('ESD', '9'): (-0.5, -5.266), ('ESD', '7'): (0.5, -5.266), ('ESD', '6'): (1.0, -5.266),
    ('SW', '1'): (-7.75, -4.566), ('SW', '3'): (-5.85, -4.566), ('SW', '4'): (-5.85, -7.266), ('SW', '5'): (-6.8, -7.266),
    ('TVS', '1'): (-2.605, -3.805), ('C3', '1'): (-7.42, -1.866), ('C2', '1'): (-7.7, -0.316),
    ('RLED', '1'): (-7.433, 1.184), ('RLED', '2'): (-6.567, 1.184), ('LED', '2'): (-7.749, 2.684),
    ('RP1', '1'): (2.9, -4.783), ('RP1', '2'): (2.9, -5.649), ('RP2', '1'): (4.1, -4.783), ('RP2', '2'): (4.1, -5.649),
    ('RSET', '1'): (-6.8, -8.483), ('PD', '1'): (-4.6, -7.783),
}
EXPECT_HOST = {
    ('J', 'A4B9'): (-2.4, -2.474), ('J', 'A5'): (-1.25, -2.474), ('J', 'B5'): (1.75, -2.474), ('J', 'B4A9'): (2.4, -2.474),
    ('ESD', '1'): (-1.0, -4.466), ('ESD', '5'): (1.0, -4.466), ('TVS', '1'): (-2.605, -3.805),
    ('C', '1'): (-4.0, -5.096), ('RTOP', '1'): (-5.3, -5.083), ('RTOP', '2'): (-5.3, -5.949),
    ('RBOT', '1'): (-6.5, -5.083), ('RD1', '1'): (2.9, -4.783), ('RD2', '1'): (4.1, -4.783), ('TP', '1'): (-6.0, -8.216),
}


# ---------------------------------------------------------------- receptacle frame
class Frame:
    """local (receptacle) <-> board coordinates for footprint `ref` (KiCad: rotation counter-clockwise, y down)"""

    def __init__(self, r, ref):
        fp = [f for f in r.B['footprints'] if f['ref'] == ref]
        assert len(fp) == 1, (ref, len(fp))
        f = fp[0]
        self.r, self.ref = r, ref
        self.ox, self.oy = f['x'], f['y']
        t = math.radians(f['rot'])
        self.c, self.s = math.cos(t), math.sin(t)

    def b(self, lx, ly):
        """board point of local (lx, ly)"""
        x = self.ox + lx * self.c + ly * self.s
        y = self.oy - lx * self.s + ly * self.c
        return (round(x, 4) + 0.0, round(y, 4) + 0.0)

    def l(self, bx, by):
        dx, dy = bx - self.ox, by - self.oy
        return (dx * self.c - dy * self.s, dx * self.s + dy * self.c)

    def lp(self, ref, num):
        """local position of a pad"""
        return self.l(*self.r.P(ref, num))

    def bs(self, *pts):
        """map local points to board points; pad references pass through"""
        return [q if isinstance(q[0], str) else self.b(*q) for q in pts]

    def angle(self, lx, ly):
        """board direction (degrees, atan2(dy, dx)) of the local vector (lx, ly)"""
        x, y = lx * self.c + ly * self.s, -lx * self.s + ly * self.c
        a = round(math.degrees(math.atan2(y, x)), 1) + 0.0
        return 180.0 if a == -180.0 else a


def check_frame(fr, roles, expect, what):
    for (role, num), want in expect.items():
        got = fr.lp(roles[role], num)
        assert math.dist(got, want) < 0.02, '%s: %s.%s (%s) at local %s, expected %s: the cluster moved, re-derive ' \
            'route_ports.py' % (what, roles[role], num, role, tuple(round(v, 3) for v in got), want)


def two_pad_part_on(r, net, exclude):
    """the two-pad part (a resistor) with a pad on `net`, other than `exclude`"""
    refs = sorted({rf for (rf, num) in r.pads if rf != exclude and r.net(rf, num) == net})
    refs = [rf for rf in refs if len([1 for (q, n) in r.pads if q == rf]) == 2]
    assert len(refs) == 1, (net, refs)
    return refs[0]


# ---------------------------------------------------------------- shared by ports and HOST
def route_data(r, fr, J, ESD):
    """D+/D-: A6/A7 jog onto the ESD array's connector-side pins and straight through to pins 10/9 (TI TPD4E05U06
    s10.1: straight, at the connector); B6/B7 tied to them on L4 under the receptacle; the pair leaves as a coupled
    0.26 / 0.15 mm pair. Returns the handoff (DP, DM, dir)."""
    dp, dm = r.net(J, 'A6'), r.net(J, 'A7')
    assert r.net(J, 'B6') == r.net(ESD, '1') == r.net(ESD, '10') == dp, 'DP pads'
    assert r.net(J, 'B7') == r.net(ESD, '2') == r.net(ESD, '9') == dm, 'DM pads'
    jy = fr.lp(J, 'A6')[1]                   # receptacle pad centres
    pad_end = jy + 0.65                      # pad outer end (pads 1.3 long), under the body
    ex = {n: fr.lp(ESD, n)[0] for n in ('1', '2')}
    ey = fr.lp(ESD, '1')[1]
    ey_hub = fr.lp(ESD, '10')[1]
    # jog between the receptacle pad and the ESD pad (43 deg): 0.164 mm between the two diagonals, 0.178 mm from DM
    # to the ESD's wide GND pin 3
    bend0, bend1 = jy - 0.826, ey + 0.366
    # receptacle -> ESD connector side -> straight through to the hub-side pins (0.2 mm through the 0.5 mm pitch)
    for net, a, e_in, e_out in ((dp, 'A6', '1', '10'), (dm, 'A7', '2', '9')):
        ax = fr.lp(J, a)[0]
        r.track(F, NECK, *fr.bs((J, a), (ax, bend0), (ex[e_in], bend1), (ESD, e_in), (ESD, e_out)))
    # coupled pair from the hub-side pins: DP stays on its pin axis, DM steps in to the 0.41 mm pitch
    pitch = USB_W + USB_GAP
    dpx, dmx = ex['1'], ex['1'] + pitch
    y0 = ey_hub - 0.334                      # just past the hub-side pad end
    y1 = y0 - abs(fr.lp(ESD, '9')[0] - dmx)  # 45 deg step
    hy = ey_hub - 1.734                      # handoff: past the ESD GND via row and the CC1 run
    r.track(F, USB_W, *fr.bs((ESD, '10'), (dpx, hy)))
    r.track(F, NECK, *fr.bs((ESD, '9'), (fr.lp(ESD, '9')[0], y0)))
    r.track(F, USB_W, *fr.bs((fr.lp(ESD, '9')[0], y0), (dmx, y1), (dmx, hy)), net=dm)
    # A/B-row tie under the receptacle body: B7 -> L4 -> A7 (DM, row 1), A6 -> L4 -> B6 (DP, row 2)
    row1, row2 = tie_rows(pad_end)
    vias = {'B7': row1, 'A7': row1, 'A6': row2, 'B6': row2}
    for pad, y in vias.items():
        x = fr.lp(J, pad)[0]
        r.via(fr.b(x, y), r.net(J, pad), *SV)
        r.track(F, NECK, *fr.bs((J, pad), (x, y)))
    r.track(B, NECK, *fr.bs((fr.lp(J, 'B7')[0], row1), (fr.lp(J, 'A7')[0], row1)), net=dm)
    r.track(B, NECK, *fr.bs((fr.lp(J, 'A6')[0], row2), (fr.lp(J, 'B6')[0], row2)), net=dp)
    return {'DP': fr.b(dpx, hy), 'DM': fr.b(dmx, hy), 'dir': fr.angle(0.0, -1.0)}


def tie_rows(pad_end):
    """the two via rows under the receptacle body (local y): row 1 0.29 mm past the pad ends (0.065 mm via-to-own-pad,
    0.23 mm to the neighbouring pads), row 2 0.6 mm further"""
    return pad_end + 0.29, pad_end + 0.89


def route_cc(r, fr, J, ESD, cc1_to, cc2_to, host=False):
    """CC1 / CC2 through the ESD array (straight-through pins 4-7 / 5-6), then on to their Rp (port) or Rd (HOST).
    CC2 (B5) reaches pin 5 on L1. CC1 (A5) sits on the far side of the D+/D- pair: via under the receptacle, L4
    under the pair, up beside ESD pin 6/7.
    Port: CC2's Rp sits behind the VBUS pad group, so CC2 hops on L4 (cc2_to gets the via); CC1's L4 run goes below
      the A/B tie and rises between B6's and CC2's vias.
    HOST: the 3V3 trunk (route_3v3) runs on L4 under J2 and up at local x 1.5, so CC1's L4 run goes straight in at
      x(A5) and comes up left of that trunk, between ESD pin 7 and the GND via; CC2 stays on L1 (cc2_to gets the
      bend point above B5).
    cc1_to / cc2_to: functions (r, fr, local point, net) that finish the run to the resistor."""
    cc1, cc2 = r.net(J, 'A5'), r.net(J, 'B5')
    assert r.net(ESD, '4') == r.net(ESD, '7') == cc1 and r.net(ESD, '5') == r.net(ESD, '6') == cc2, 'CC pads'
    jy = fr.lp(J, 'A5')[1]
    row1, row2 = tie_rows(jy + 0.65)
    a5x, b5x, b6x = fr.lp(J, 'A5')[0], fr.lp(J, 'B5')[0], fr.lp(J, 'B6')[0]
    e5, e7 = fr.lp(ESD, '5'), fr.lp(ESD, '7')
    # CC2: B5 -> bend (via for the port's L4 hop) -> ESD pin 5 -> pin 6
    v2 = (b5x, jy - 1.126)
    r.track(F, SIG, *fr.bs((J, 'B5'), v2, (e5[0], e5[1] + 0.116), (ESD, '5'), (ESD, '6')))
    if not host:
        r.via(fr.b(*v2), cc2, *SV)
    cc2_to(r, fr, v2, cc2)
    # CC1: A5 -> via under the body -> L4 -> via -> ESD pin 7 / pin 4
    va = (a5x, row2)
    r.via(fr.b(*va), cc1, *SV)
    r.track(F, SIG, *fr.bs((J, 'A5'), va))
    if host:
        vb = (e7[0] + 0.15, e7[1] - 0.984)
        r.track(B, SIG, *fr.bs(va, (a5x, vb[1] + 0.75), vb), net=cc1)
        r.via(fr.b(*vb), cc1, *SV)
        r.track(F, SIG, *fr.bs((ESD, '4'), (ESD, '7'), (e7[0], vb[1] + 0.15), vb))
    else:
        riser = (b6x + b5x) / 2
        low = row2 + 0.55
        top = e7[1] - 0.684
        vb = (riser, top)
        r.track(B, SIG, *fr.bs(va, (a5x, low), (riser, low), vb), net=cc1)
        r.via(fr.b(*vb), cc1, *SV)
        r.track(F, SIG, *fr.bs((ESD, '4'), (ESD, '7'), (e7[0], top), vb))
    cc1_to(r, fr, vb, cc1)


# ---------------------------------------------------------------- downstream port k
def roles_of(r, k):
    n = 100 * k
    sw = 'U%d' % (n + 1)
    return {'J': 'J%d' % (n + 1), 'SW': sw, 'ESD': 'U%d' % (n + 2), 'TVS': 'D%d' % (n + 1), 'LED': 'D%d' % (n + 2),
            'RSET': 'R%d' % (n + 1), 'RP1': 'R%d' % (n + 2), 'RP2': 'R%d' % (n + 3), 'RLED': 'R%d' % (n + 4),
            'C2': 'C%d' % (n + 2), 'C3': 'C%d' % (n + 3), 'PD': two_pad_part_on(r, r.net(sw, '4'), sw)}


def route_port(r, k):
    R = roles_of(r, k)
    J, SW, ESD, TVS, LED = R['J'], R['SW'], R['ESD'], R['TVS'], R['LED']
    RP1, RP2, RLED, RSET, PD, C2, C3 = R['RP1'], R['RP2'], R['RLED'], R['RSET'], R['PD'], R['C2'], R['C3']
    fr = Frame(r, J)
    check_frame(fr, R, EXPECT, 'port %d' % k)
    vbus = r.net(J, 'A4B9')
    for q in ((J, 'B4A9'), (SW, '1'), (TVS, '1'), (C2, '1'), (C3, '1'), (RLED, '1'), (RP1, '1'), (RP2, '2')):
        assert r.net(*q) == vbus, ('VBUS', q)
    assert r.net(RP1, '2') == r.net(J, 'A5') and r.net(RP2, '1') == r.net(J, 'B5'), 'Rp nets'
    L = fr.lp

    # D+/D- and CC
    h = route_data(r, fr, J, ESD)

    def cc1_rp(r, fr, vb, net):
        # on to the CC1 Rp's CC pad (top-left of the Rp pair), above ESD pin 6
        rp = L(RP1, '2')
        r.track(F, SIG, *fr.bs(vb, (rp[0] - 0.3, vb[1]), (RP1, '2')), net=net)

    def cc2_rp(r, fr, v2, net):
        # L4 under the B4A9 pad / VBUS link to a via below the CC2 Rp, up into its CC pad
        rp = L(RP2, '1')
        vc = (rp[0], rp[1] + 0.833)
        r.track(B, SIG, *fr.bs(v2, (vc[0] - 0.35, v2[1]), vc), net=net)
        r.via(fr.b(*vc), net, *SV)
        r.track(F, SIG, *fr.bs(vc, (RP2, '1')), net=net)

    route_cc(r, fr, J, ESD, cc1_rp, cc2_rp)

    # VBUS, switched, 3 A. L1: OUT -> via row -> band over the switch's edge-side pins to the TVS and the A4B9 pad
    # group; cap / LED column below. L4: 1.0 mm trunk from the via row to a via beside the TVS (in parallel with the
    # L1 band), then a 0.6 mm tie over the pair's hub side to the B4A9 / Rp group (pads tie on L4: layout-plan s6).
    sw1, tvs1 = L(SW, '1'), L(TVS, '1')
    yb = L(J, 'A4B9')[1] - 1.026                         # band / via row / trunk line (-3.5)
    # 1.25 mm pitch: the antipads (via + 0.2 mm) stay apart on L2 / L3, so the row does not slot the GND plane
    row = [(sw1[0] - 1.25, yb), (sw1[0], yb), (sw1[0] + 1.25, yb)]
    r.track(F, 0.6, *fr.bs((SW, '1'), (sw1[0], yb)))
    # 0.9 mm band: centred between the switch's edge-side pins and the shell leg (0.2 mm each side), then between the
    # OCS_N run and the A1B12 pad into the TVS's VBUS pad
    ybb = L(SW, '1')[1] + 1.206
    r.track(F, VBUS_W, *fr.bs(row[0], (row[0][0], ybb), (tvs1[0] - 1.795, ybb), (tvs1[0] - 1.365, tvs1[1] + 0.01),
                              (TVS, '1')), net=vbus)
    r.track(F, 0.5, *fr.bs((sw1[0], yb), (C3, '1'), (C2, '1'), (RLED, '1')), net=vbus)
    a4 = L(J, 'A4B9')
    r.track(F, 0.4, *fr.bs((TVS, '1'), (a4[0], a4[1] - 0.826), (J, 'A4B9')))
    v1 = (L(J, 'B8')[0], tvs1[1] + 0.105)                # beside the TVS, behind the B8 (SBU) pad
    r.track(F, 0.4, *fr.bs((TVS, '1'), v1))
    for p in row + [v1]:
        r.via(fr.b(*p), vbus, *PV)
    r.track(B, TRUNK_W, *fr.bs(row[0], (v1[0] - 0.2, yb), v1), net=vbus)
    # B4A9 side: via left of the Rp VBUS pad (inside the cluster, so the corner ports 7/8 and 10/1 do not meet)
    b4, rp1 = L(J, 'B4A9'), L(RP1, '1')
    v2 = (rp1[0] - 0.85, rp1[1] - 0.217)
    ytie = L(ESD, '9')[1] - 2.234                        # beyond the ESD GND via, under the pair's hub-side run
    # two vias: with the pads forced to share 1.5 / 1.5 A, power.py put all 1.5 A of B4A9 through one 0.3 mm via
    v2b = (v2[0] + 0.1, v2[1] + 0.7)
    r.track(B, TIE_W, *fr.bs(v1, (v1[0], ytie), (v2[0], ytie), v2, v2b), net=vbus)
    for p in (v2, v2b):
        r.via(fr.b(*p), vbus, *PV)
    r.track(F, 0.4, *fr.bs(v2b, v2, (RP1, '1')), net=vbus)
    r.track(F, 0.4, *fr.bs((J, 'B4A9'), (b4[0], b4[1] - 1.126), (rp1[0], b4[1] - 1.626), (RP1, '1')))
    r.track(F, SIG, *fr.bs((RP1, '1'), (RP2, '2')))      # between the two CC pads (Rp current only)

    # LED: VBUS -> R -> LED anode, under R's VBUS pad
    rl2, led2 = L(RLED, '2'), L(LED, '2')
    yl = rl2[1] + 0.666
    r.track(F, SIG, *fr.bs((RLED, '2'), (rl2[0], yl), (led2[0], yl), (LED, '2')))

    # RSET at ISET; EN to its pull-down and a via; OCS_N to a via beside the TVS
    r.track(F, 0.25, *fr.bs((SW, '5'), (RSET, '1')))
    r.track(F, SIG, *fr.bs((SW, '4'), (PD, '1')))
    sw4, sw3 = L(SW, '4'), L(SW, '3')
    en_v = (sw4[0], sw4[1] - 1.134)
    r.track(F, SIG, *fr.bs((SW, '4'), en_v))
    r.via(fr.b(*en_v), r.net(SW, '4'), *SV)
    ocs_v = (sw3[0] + 2.45, sw3[1] - 0.6)
    r.track(F, SIG, *fr.bs((SW, '3'), (sw3[0] + 1.85, sw3[1]), ocs_v))
    r.via(fr.b(*ocs_v), r.net(SW, '3'), *SV)

    h['EN'] = fr.b(*en_v)
    h['OCS_N'] = fr.b(*ocs_v)
    PORT_HANDOFF[k] = h


# ---------------------------------------------------------------- HOST receptacle (J2, U7, D40, C74, R64/R65, R77/R78)
def host_roles(r):
    J = 'J2'
    vbus = r.net(J, 'A4B9')
    tvs = [rf for (rf, n) in sorted(r.pads) if rf.startswith('D') and r.net(rf, n) == vbus]
    caps = [rf for (rf, n) in sorted(r.pads) if rf.startswith('C') and r.net(rf, n) == vbus]
    rtop = [rf for (rf, n) in sorted(r.pads) if rf.startswith('R') and r.net(rf, n) == vbus]
    assert len(tvs) == len(caps) == len(rtop) == 1, (tvs, caps, rtop)
    det = [r.net(rtop[0], n) for n in ('1', '2') if r.net(rtop[0], n) != vbus][0]
    rbot = two_pad_part_on(r, det, rtop[0])
    tp = [rf for (rf, n) in sorted(r.pads) if rf.startswith('TP') and r.net(rf, n) == det]
    esd = [rf for (rf, n) in sorted(r.pads) if rf.startswith('U') and n == '1' and r.net(rf, n) == r.net(J, 'A6')]
    rd1 = two_pad_part_on(r, r.net(J, 'A5'), esd[0] if esd else None) if esd else None
    rd2 = two_pad_part_on(r, r.net(J, 'B5'), esd[0] if esd else None) if esd else None
    assert len(tp) == 1 and len(esd) == 1, (tp, esd)
    return {'J': J, 'ESD': esd[0], 'TVS': tvs[0], 'C': caps[0], 'RTOP': rtop[0], 'RBOT': rbot, 'TP': tp[0],
            'RD1': rd1, 'RD2': rd2}


def route_host(r):
    R = host_roles(r)
    J, ESD, TVS, C, RTOP, RBOT, TP, RD1, RD2 = (R[k] for k in ('J', 'ESD', 'TVS', 'C', 'RTOP', 'RBOT', 'TP', 'RD1', 'RD2'))
    fr = Frame(r, J)
    check_frame(fr, R, EXPECT_HOST, 'HOST')
    L = fr.lp
    vbus = r.net(J, 'A4B9')
    cc1, cc2 = r.net(J, 'A5'), r.net(J, 'B5')
    rd1_cc = [n for n in ('1', '2') if r.net(RD1, n) == cc1][0]
    rd2_cc = [n for n in ('1', '2') if r.net(RD2, n) == cc2][0]
    rtop_v = [n for n in ('1', '2') if r.net(RTOP, n) == vbus][0]
    rtop_d = '2' if rtop_v == '1' else '1'
    det = r.net(RTOP, rtop_d)
    rbot_d = [n for n in ('1', '2') if r.net(RBOT, n) == det][0]
    c_v = [n for n in ('1', '2') if r.net(C, n) == vbus][0]

    h = route_data(r, fr, J, ESD)

    def cc1_rd(r, fr, vb, net):
        # the Rd's CC pad is the one nearer the receptacle: across beside the Rd's GND pad, down to it
        rd = L(RD1, rd1_cc)
        xm = rd[0] - 1.0
        r.track(F, SIG, *fr.bs(vb, (xm - 0.3, vb[1]), (xm, vb[1] + 0.3), (xm, rd[1] - 0.167), (RD1, rd1_cc)), net=net)

    def cc2_rd(r, fr, v2, net):
        # on L1 behind the B4A9 pad (HOST_VBUS has no L1 link there) and the CC1 Rd, into the CC2 Rd from below
        rd = L(RD2, rd2_cc)
        yk = v2[1] - 0.35
        r.track(F, SIG, *fr.bs(v2, (v2[0] + 0.35, yk), (rd[0] - 0.7, yk), (rd[0], rd[1] + 0.133), (RD2, rd2_cc)),
                net=net)

    route_cc(r, fr, J, ESD, cc1_rd, cc2_rd, host=True)

    # HOST_VBUS (detection only, no load current): A4B9 -> TVS -> C -> divider top on L1. B4A9: 0.15 mm link past the
    # locating peg to a via under the receptacle body, then L4 toward the board edge around the start of the 3V3
    # trunk (its via at local (-5.5, -0.17)) and back in above the shell leg to a via beside the TVS.
    tvs1, a4, b4 = L(TVS, '1'), L(J, 'A4B9'), L(J, 'B4A9')
    r.track(F, 0.4, *fr.bs((TVS, '1'), (a4[0], a4[1] - 0.826), (J, 'A4B9')))
    cpos = L(C, c_v)
    r.track(F, 0.3, *fr.bs((TVS, '1'), (cpos[0], tvs1[1]), (C, c_v), (RTOP, rtop_v)))
    v1 = (L(J, 'B8')[0], tvs1[1] + 0.105)
    r.via(fr.b(*v1), vbus, *SV)
    r.track(F, 0.3, *fr.bs((TVS, '1'), v1))
    pad_end = b4[1] + 0.65
    hv = (b4[0] - 0.15, pad_end + 1.524)
    r.track(F, 0.15, *fr.bs((J, 'B4A9'), (hv[0], pad_end - 0.076), hv))
    r.via(fr.b(*hv), vbus, *SV)
    yf, xl, yk = pad_end + 2.424, a4[0] - 3.8, a4[1] - 0.526
    r.track(B, SIG, *fr.bs(hv, (hv[0], yf), (xl, yf), (xl, yk), (v1[0] - 0.3, yk), v1), net=vbus)
    # the L4 GND piece this run and the 3V3 trunk enclose has only the shell leg: a second via to the planes
    # (pour_check), under the body between the peg, the A5 via and the trunk
    r.via(fr.b(a4[0] + 0.4, pad_end + 0.974), r.net(J, 'A1B12'), *SV)

    # VBUS_DET divider -> TP41 -> handoff via (hub A's VBUS_DET, routed in the hub stage)
    rt_d, rb_d, tp = L(RTOP, rtop_d), L(RBOT, rbot_d), L(TP, '1')
    r.track(F, SIG, *fr.bs((RTOP, rtop_d), (RBOT, rbot_d)))
    r.track(F, SIG, *fr.bs((RTOP, rtop_d), (rt_d[0], rt_d[1] - 1.05), (tp[0], rt_d[1] - 1.75), (TP, '1')))
    dv = (tp[0], tp[1] - 0.984)
    r.track(F, SIG, *fr.bs((TP, '1'), dv))
    r.via(fr.b(*dv), det, *SV)
    h['VBUS_DET'] = fr.b(*dv)
    PORT_HANDOFF['HOST'] = h


def route_ports(r):
    PORT_HANDOFF.clear()
    for k in PORTS:
        route_port(r, k)
    route_host(r)
    for k, h in PORT_HANDOFF.items():
        r.log.append('handoff %s: %s' % (k, ', '.join('%s %s' % (n, h[n]) for n in sorted(h))))
