"""Generate tools/place.json for the usb-hub board (Stage 1 placement).

Coordinates: mm relative to the outline's top-left (outline 85 x 85), KiCad y down, rotation CCW degrees.
Generates tools/place.json, which build.sh reads (the placement data); fp.json is a footprint pad dump of the board.
  python3 place_gen.py fp.json OUT.json
"""
import json, math, sys

FP = json.load(open(sys.argv[1]))          # fp.json dump (local pad coordinates per footprint)
OUT = sys.argv[2]
W = H = 85.0
P = {}


def put(ref, x, y, rot=0):
    assert ref in FP, ref
    assert ref not in P, 'placed twice: ' + ref
    P[ref] = [round(x, 3), round(y, 3), int(round(rot)) % 360]


def R(theta, u, w):
    """KiCad rotation of a local vector by theta (CCW on screen, y down)."""
    t = math.radians(theta)
    return (u * math.cos(t) + w * math.sin(t), -u * math.sin(t) + w * math.cos(t))


def frame(anc, theta):
    """parts given in an edge frame: u along the edge, w outward (+) / inward (-)"""
    ax, ay = anc

    def f(ref, u, w, r=0):
        dx, dy = R(theta, u, w)
        put(ref, ax + dx, ay + dy, r + theta)
    return f


def pad(ref, num):
    for p in FP[ref]['pads']:
        if p[0] == str(num):
            return p[1], p[2]
    raise KeyError((ref, num))


def netof(ref, num):
    for p in FP[ref]['pads']:
        if p[0] == str(num):
            return p[6]
    raise KeyError((ref, num))


def pin_xy(ref, num):
    x, y, r = P[ref]
    px, py = pad(ref, num)
    dx, dy = R(r, px, py)
    return x + dx, y + dy


def side_normal(ic, num):
    x, y, r = P[ic]
    px, py = pad(ic, num)
    n = (1 if px > 0 else -1, 0) if abs(px) > abs(py) else (0, 1 if py > 0 else -1)
    return R(r, *n)


def facing(ref, net, ux, uy):
    """rotation that points the pad on `net` along unit vector (ux, uy)"""
    pads = [p for p in FP[ref]['pads'] if p[6] == net or p[6].endswith('/' + net)]
    assert pads, (ref, net, [p[6] for p in FP[ref]['pads']])
    lx = pads[0][1]
    if lx < 0:
        ux, uy = -ux, -uy                   # the pad sits at local -x: point local +x the other way
    return round(math.degrees(math.atan2(-uy, ux)) / 90) * 90


def at_pin(ref, ic, num, dist, along=0.0, net=None):
    """2-pad part radially outside an IC pin; the pad on the pin's net (or `net`) faces the pin"""
    px, py = pin_xy(ic, num)
    nx, ny = side_normal(ic, num)
    tx, ty = -ny, nx
    put(ref, px + nx * dist + tx * along, py + ny * dist + ty * along, facing(ref, net or netof(ic, num), -nx, -ny))


def at(ref, x, y, r=0):
    put(ref, x, y, r)


DIRS = {'R': (1, 0), 'L': (-1, 0), 'U': (0, -1), 'D': (0, 1)}


def orient(ref, x, y, net, d):
    """place a 2-pad part with the pad on `net` toward 'L','R','U','D'"""
    put(ref, x, y, facing(ref, net, *DIRS[d]))


# ---------------------------------------------------------------- mounting holes (given)
for ref, xy in {'H1': (4, 4), 'H2': (81, 4), 'H3': (4, 81), 'H4': (81, 81)}.items():
    put(ref, *xy)

# ---------------------------------------------------------------- receptacles and port clusters
# HRO TYPE-C-31-M-12: the drawing puts the PCB edge 5.79 mm in front of the rear shell-leg holes (holes 4.18 apart),
# i.e. local y = -1.706 + 5.79 = 4.084; the shell front is 2.60 in front of the front legs (local 5.07): ~1.0 mm
# overhang, as drawn. GCT USB4105: the edge 2.60 in front of the front stakes (2.373 + 2.60 = 4.973) = flush.
HRO_EDGE = 4.084
GCT_EDGE = 4.973

EDGES = {'left': 270, 'front': 0, 'right': 90, 'back': 180}
PORTS = {1: ('left', 21.0), 2: ('left', 42.5), 3: ('left', 64.0),
         4: ('front', 16.0), 5: ('front', 33.7), 6: ('front', 51.3), 7: ('front', 69.0),
         8: ('right', 64.0), 9: ('right', 42.5), 10: ('right', 21.0)}


PULLDOWN = {1: 'R56', 2: 'R57', 3: 'R58', 4: 'R59', 5: 'R60', 6: 'R61', 7: 'R71', 8: 'R72', 9: 'R73', 10: 'R74'}


def anchor(edge, s):
    return {'left': (0, s), 'front': (s, H), 'right': (W, s), 'back': (s, 0)}[edge]


def port_cluster(k, edge, s):
    f = frame(anchor(edge, s), EDGES[edge])
    n = 100 * k
    f('J%d' % (n + 1), 0, -HRO_EDGE, 0)
    f('U%d' % (n + 2), 0, -8.95, 0)          # TPD4E05U06 right behind the signal pins (flow-through)
    f('D%d' % (n + 1), -2.6, -8.6, 90)       # ESD5Z6.0 VBUS TVS at the left VBUS pin
    f('R%d' % (n + 2), 2.9, -9.3, 90)        # Rp CC1 -> VBUS, behind the right VBUS pin
    f('R%d' % (n + 3), 4.1, -9.3, 90)        # Rp CC2 -> VBUS
    # column beside the receptacle (clockwise side): LED at the edge, its resistor, VBUS caps
    f('D%d' % (n + 2), -7.0, -1.4, 180)      # green LED, seen through the lid
    f('R%d' % (n + 4), -7.0, -2.9, 0)
    f('C%d' % (n + 2), -7.0, -4.4, 0)        # 22 uF VBUS
    f('C%d' % (n + 3), -7.0, -5.95, 0)        # 100 nF VBUS
    f('U%d' % (n + 1), -6.8, -10.0, 270)     # SY6863: OUT/GND/OCB toward the edge, IN/ISET/EN inward
    f('C%d' % (n + 1), -9.6, -11.0, 90)      # 10 uF at IN
    f('R%d' % (n + 1), -6.8, -13.0, 90)      # RSET at ISET
    f(PULLDOWN[k], -4.6, -12.3, 90)          # 10 k EN pull-down (hub PRTPWR net), at the EN pin as SY6863 Fig 4 R_ENB


for k, (edge, s) in PORTS.items():
    port_cluster(k, edge, s)

# HOST receptacle (hubs sheet), back edge toward the left
f = frame(anchor('back', 20.0), EDGES['back'])
f('J2', 0, -HRO_EDGE, 0)
f('U7', 0, -8.95, 0)
f('D40', -2.6, -8.6, 90)
f('R77', 2.9, -9.3, 90)                       # Rd CC1
f('R78', 4.1, -9.3, 90)                       # Rd CC2
# host-powered mode (2026-11-18): the HOST_VBUS trunk runs from the TVS east and then south at x 124.6 into the eFuse
# IN strip, so C74 moved east of it and the VBUS_DET divider moved west of the HOST pair (fed from the B4A9 pad's L4
# via, joining hub A's L1 VBUS_DET run at x 119.3 with no L4 crossing under the pair)
orient('C74', 25.75, 9.6, 'HOST_VBUS', 'L')    # 1 uF HOST_VBUS, east of the trunk
orient('R64', 17.75, 12.3, 'HOST_VBUS', 'U')   # HOST_VBUS -> VBUS_DET 100k
orient('R65', 17.75, 14.4, 'HUBA_VBUS_DET', 'U')   # VBUS_DET -> GND 100k
at('TP41', 19.3, 15.0)                         # VBUS_DET, on hub A's x 119.3 run
# U8 TPS259470 rot 180 in the free patch below the receptacle: IN strip x 124.6 (trunk from the north), OUT strip
# x 124.1 (south to the L3 via column); DVDT / ILM / ITIMER / GND face west (the quiet HOST pair side, away from L1's
# switch node: TI layout guidelines s8.4.1), one 0402 column at x 122.2; EN / OVLO east, EN divider below the part.
# Outline (silk) boxes: U8 x 122.9-126.2, L1 down to y 113.6, D41 from x 128.0 - the parts sit between them.
at('U8', 24.365, 17.0, 180)
orient('C75', 22.2, 14.9, 'GND', 'U')          # dVdt 10 nF, DVDT pad down to pin 7
orient('R81', 22.2, 18.2, 'Net-(U8-ILM)', 'U')     # ILM 1.87 k (pin 8's GND via sits between it and C75)
orient('C76', 22.2, 21.0, 'Net-(U8-ITIMER)', 'U')  # ITIMER 5.1 nF
orient('C77', 25.3, 21.9, '5V_BUS', 'L')       # 1 uF at the end of the OUT via column
orient('C78', 25.97, 13.9, 'HOST_VBUS', 'L')   # 100 nF at IN: pad on the trunk, north of the y 114.6 branch
orient('R79', 26.4, 19.1, 'HOST_EN', 'L')      # EN/UVLO 100 k (HOST_VBUS pad east, fed by the branch at x 127.4)
orient('R80', 26.4, 20.3, 'HOST_EN', 'L')      # EN/UVLO 47 k
orient('D41', 30.7, 16.2, 'VIN', 'R')          # SS34 5V_BUS -> VIN: cathode clear of C14's GND via and outline
orient('R83', 28.5, 19.6, '5V_BUS', 'U')       # 2.2 k 5V_BUS bleed under D41's anode (C13's outline from x 129.2)

# ---------------------------------------------------------------- PD input: J1 + TPS25730 (power_in)
at('J1', 62.0, GCT_EDGE, 180)
at('U1', 54.0, 14.2, 270)       # rot 270: PPHV pins bottom-left (to the buck input), VBUS right/bottom-right (J1)
at('D1', 65.0, 10.6, 0)         # VBUS TVS at the receptacle VBUS pins (VBUS pads up)
at('D2', 68.3, 14.6, 270)       # VBUS-GND Schottky (cathode/VBUS up)
orient('C1', 63.4, 13.7, 'PD_VBUS', 'L')    # 4.7 uF VBUS (up 0.4: clear of C6's outline)
orient('C4', 62.75, 19.5, 'PD_VBUS', 'L')    # 10 nF at VBUS_IN (routing: moved off pins 32/33 so CC1/CC2 escape east)
orient('C5', 59.75, 13.15, 'PD_VBUS', 'L')   # up/right: C7 sits on the CC2 lane, PLUG_EVENT via west of it
orient('C2', 55.35, 18.75, 'PD_VBUS', 'U')   # 10 nF at VBUS_IN pins 23-25
orient('C3', 57.6, 19.4, 'PD_VBUS', 'L')
orient('D3', 63.05, 9.3, 'Net-(D3-K)', 'U')   # PESD24 at the receptacle CC1 pin
orient('D4', 60.25, 9.3, 'Net-(D4-K)', 'U')   # PESD24 at CC2
orient('C7', 57.85, 15.05, 'Net-(D4-K)', 'L')   # 330 pF at CC2 pin 29 (same layer, no via pin-to-cap; up 0.43 so the CC1 lane passes under it)
orient('C6', 61.0, 15.8, 'Net-(D3-K)', 'L')     # 330 pF at CC1 pin 28 (on the CC1 lane east of C7; frees the RES lanes)
# top side (LDO / ADC straps)
orient('C9', 55.15, 8.45, 'PD_LDO3V3', 'D')     # LDO_3V3 pin 1
orient('C10', 52.85, 8.6, 'Net-(U1-LDO_1V5)', 'D')
# ADC dividers and pull-ups in one column of horizontal 0402s (signal pads toward the pins, x 50.53; supply/GND pads
# outward, x 49.67), so each divider's mid node is one short vertical and the LDO_3V3 pads form two runs fed from the
# west (routing: the first placement boxed R1's LDO pad in between ADCIN1/ADCIN3 and left no room for the I2C vias).
orient('R4', 50.1, 6.6, 'Net-(U1-ADCIN3)', 'R')    # ADCIN3 lower (GND)
orient('R3', 50.1, 7.85, 'Net-(U1-ADCIN3)', 'R')   # ADCIN3 upper (LDO_3V3)
orient('R1', 50.1, 9.1, 'Net-(U1-ADCIN1)', 'R')    # ADCIN1 upper (LDO_3V3)
orient('R2', 50.1, 10.35, 'Net-(U1-ADCIN1)', 'R')  # ADCIN1 lower (GND)
orient('R6', 50.1, 11.6, 'Net-(U1-ADCIN4)', 'R')   # ADCIN4 lower (GND), shares the R2 GND via
orient('R5', 50.1, 12.85, 'Net-(U1-ADCIN4)', 'R')  # ADCIN4 upper (LDO_3V3)
orient('R12', 50.1, 16.6, 'Net-(U1-FAULT_IN)', 'R')
# I2C pull-ups at their test pads (any point of the bus): the pins' corridor holds the SDA/SCL vias instead
orient('R11', 49.4, 5.0, 'Net-(U1-I2C_SCL)', 'L')
orient('R10', 51.6, 5.0, 'Net-(U1-I2C_SDA)', 'L')
# right side: VIN_3V3 cap + DNP link, reserved pins
orient('C11', 58.7, 11.3, 'Net-(U1-VIN_3V3)', 'L')
orient('R13', 62.0, 11.3, 'Net-(U1-VIN_3V3)', 'L')
orient('R9', 57.3, 12.9, 'Net-(R9-Pad1)', 'L')
orient('R7', 60.7, 18.65, 'Net-(R7-Pad1)', 'L')   # R7/R8 swapped: RES lanes do not cross
orient('R8', 60.7, 17.4, 'Net-(R8-Pad1)', 'L')
# VIN (PPHV) local cap at the PPHV pins + bulk
orient('C8', 51.9, 19.1, 'VIN', 'R')
at('C12', 44.6, 14.2, 0)
# PD status / I2C test pads, GND pad next to them
at('TP5', 47.5, 3.0); at('TP3', 49.5, 3.0); at('TP4', 51.5, 3.0);   # SINK_EN/SCL/SDA order of their L4 lanes (no crossing)
at('TP6', 53.5, 3.0); at('TP7', 55.5, 3.0)
at('TP8', 45.5, 3.0)
at('TP1', 43.5, 3.0)            # VIN

# ---------------------------------------------------------------- 5 V buck (LM5148), TI Fig 9-47 rotated 180 deg
# FET column (VIN end at the top, PGND at the bottom), SW between the FETs feeding the inductor on the left,
# input caps beside the column, controller on the right, shunt + output caps toward the board centre.
QX = 46.5
at('Q30', QX, 24.0, 0)          # high side: drain (VIN) up, source pins down
at('Q31', QX, 31.8, 0)          # low side: drain (SW) up, source pins (PGND) down
orient('C34', QX - 0.8, 19.5, 'VIN', 'D')   # 100 nF HF at the HS drain
orient('C35', QX + 0.8, 19.5, 'VIN', 'D')
for i, ref in enumerate(['C30', 'C31', 'C32', 'C33']):
    orient(ref, 51.6 + 3.4 * i, 23.6, 'VIN', 'U')   # 10 uF 1210, VIN pad up, GND pad down
at('L30', 37.8, 27.8, 180)       # SW pad right (to the FETs), ISNS pad left
at('R30', 28.6, 30.0, 270)       # shunt vertical: ISNS top, 5V_BUS bottom
OUTC = ['C36', 'C37', 'C38', 'C39', 'C40', 'C41']
for i, ref in enumerate(OUTC):
    orient(ref, 21.9 + 3.4 * i, 37.3, '5V_BUS', 'U')
orient('C42', 23.6, 28.0, '5V_BUS', 'R')
orient('C43', 23.6, 31.6, '5V_BUS', 'R')
at('U30', 55.0, 32.6, 180)       # power pins (HO/LO/SW/CBOOT/VCC/PGND) left toward the FETs, analog pins right/top
orient('C44', 52.4, 28.9, 'Net-(U30-VCC)', 'D')      # VCC 2.2 uF at VCC/PGND
orient('C45', 54.0, 28.9, '5V_VDDA', 'D')            # VDDA 100 nF
orient('R35', 55.3, 28.9, 'Net-(U30-FB)', 'D')       # FB lower
orient('R34', 56.55, 28.9, 'Net-(U30-FB)', 'D')      # FB upper (sense from the output)
orient('C48', 57.8, 28.9, 'Net-(U30-EXTCOMP)', 'D')  # CHF
orient('R33', 59.6, 31.0, 'Net-(U30-EXTCOMP)', 'L')  # Rcomp
orient('C47', 61.8, 31.0, '5V_RC', 'L')              # Ccomp
orient('R31', 59.6, 33.55, 'Net-(U30-RT)', 'L')      # RT (below CNFG: RT reaches it on L4, CNFG on L1 above)
orient('R32', 59.6, 32.3, 'Net-(U30-CNFG)', 'L')     # CNFG
orient('C46', 52.9, 36.0, 'Net-(U30-CBOOT)', 'U')    # CBOOT-SW
orient('R38', 54.15, 36.0, 'BUCK_PG', 'U')      # PG pull-up
orient('R37', 55.4, 36.8, 'Net-(U30-EN)', 'U')       # EN lower (R36/R37 0.8 down: ISNS/VOUT/PG vias under the pin row)
orient('R36', 56.65, 36.8, 'Net-(U30-EN)', 'U')      # EN upper (VIN)
at('TP30', 62.5, 37.5)           # 5V_BUS
at('TP31', 54.5, 39.0)           # PG (beside R38: the space at x 62.5 carries the Kelvin/FB lanes)
at('TP32', 62.5, 40.0)           # GND

# ---------------------------------------------------------------- 3V3 buck (TPS54202), back left of the PD sink
# TI Fig 7-16: GND/SW/VIN pins on one side, inductor off SW, input caps at VIN/GND, FB divider on the far side
at('U2', 36.0, 14.5, 270)                     # GND/SW/VIN pins face left, BOOT/EN/FB right
at('L1', 30.6, 10.0, 90)                       # SW pad down (next to the SW pin), 3V3 pad up
orient('C14', 34.6, 17.4, 'VIN', 'U')         # 100 nF at the VIN pin
orient('C13', 33.3, 20.2, 'VIN', 'R')         # 10 uF input
orient('C15', 36.0, 12.2, 'Net-(U2-BOOT)', 'R')
for i, ref in enumerate(['C16', 'C17', 'C18']):
    orient(ref, 27.0 + 2.2 * i, 3.2, '3V3', 'D')   # 22 uF at the inductor's 3V3 pad
orient('R15', 39.0, 14.9, 'Net-(U2-FB)', 'L')   # FB lower
orient('R14', 39.0, 16.15, 'Net-(U2-FB)', 'L')   # FB upper
orient('C19', 39.0, 17.4, 'Net-(U2-FB)', 'L')    # feed-forward
at('TP2', 26.0, 6.8)                          # 3V3

# status LEDs at the back edge (seen through the lid): green PD OK (5V_BUS), red low power
at('D5', 37.0, 1.8, 0)
at('R16', 37.0, 3.2, 0)
at('R17', 37.0, 4.45, 0)
at('D6', 40.4, 1.8, 0)
at('R18', 40.4, 3.35, 0)
at('Q1', 40.4, 5.6, 0)

# ---------------------------------------------------------------- hub A (USB2517) rot 270: DN1-5 face the left edge,
# UP / DN6 / DN7 / crystal on the top side. Pins at 0.5 mm: top y 52.5 (64..49 left->right), left x 23.5 (1..16 top->
# bottom), right x 32.5 (48..33 top->bottom), bottom y 61.5 (17..32 left->right).
at('U4', 28.0, 57.0, 270)
# PLL / RBIAS group left of the top-left corner (traces turn left over the corner, above the DN1 pair)
orient('C56', 21.4, 52.4, '3V3', 'R')                      # VDD33PLL pin 64
orient('R41', 21.4, 51.15, 'Net-(U4-RBIAS)', 'R')          # RBIAS pin 63
orient('C59', 20.4, 49.65, 'Net-(U4-VDD18PLL)', 'R')        # VDD18PLL pin 62, 1 uF
# crystal in the wedge between the UP pair (going up at x 26.75-27.25) and DN1 (going up at x ~18)
at('Y1', 24.3, 48.0, 0)                                   # XTAL1 pad bottom-left, XTAL2 pad top-right
orient('C60', 20.9, 48.2, 'Net-(U4-XTAL1{slash}CLKIN)', 'R')
orient('C61', 24.6, 45.1, 'Net-(U4-XTAL2)', 'R')
at('R40', 20.9, 46.6, 0)                                   # 1 M across the crystal
# supply decoupling: left side VDDA (pins 5, 10) where the DN pairs diverge; top VDDA 57 above the UP/DN7 split
orient('C50', 20.3, 55.25, '3V3', 'R')                     # pin 5 (between DN2 and DN3)
orient('C51', 19.6, 58.0, '3V3', 'R')                     # pin 10 (DN4 turns down left of it, DN5 right of it)
orient('C55', 28.6, 47.8, '3V3', 'D')                      # pin 57: in the wedge right of UP, above the DN7 turn
# right side: two columns of straps, a fan-out channel for vias next to the pins
for ref, y, net in [('C54', 51.75, '3V3'), ('R50', 53.00, 'Net-(U4-LED_A2{slash}PRT_SWP2)'),
                    ('R48', 54.25, 'Net-(U4-LED_B2{slash}BOOST1)'), ('C53', 55.50, '3V3'),
                    ('R45', 56.75, 'Net-(U4-SUSP_IND{slash}NON_REM0)'), ('R43', 58.00, 'Net-(U4-HS_IND{slash}CFG_SEL1)'),
                    ('R44', 59.25, 'Net-(U4-SDA{slash}NON_REM1)'), ('R63', 60.50, 'Net-(U4-PRTPWR7)'),
                    ('R46', 61.75, 'Net-(U4-LED_B3{slash}GANG_EN)'), ('R52', 63.00, 'Net-(U4-LED_A4{slash}PRT_SWP4)')]:
    orient(ref, 35.0, y, net, 'L')
for ref, y, net in [('R49', 51.75, 'Net-(U4-LED_A1{slash}PRT_SWP1)'), ('R47', 53.00, 'Net-(U4-LED_B1{slash}BOOST0)'),
                    ('R51', 54.25, 'Net-(U4-LED_A3{slash}PRT_SWP3)'), ('R42', 58.00, 'Net-(U4-SCL{slash}CFG_SEL0)')]:
    orient(ref, 37.3, y, net, 'L')
# bottom side: via fan-out rows for PRTPWR/OCS right under the pins, then the core caps and straps
orient('C52', 27.6, 65.2, '3V3', 'U')                      # VDD33CR pin 24
orient('C58', 29.2, 65.5, 'Net-(U4-VDD18)', 'U')           # VDD18 pin 25, 1 uF
orient('C57', 25.9, 65.5, '3V3', 'U')                      # 10 uF bulk
orient('R54', 24.1, 64.6, 'Net-(U4-LED_A6{slash}PRT_SWP6)', 'U')
orient('R53', 31.6, 64.6, 'Net-(U4-LED_A5{slash}PRT_SWP5)', 'U')
orient('R55', 22.65, 64.6, 'Net-(U4-LED_A7{slash}PRT_SWP7)', 'U')  # pin 15: trace runs down beside the pin row, DN5 turns down outside it

# ---------------------------------------------------------------- hub B (USB2514B) rot 90: DN1-4 face the right edge.
# Pins: right x 61 (DN4 top y 55 .. DN1 y 59), top y 54 (10..18 right->left), left x 55 (19..27 top->bottom),
# bottom y 60 (28..36 left->right: UP at 57/57.5, XTAL 58/58.5).
at('U5', 58.0, 57.0, 90)
orient('C65', 60.9, 50.9, '3V3', 'D')                      # VDDA pin 10
orient('C68', 58.85, 50.9, 'Net-(U5-CRFILT)', 'D')         # CRFILT pin 14
orient('C66', 57.6, 50.9, '3V3', 'D')                      # VDD33 pin 15
orient('C64', 63.6, 57.0, '3V3', 'L')                      # VDDA pin 5 (between DN2 and DN3)
orient('C67', 52.9, 56.65, '3V3', 'R')                     # VDD33 pin 23
orient('R69', 52.15, 55.4, 'Net-(U5-SDA{slash}NON_REM1)', 'R')   # 0.75 mm west of the strap column (clear of C70): room for pin 22 to reach it past pins 20/21 (hub B routing)
orient('R67', 52.9, 57.9, 'Net-(U5-SCL{slash}CFG_SEL0)', 'R')
orient('R68', 52.9, 59.15, 'Net-(U5-HS_IND{slash}CFG_SEL1)', 'R')
orient('R62', 50.6, 59.15, 'HUBB_VBUS_DET', 'R')
orient('R75', 50.6, 60.4, 'HUBB_VBUS_DET', 'R')            # DNP fallback to 3V3
orient('C70', 49.6, 55.4, '3V3', 'R')                      # 10 uF bulk
orient('C63', 56.1, 61.7, '3V3', 'U')                      # VDDA pin 29
orient('R70', 54.85, 62.0, 'Net-(U5-SUSP_IND{slash}NON_REM0)', 'U')
at('Y2', 60.4, 64.0, 180)                                  # XTALIN pad top-right, XTALOUT bottom-left
orient('C62', 63.8, 61.0, '3V3', 'L')                      # VDDA pin 36
orient('R66', 63.8, 62.25, 'Net-(U5-RBIAS)', 'L')          # RBIAS pin 35
orient('C69', 63.8, 63.5, 'Net-(U5-PLLFILT)', 'L')         # PLLFILT pin 34
orient('C71', 64.0, 64.75, 'Net-(U5-XTALIN{slash}CLKIN)', 'L')
orient('C72', 59.5, 66.9, 'Net-(U5-XTALOUT)', 'R')

# reset supervisor between the hubs (RESET_N to both on L4), test pads beside it
at('U6', 45.0, 57.0, 0)
orient('C73', 45.0, 54.4, '3V3', 'L')
orient('R76', 45.0, 60.0, 'HUB_RESET_N', 'L')
at('TP40', 43.0, 62.0)
at('TP42', 45.6, 62.0)

json.dump(P, open(OUT, 'w'), indent=0)

# ---------------------------------------------------------------- quick self-check (approximates board_lint)
BX = json.load(open(sys.argv[1].replace('fp.json', 'boxes.json')))


def wbox(ref):
    kind, x0, y0, x1, y1 = BX[ref]
    x, y, r = P[ref]
    pts = [R(r, px, py) for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    return kind, (x + min(p[0] for p in pts), y + min(p[1] for p in pts), x + max(p[0] for p in pts), y + max(p[1] for p in pts))


bad = []
refs = sorted(P)
WB = {r: wbox(r) for r in refs}
for i, a in enumerate(refs):
    ka, A = WB[a]
    for b in refs[i + 1:]:
        kb, B = WB[b]
        if ka == 'crt' and kb == 'crt':
            continue
        ox, oy = min(A[2], B[2]) - max(A[0], B[0]), min(A[3], B[3]) - max(A[1], B[1])
        if ox > 0.1 and oy > 0.1:
            bad.append('%s/%s %.2fx%.2f @(%.1f,%.1f)' % (a, b, ox, oy, (max(A[0], B[0]) + min(A[2], B[2])) / 2, (max(A[1], B[1]) + min(A[3], B[3])) / 2))
for r, (k, A) in WB.items():
    if r[0] == 'J' or r[0] == 'H':
        continue
    if A[0] < 0 or A[1] < 0 or A[2] > W or A[3] > H:
        bad.append('%s outside %s' % (r, [round(v, 2) for v in A]))
print('self-check: %d overlaps' % len(bad))
for l in bad:
    print('  ', l)
missing = sorted(set(FP) - set(P))
print('placed', len(P), 'of', len(FP), '; missing', len(missing), ' '.join(missing))
