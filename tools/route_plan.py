"""Routing plan for the usb-hub board (router.py: tracks, vias, zones at chosen coordinates; no autorouter).

  router.py apply hw/usb-hub.kicad_pcb build/pack0/board.json tools/route_plan.py      (tools/build.sh runs it)

Layer plan (docs/layout-plan.md): L1 F.Cu parts, signals and local power pours; L2 In1.Cu solid GND; L3 In2.Cu
5V_BUS pour with PD_VBUS / VIN / GND / 3V3 islands; L4 B.Cu slow signals, the 3V3 trunk and a GND pour.
Coordinates are absolute board mm (outline 100..185). Every track takes its net from the pads it touches (R17);
free points name the net of the pad they continue from.
"""
import math
import os

F, L2, L3, B = 'F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'
SIG = 0.2           # TPS25730 Table 9-1: CC / GPIO / LDO 8 mil minimum
GW = 0.3            # component GND stubs (Table 9-1: 10 mil)
SV = (0.45, 0.2)    # signal / small via (TPS25730 Fig 9-16 minimum is 16 / 8 mil)
PV = (0.6, 0.3)     # power via (~1 A each at 0.3 mm drill)
BOARD = (100.0, 100.0, 185.0, 185.0)

VBUS_PD = '/power_in/PD_VBUS'


# ---------------------------------------------------------------- helpers (nets always from pads)
def pad_on(r, ref, netpart):
    """(ref, num) of the pad of `ref` whose net name contains `netpart`"""
    hits = sorted({num for (rf, num) in r.pads if rf == ref and netpart in r.net(rf, num)})
    assert len(hits) == 1, (ref, netpart, hits)
    return (ref, hits[0])


def via_at(r, pad, at, link_w=GW, v=SV, link=True):
    """via at `at` on the net of `pad`, joined to the pad on F.Cu"""
    net = r.net(*pad)
    ok = r.via(at, net, v[0], v[1])
    if ok and link:
        r.track(F, link_w, pad, at)
    return ok


def poly_rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def net_of(r, ref, num):
    return r.net(ref, str(num))


# ---------------------------------------------------------------- planes
def planes(r):
    gnd = net_of(r, 'J1', '1')
    r.zone(gnd, L2, poly_rect(*BOARD), prio=0, name='L2_GND')
    r.zone(gnd, B, poly_rect(*BOARD), prio=0, name='L4_GND')
    bus = net_of(r, 'R30', '2')
    r.zone(bus, L3, poly_rect(*BOARD), prio=0, name='L3_5V_BUS')
    # PD_VBUS island: J1 VBUS via fields, U1 VBUS pins, the VBUS_IN field below U1
    r.zone(net_of(r, 'C1', '1'), L3, [(154.0, 107.9), (170.3, 107.9), (170.3, 120.9), (154.0, 120.9)],
           prio=2, name='L3_PD_VBUS')
    # VIN island: PPHV / Cin / Q30 drain, C12, the TPS54202 input; stays off the SW node and L30 (GND region below)
    vin = net_of(r, 'C8', '1')
    r.zone(vin, L3, [(131.5, 112.6), (153.7, 112.6), (153.7, 121.1), (165.0, 121.1), (165.0, 127.3),
                     (150.3, 127.3), (150.3, 125.4), (143.3, 125.4), (143.3, 122.7), (131.5, 122.7)],
           prio=2, name='L3_VIN')
    # GND under L30, the SW node and the LM5148 (nothing but GND under SW on the inner layers). From x 154 the top
    # edge is at y 127.0 so the L4 VOUT sense run into the FB via (y 127.5) lies over GND, not over the island gap.
    r.zone(gnd, L3, [(132.3, 122.9), (143.0, 122.9), (143.0, 125.7), (150.0, 125.7), (150.0, 127.6),
                     (154.0, 127.6), (154.0, 127.0), (161.2, 127.0), (161.2, 141.2), (141.2, 141.2),
                     (141.2, 132.9), (132.3, 132.9)],
           prio=3, name='L3_GND_BUCK')


# ---------------------------------------------------------------- (a) PD input: J1, TPS25730
def route_pd(r):
    gnd = net_of(r, 'J1', '1')
    vbus = VBUS_PD
    # J1 GND pins to the shell legs
    r.track(F, GW, ('J1', 'B1'), ('J1', 'A12'), (157.68, 107.345))
    r.track(F, GW, ('J1', 'B12'), ('J1', 'A1'), (166.32, 107.345))
    # VBUS pours at both J1 pin pairs, via fields to the L3 PD_VBUS island
    r.zone(vbus, F, [(156.8, 108.1), (159.35, 108.1), (159.35, 106.9), (159.92, 106.9), (159.92, 110.0),
                     (156.8, 110.0)], prio=5, name='F_VBUS_L')
    r.via_field(vbus, 157.2, 108.75, 159.0, 109.65, pitch=0.9, size=PV[0], drill=PV[1])
    r.zone(vbus, F, [(164.0, 106.9), (164.75, 106.9), (164.75, 108.05), (169.8, 108.05), (169.8, 113.5),
                     (166.2, 113.5), (166.2, 112.8), (162.7, 112.8), (162.7, 114.85), (161.2, 114.85),
                     (161.2, 112.1), (166.15, 112.1), (166.15, 109.95), (163.6, 109.95), (163.6, 108.05),
                     (164.0, 108.05)], prio=5, name='F_VBUS_R')
    r.via_field(vbus, 166.5, 108.65, 169.2, 111.0, pitch=0.9, size=PV[0], drill=PV[1])
    r.via((161.55, 112.35), vbus, *PV)
    # D1 TVS: GND pads into the exposed pad, two vias in it; D3 GND to the same pad
    for n, x in (('1', 164.35), ('2', 165.0), ('3', 165.65)):
        r.track(F, 0.28, ('D1', n), (x, 110.75))
    r.via_field(gnd, 164.6, 110.6, 165.4, 110.6, pitch=0.8, size=SV[0], drill=SV[1], in_pad=('D1', '7'))
    r.track(F, GW, ('D3', '2'), (163.75, 110.6), ('D1', '7'))
    # GND pour for C1 / D2 / C6 / R7 / R8 GND pads
    r.zone(gnd, F, [(161.0, 115.1), (163.3, 115.1), (163.3, 113.05), (166.4, 113.05), (166.4, 113.75),
                    (170.2, 113.75), (170.2, 118.5), (161.0, 118.5)], prio=4, name='F_GND_PD_R')
    r.via_field(gnd, 163.7, 115.6, 169.7, 118.0, pitch=1.2)

    # CC: receptacle -> PESD24 -> via -> L4 -> via after the 330 pF cap -> cap -> pin (TPS25730 s9.4.1.3)
    r.track(F, SIG, ('J1', 'B5'), ('D4', '1'))
    r.track(F, SIG, ('J1', 'A5'), (163.25, 108.35), ('D3', '1'))
    cc2a, cc1a = (161.0, 108.65), (162.35, 108.45)
    via_at(r, ('D4', '1'), cc2a, SIG)
    via_at(r, ('D3', '1'), cc1a, SIG)
    cc2b, cc1b = (157.35, 114.15), (160.3, 114.85)
    r.track(F, SIG, ('U1', '29'), (156.5, 115.4), ('C7', '1'))
    via_at(r, ('C7', '1'), cc2b, SIG)
    r.track(F, SIG, ('U1', '28'), (159.5, 115.8), ('C6', '1'))
    via_at(r, ('C6', '1'), cc1b, SIG)
    cc1 = r.net('C6', '1')
    cc2 = r.net('C7', '1')
    r.track(B, SIG, cc1a, (162.35, 113.9), (161.4, 114.85), cc1b, net=cc1)
    r.track(B, SIG, cc2a, (160.9, 108.85), (160.9, 113.35), (157.35, 113.35), cc2b, net=cc2)
    # D4 GND, C7/R9 GND, C11/C5 GND
    via_at(r, ('D4', '2'), (160.25, 110.25))
    r.via((158.2, 114.2), gnd, *SV)
    r.track(F, GW, ('R9', '2'), (158.2, 114.2), ('C7', '2'))
    r.via((159.75, 112.3), gnd, *SV)
    r.track(F, GW, ('C11', '2'), (159.75, 112.3), ('C5', '2'))

    # U1 right column
    r.track(F, SIG, ('U1', '38'), (156.35, 111.5), (157.1, 111.5))                 # VIN_3V3 -> C11
    pe = (158.65, 112.45)
    r.track(F, SIG, ('U1', '37'), (156.8, 112.2), (157.0, 112.27), (158.4, 112.27), pe)   # PLUG_EVENT
    r.via(pe, r.net('U1', '37'), *SV)
    r.track(F, SIG, ('U1', '36'), (156.5, 112.6), ('R9', '1'))
    r.track(F, SIG, ('U1', '35', 1), (155.2, 113.2))
    r.track(F, GW, ('U1', '33', 1), (156.65, 114.0))                            # VBUS sense pins 32/33
    r.via((156.65, 114.0), vbus, *SV)
    r.track(F, SIG, (155.9, 114.62), (155.2, 114.62), net=gnd)
    r.track(F, SIG, ('U1', '30'), (155.15, 115.1))                              # DRAIN pins into pad 40
    r.track(F, SIG, ('U1', '15'), (152.85, 115.1))
    r.track(F, 0.3, ('C5', '1'), (159.6, 114.0))
    r.via((159.6, 114.0), vbus, *SV)
    # reserved pins 26/27 -> 10 k to GND
    r.track(F, SIG, ('U1', '27'), (158.9, 116.2), (159.2, 116.5), (159.2, 117.4), ('R8', '1'))
    r.track(F, SIG, ('U1', '26'), (158.5, 116.6), (158.5, 118.65), ('R7', '1'))

    # U1 left column
    r.track(F, SIG, ('U1', '7'), (151.3, 111.8), pad_on(r, 'R6', 'ADCIN4'))
    r.track(F, SIG, pad_on(r, 'R6', 'ADCIN4'), pad_on(r, 'R5', 'ADCIN4'))
    sda_v, scl_v = (150.6, 113.75), (150.6, 114.65)
    r.track(F, SIG, ('U1', '8'), (151.08, 112.2), (151.08, 113.4), sda_v)
    r.via(sda_v, r.net('U1', '8'), *SV)
    r.track(F, SIG, ('U1', '9'), (151.48, 112.6), (151.48, 114.5), scl_v)
    r.via(scl_v, r.net('U1', '9'), *SV)
    for n, y in (('11', 113.4), ('12', 113.8), ('14', 114.5)):
        r.track(F, SIG, ('U1', n), (152.85, y))
    g16 = (151.2, 115.6)
    r.via(g16, gnd, *SV)
    r.track(F, 0.25, ('U1', '16'), g16)
    r.track(F, 0.25, ('U1', '17'), g16)
    r.track(F, SIG, ('U1', '18'), (151.5, 116.2), (151.1, 116.6), pad_on(r, 'R12', 'FAULT_IN'))
    se = (151.25, 117.2)
    r.track(F, SIG, ('U1', '19'), (151.65, 116.6), se)
    r.via(se, r.net('U1', '19'), *SV)

    # U1 top row: LDO_3V3, ADCIN1 (via), LDO_1V5, ADCIN3 (lane under C10), CAP_MIS (via)
    r.track(F, SIG, ('U1', '1'), (155.5, 110.8), (155.5, 109.9))
    a1 = (154.7, 110.55)
    r.track(F, SIG, ('U1', '2'), (154.6, 110.9), a1)
    r.via(a1, r.net('U1', '2'), *SV)
    ldo = r.net('U1', '3')
    r.track(F, SIG, ('U1', '3'), (154.2, 109.9), (154.55, 109.9))
    r.track(F, SIG, (154.2, 109.9), (154.2, 105.7), (148.3, 105.7), (148.3, 112.85), pad_on(r, 'R5', 'LDO3V3'),
            pad_on(r, 'R12', 'LDO3V3'), net=ldo)
    r.track(F, SIG, (148.3, 107.85), pad_on(r, 'R3', 'LDO3V3'), pad_on(r, 'R1', 'LDO3V3'))
    for ref in ('R11', 'R10'):
        q = pad_on(r, ref, 'LDO3V3')
        r.track(F, SIG, q, (r.P(*q)[0], 105.7))
    r.track(F, SIG, ('U1', '4'), (153.8, 109.9), (153.45, 109.9))
    r.track(F, SIG, ('U1', '5'), (153.4, 110.56), (151.3, 110.56), (151.3, 107.85), pad_on(r, 'R3', 'ADCIN3'),
            pad_on(r, 'R4', 'ADCIN3'))
    cm = (152.35, 111.1)
    r.track(F, SIG, ('U1', '6'), cm)
    r.via(cm, r.net('U1', '6'), *SV)
    # ADCIN1 divider fed from L4
    a1b = (148.95, 109.725)
    r.via(a1b, r.net('U1', '2'), *SV)
    r.track(F, SIG, a1b, (150.533, 109.725), net=r.net('U1', '2'))
    r.track(F, SIG, pad_on(r, 'R1', 'ADCIN1'), pad_on(r, 'R2', 'ADCIN1'))
    r.track(B, SIG, a1, (154.35, 110.2), (149.4, 110.2), a1b, net=r.net('U1', '2'))
    # strap GND vias
    via_at(r, pad_on(r, 'R4', 'GND'), (148.95, 106.6))
    g26 = (148.95, 110.975)
    r.via(g26, gnd, *SV)
    r.track(F, GW, pad_on(r, 'R2', 'GND'), g26, pad_on(r, 'R6', 'GND'))
    # second stitch for the L4 GND strip between the ADCIN1 and CAP_MIS lanes (pour_check: 1 via = WEAK)
    assert any(r.via(pt, gnd, *SV, quiet=True) for pt in ((151.0, 110.975), (150.95, 111.0), (151.2, 110.95), (150.0, 110.975))), \
        'no spot for the second L4 GND strip via'
    # LDO caps' GND
    via_at(r, ('C9', '2'), (156.3, 107.45))
    via_at(r, ('C10', '2'), (152.85, 106.4))
    # exposed pad: 3 x 3 thermal vias in the GND pad
    r.via_field(gnd, 153.1, 112.335, 154.9, 114.135, pitch=0.9, size=PV[0], drill=PV[1], in_pad=('U1', '39'))

    # status lines to the test pads on L4 (TP order SINK_EN / SCL / SDA / CAP_MIS / PLUG_EVENT, west to east)
    tv = {}
    for tp, x in (('TP5', 147.5), ('TP3', 149.5), ('TP4', 151.5), ('TP6', 153.5), ('TP7', 155.7)):
        tv[tp] = (x, 104.3)
        r.via(tv[tp], r.net(tp, '1'), *SV)
        r.track(F, SIG, (tp, '1'), tv[tp])
    r.track(F, SIG, tv['TP3'], pad_on(r, 'R11', 'SCL'))
    r.track(F, SIG, tv['TP4'], pad_on(r, 'R10', 'SDA'))
    r.track(B, SIG, se, (147.0, 117.2), (147.0, 104.8), tv['TP5'], net=r.net('U1', '19'))
    r.track(B, SIG, scl_v, (147.4, 114.65), (147.4, 104.95), (149.5, 104.95), tv['TP3'], net=r.net('U1', '9'))
    r.track(B, SIG, sda_v, (147.8, 113.75), (147.8, 105.4), (151.5, 105.4), tv['TP4'], net=r.net('U1', '8'))
    r.track(B, SIG, cm, (151.7, 111.75), (148.2, 111.75), (148.2, 105.85), (153.5, 105.85), tv['TP6'],
            net=r.net('U1', '6'))
    r.track(B, SIG, pe, (155.7, 112.45), tv['TP7'], net=r.net('U1', '37'))

    # VIN_3V3 (C11) to the DNP R13 link on L4, around the CC vias; R13's 3V3 side from Q1's 3V3 via (route_3v3)
    v33 = r.net('C11', '1')
    va, vb = (156.4, 110.55), (161.6, 110.5)
    r.via(va, v33, *SV)
    r.track(F, SIG, va, (157.1, 110.9), net=v33)
    r.track(B, SIG, va, (156.4, 108.45), (156.75, 108.1), (161.65, 108.1), vb, net=v33)
    via_at(r, ('R13', '1'), vb, SIG)

    # VBUS_IN: L1 pour under the pins 23-25 to C2/C3/C4 and a via field to the L3 PD_VBUS island
    r.zone(vbus, F, [(154.1, 116.75), (158.2, 116.75), (158.2, 119.0), (163.6, 119.0), (163.6, 120.75),
                     (154.5, 120.75), (154.5, 117.6), (154.1, 117.6)], prio=7, name='F_VBUS_IN')
    via_at(r, ('C2', '2'), (155.35, 119.85))
    via_at(r, ('C3', '2'), (158.02, 120.15))
    via_at(r, ('C4', '2'), (163.17, 120.3))
    r.via_field(vbus, 155.0, 119.45, 163.1, 120.35, pitch=0.9, size=PV[0], drill=PV[1])
    r.via_field(vbus, 156.1, 117.65, 157.9, 118.45, pitch=0.8, size=PV[0], drill=PV[1])

    # PPHV -> VIN: L1 pour from the PPHV pins over C8, along the Cin row to the Q30 drain; vias to the L3 VIN island
    vin = r.net('C8', '1')
    r.zone(vin, F, [(152.55, 116.95), (153.95, 116.95), (153.95, 117.6), (154.3, 117.6), (154.3, 120.95),
                    (163.45, 120.95), (163.45, 123.2), (149.8, 123.2), (149.8, 125.45), (143.95, 125.45),
                    (143.95, 119.5), (149.3, 119.5), (149.3, 120.95), (152.55, 120.95)], prio=6, name='F_VIN')
    for x in (144.6, 146.5, 148.3):
        r.via((x, 120.0), vin, *PV)
    for y in (121.6, 122.5, 123.4, 124.3, 125.2):
        r.via((149.45, y), vin, *PV)
    r.via_field(vin, 144.7, 122.2, 148.3, 124.6, pitch=1.2, size=PV[0], drill=PV[1], in_pad=('Q30', '9'))
    # GND pour for the C12 / C8 / C34 / C35 GND pads
    r.zone(gnd, F, [(145.3, 113.35), (149.3, 113.35), (149.3, 117.6), (151.6, 117.6), (151.6, 120.6),
                    (149.3, 120.6), (149.3, 119.35), (145.2, 119.35)], prio=4, name='F_GND_PD_L')
    r.via_field(gnd, 145.6, 115.4, 148.8, 117.4, pitch=1.0)
    r.via_field(gnd, 145.7, 118.35, 147.5, 118.35, pitch=0.9)
    for y in (118.2, 119.4):
        r.via((151.65, y), gnd, *PV)
    # C12 (bulk) VIN pad onto the L3 VIN island; TP1 (VIN) to it
    for x in (141.0, 142.2, 143.4):
        via_at(r, ('C12', '1'), (x, 115.45), 0.6, PV)
    r.track(F, 0.4, ('TP1', '1'), (143.5, 113.7), (143.0, 114.2))


# ---------------------------------------------------------------- (b) LM5148 5 V / 17 A buck (TI Fig 9-47, rotated)
def route_buck(r):
    gnd = net_of(r, 'J1', '1')
    sw, isns, bus, vin = r.net('L30', '1'), r.net('L30', '2'), r.net('R30', '2'), r.net('Q30', '9')
    # power copper on L1: SW node kept small (no vias), L30 -> R30 shunt, R30 -> output caps; Cin / Q31 PGND
    r.zone(sw, F, [(139.7, 123.1), (142.6, 123.1), (142.6, 125.8), (147.85, 125.8), (147.85, 127.75),
                   (149.0, 127.75), (149.0, 133.2), (139.7, 132.5)], prio=6, name='F_5V_SW')
    r.zone(isns, F, [(126.8, 123.1), (135.9, 123.1), (135.9, 132.5), (133.0, 132.5), (133.0, 127.95),
                     (126.8, 127.95)], prio=6, name='F_5V_ISNS')
    r.zone(bus, F, [(123.95, 126.4), (126.2, 126.4), (126.2, 131.9), (130.6, 131.9), (130.6, 132.75),
                    (140.3, 132.75), (140.3, 137.4), (120.4, 137.4), (120.4, 134.75), (123.95, 134.75)],
           prio=6, name='F_5V_BUS_OUT')
    r.zone(gnd, F, [(120.4, 137.75), (140.6, 137.75), (140.6, 140.9), (120.4, 140.9)], prio=5, name='F_GND_COUT')
    r.zone(gnd, F, [(120.4, 126.4), (123.45, 126.4), (123.45, 134.4), (120.4, 134.4)], prio=5, name='F_GND_C42')
    r.zone(gnd, F, [(151.0, 124.15), (163.5, 124.15), (163.5, 126.85), (151.0, 126.85)], prio=5, name='F_GND_CIN')
    r.zone(gnd, F, [(143.9, 133.95), (147.75, 133.95), (147.75, 137.4), (143.9, 137.4)], prio=5, name='F_GND_Q31')

    # Kelvin ISNS+ / VOUT from the shunt's inner pad edges, as a pair on L4 (y 141.5 / 141.9), away from SW
    isns_a, vout_a = (128.6, 128.7), (128.0, 131.0)
    isns_b, vout_b = (155.7, 135.3), (157.7, 135.55)
    fb_v = (156.55, 127.5)
    r.track(F, 0.25, ('R30', '1'), isns_a)
    r.track(F, 0.25, ('R30', '2'), (128.6, 132.0), vout_a)
    for v, n in ((isns_a, isns), (vout_a, bus), (isns_b, isns), (vout_b, bus), (fb_v, bus)):
        r.via(v, n, *SV)
    # L3 kept off the VOUT Kelvin via (it must meet 5V_BUS only at R30:2), small enough that ISNS beside it stays
    # over L3 copper
    r.keepout(L3, poly_rect(vout_a[0] - 0.45, vout_a[1] - 0.45, vout_a[0] + 0.45, vout_a[1] + 0.45), name='KELVIN_VOUT')
    r.track(B, SIG, isns_a, (128.7, 128.8), (128.7, 141.5), (158.8, 141.5), (158.8, 136.3), (155.7, 136.3), isns_b, net=isns)
    r.track(B, SIG, vout_a, (128.2, 131.2), (128.2, 141.9), (159.2, 141.9), (159.2, 127.5), fb_v, net=bus)
    r.track(B, SIG, (159.2, 135.0), (157.7, 135.0), vout_b, net=bus)
    r.track(F, SIG, ('U30', '20'), isns_b)
    r.track(F, 0.15, ('U30', '21'), (156.25, 135.25), (156.55, 135.55), vout_b)
    r.track(F, SIG, fb_v, (156.55, 127.9), ('R34', '2'), net=bus)

    # output: 5V_BUS via fields to the L3 plane (17 A), output-cap GND vias; Kelvin corridor x 127.3-129.4 kept clear
    r.via_field(bus, 130.9, 133.45, 140.0, 134.35, pitch=0.9, size=PV[0], drill=PV[1])
    for x0, x1 in ((120.9, 126.9), (129.6, 139.9)):
        r.via_field(bus, x0, 137.05, x1, 137.05, pitch=0.9, size=PV[0], drill=PV[1])
        # output-cap GND at 1.8 mm pitch: at 0.9 mm the L3 antipads merge into a wall across the 5V_BUS plane
        r.via_field(gnd, x0, 140.3, x1, 140.3, pitch=1.8, size=PV[0], drill=PV[1])
    r.via_field(bus, 126.45, 128.6, 126.45, 131.3, pitch=0.9, size=PV[0], drill=PV[1])
    r.via_field(gnd, 120.75, 126.9, 120.75, 133.9, pitch=1.8, size=PV[0], drill=PV[1])
    # PGND: Cin returns and the Q31 source straight down to L2
    r.via_field(gnd, 144.6, 136.1, 147.3, 136.9, pitch=0.8, size=PV[0], drill=PV[1])
    for x in (153.3, 156.7, 160.1):
        for y in (124.6, 125.5):
            r.via((x, y), gnd, *SV)
    for x in (151.4, 153.8, 154.7, 157.4, 158.3, 159.2, 160.9, 161.8, 162.7):
        r.via((x, 126.45), gnd, *PV)

    # gate drive: HO with SW beside it on L1 (pair), LO on L4 over the L3 GND region
    ho, lo = r.net('Q30', '4'), r.net('Q31', '4')
    r.track(F, 0.3, ('U30', '13'), (151.6, 133.35))
    r.track(F, 0.65, (151.6, 133.35), (150.4, 133.35), (150.4, 126.75), ('Q30', '4'), net=ho)
    r.track(F, 0.3, ('U30', '14'), (152.55, 134.75), (152.2, 134.75))
    r.track(F, 0.3, (152.2, 134.75), (152.2, 136.42), ('C46', '2'), net=sw)
    r.track(F, 0.65, (152.2, 134.75), (149.5, 134.75), (149.5, 128.775), ('Q31', '5'), net=sw)
    r.track(F, SIG, ('U30', '15'), (153.25, 134.85), ('C46', '1'))
    lo_a, lo_b = (152.0, 130.4), (148.6, 136.25)
    r.track(F, 0.3, ('U30', '11'), lo_a)
    r.via(lo_a, lo, *SV)
    r.track(B, 0.5, lo_a, (150.95, 130.4), (150.95, 136.25), lo_b, net=lo)
    r.via(lo_b, lo, *PV)
    r.track(F, 0.5, lo_b, ('Q31', '4'), net=lo)

    # VIN (bias) for pin 12 and the EN divider top, on L4 into the L3 VIN island
    vin_a, vin_b, vin_c = (151.65, 132.1), (152.6, 127.0), (156.65, 138.0)
    r.track(F, 0.3, ('U30', '12'), vin_a)
    r.via(vin_a, vin, *SV)
    r.via(vin_b, vin, *PV)
    r.track(B, 0.3, vin_a, (152.6, 132.1), vin_b, net=vin)
    r.track(B, 0.3, (152.6, 132.1), (152.6, 138.0), vin_c, net=vin)
    via_at(r, ('R36', '1'), vin_c, 0.3)

    # VCC / VDDA / AGND / PGND at the pins; exposed pad 3 x 2 vias (AGND and PGND meet at the DAP)
    r.track(F, 0.3, ('U30', '9'), (153.75, 130.3), (153.55, 130.1), (152.6, 130.1), ('C44', '1'))
    via_at(r, ('C44', '2'), (151.6, 128.2))
    r.track(F, SIG, ('U30', '8'), (154.2, 129.4))
    vdda_a, vdda_b = (153.3, 129.35), (154.75, 137.1)
    via_at(r, ('C45', '1'), vdda_a, SIG)
    r.track(B, SIG, vdda_a, (153.3, 136.5), vdda_b, net=r.net('C45', '1'))
    r.track(F, SIG, ('U30', '18'), (154.75, 136.433), ('R38', '2'))
    r.via(vdda_b, r.net('C45', '1'), *SV)
    r.track(F, SIG, (154.75, 136.433), vdda_b, net=r.net('C45', '1'))
    r.track(F, SIG, ('C45', '2'), ('R35', '2'))
    r.track(F, SIG, ('U30', '7'), (154.75, 128.47))
    r.track(F, SIG, ('U30', '7'), (154.75, 131.75))
    r.track(F, SIG, ('U30', '10'), (153.25, 131.4), (153.6, 131.75))
    r.track(F, SIG, ('U30', '16'), (153.75, 133.45))
    r.track(F, SIG, ('U30', '2'), (157.25, 131.2), ('U30', '1'))
    r.track(F, SIG, ('U30', '1'), (156.4, 131.85))
    r.track(F, SIG, ('U30', '24'), (156.4, 133.35))
    r.track(F, SIG, ('U30', '23'), (157.25, 133.75), ('U30', '24'))
    r.track(F, SIG, ('U30', '22'), (156.75, 133.55), (156.45, 133.55))
    r.via_field(gnd, 154.0, 132.1, 156.0, 133.1, pitch=1.0, size=PV[0], drill=PV[1], in_pad=('U30', '25'))

    # FB divider at FB, EXTCOMP / RT / CNFG escapes (RT on L4), compensation
    r.track(F, SIG, ('U30', '6'), ('R35', '1'), ('R34', '1'))
    r.track(F, 0.15, ('U30', '5'), (155.75, 129.85), (158.85, 129.85), (159.167, 130.2), ('R33', '1'))
    r.track(F, 0.15, (157.8, 129.85), ('C48', '1'), net=r.net('U30', '5'))
    via_at(r, ('C48', '2'), (158.45, 128.1), SIG)
    rt_a, rt_b = (156.25, 130.3), (158.4, 133.55)
    r.track(F, 0.15, ('U30', '4'), rt_a)
    r.via(rt_a, r.net('U30', '4'), *SV)
    r.track(B, SIG, rt_a, (157.3, 130.3), (158.4, 131.4), rt_b, net=r.net('U30', '4'))
    via_at(r, ('R31', '1'), rt_b, SIG)
    r.track(F, 0.15, ('U30', '3'), (156.75, 130.3), (158.45, 130.3), (158.45, 132.3), ('R32', '1'))
    r.track(F, SIG, ('R33', '2'), ('C47', '1'))
    r.track(F, GW, ('R32', '2'), ('R31', '2'))
    r.via((160.75, 132.9), gnd, *SV)
    r.track(F, GW, ('R32', '2'), (160.75, 132.9), net=gnd)
    via_at(r, ('C47', '2'), (162.85, 131.0))

    # EN divider, PG pull-up and test pad, CBOOT done above; R37 GND via
    r.track(F, SIG, ('U30', '19'), (155.25, 134.8), (155.12, 135.0), (155.12, 136.2), ('R37', '1'), ('R36', '2'))
    via_at(r, ('R37', '2'), (155.4, 138.75))
    r.track(F, SIG, ('U30', '17'), ('R38', '1'), (153.5, 135.9), (153.5, 138.5), ('TP31', '1'))
    # test pads
    via_at(r, ('TP30', '1'), (163.5, 137.5), 0.4, PV)
    via_at(r, ('TP32', '1'), (163.5, 140.0), 0.4, PV)


# ---------------------------------------------------------------- (c) TPS54202 3V3 buck (TI Fig 7-16) and its output
def route_3v3(r):
    gnd = net_of(r, 'J1', '1')
    vin, v33, bus = r.net('C13', '1'), r.net('L1', '2'), r.net('R30', '2')
    # SW pin -> inductor on L1 (no SW vias); BOOT cap; GND pin straight to L2
    r.track(F, 0.8, ('U2', '2'), (133.6, 114.5), (132.2, 113.6))
    r.track(F, 0.4, ('L1', '1'), (132.0, 112.2), ('C15', '2'))
    via_at(r, ('U2', '1'), (133.6, 112.95), 0.4)
    r.track(F, 0.3, ('U2', '6'), ('C15', '1'))
    # VIN: pour from the VIN pin over C14 and C13, vias to the L3 VIN island
    r.zone(vin, F, [(133.9, 115.15), (135.95, 115.15), (135.95, 122.6), (133.9, 122.6)], prio=6, name='F_VIN_U2')
    via_at(r, ('C14', '2'), (133.65, 117.82))
    for at in ((134.3, 122.15), (135.3, 122.15), (135.55, 117.55), (135.55, 118.35)):
        r.via(at, vin, *PV)
    for y in (119.3, 120.2, 121.1):
        via_at(r, ('C13', '2'), (130.35, y), 0.4, PV)
    # FB divider on the far side, sensed from the output caps on L4 (separate VOUT path to the divider)
    r.track(F, SIG, ('R15', '1'), ('R14', '2'), ('C19', '2'))
    r.track(F, SIG, ('U2', '4'), (138.567, 115.45), net=r.net('U2', '4'))
    via_at(r, ('R15', '2'), (139.433, 114.15))
    r.track(F, SIG, ('R14', '1'), ('C19', '1'))
    s_a, s_b = (132.9, 104.2), (140.1, 117.9)
    via_at(r, ('C18', '1'), s_a, 0.3)
    via_at(r, ('C19', '1'), s_b, SIG)
    r.track(B, 0.3, s_a, (133.6, 104.9), (137.9, 104.9), (137.9, 117.9), s_b, net=v33)
    # output pour at the inductor, C16-C18 and TP2; GND pour + vias at their GND pads
    r.zone(v33, F, [(125.4, 103.3), (132.5, 103.3), (132.5, 108.45), (125.4, 108.45)], prio=6, name='F_3V3_OUT')
    r.zone(gnd, F, [(125.6, 100.45), (132.6, 100.45), (132.6, 103.0), (125.6, 103.0)], prio=5, name='F_GND_3V3_OUT')
    r.via_field(gnd, 126.0, 100.95, 132.3, 100.95, pitch=0.9, size=PV[0], drill=PV[1])
    # 3V3 trunk (L4) to the hub islands; Q1 and the DNP R13 link fed from the sense line's start
    trunk = (125.5, 104.25)
    r.via(trunk, v33, *PV)
    r.track(B, 0.6, trunk, (119.0, 104.25), (118.5, 104.75), (118.5, 145.3), net=v33)
    r.via((118.5, 145.3), v33, *PV)                                    # into the L3 3V3 island A
    q1v, r13v = (142.6, 104.9), (163.0, 111.45)
    r.track(B, 0.3, (137.9, 104.9), q1v, (142.6, 101.0), (170.6, 101.0), (170.6, 111.75), (163.3, 111.75), r13v,
            net=v33)
    r.via(q1v, v33, *SV)
    r.track(F, 0.3, q1v, ('Q1', '2'), net=v33)
    via_at(r, ('R13', '2'), r13v, SIG)


# ---------------------------------------------------------------- (d) status LEDs and power test pads
def route_status(r):
    gnd = net_of(r, 'J1', '1')
    bus = r.net('R30', '2')
    via_at(r, ('D5', '1'), (136.25, 100.95))
    via_at(r, ('D6', '2'), (139.65, 100.95))
    r.track(F, SIG, ('R16', '2'), ('D5', '2'))
    r.track(F, 0.3, ('R16', '1'), ('R17', '1'))
    via_at(r, ('R16', '1'), (135.85, 103.8), 0.3, PV)
    via_at(r, ('R17', '2'), (138.1, 104.2))
    r.track(F, SIG, ('Q1', '3'), ('R18', '1'))
    r.track(F, SIG, ('R18', '2'), ('D6', '1'))
    via_at(r, ('Q1', '1'), (142.4, 107.1), 0.3, PV)
    via_at(r, ('TP8', '1'), (145.5, 104.2), 0.4)


# ---------------------------------------------------------------- power hook-ups of the port clusters, host and hubs
# Port clusters are one frame rotated (tools/place_gen.py): coordinates are written for port 1 and mapped.
PORTS = {1: ('left', 21.0), 2: ('left', 42.5), 3: ('left', 64.0), 4: ('front', 16.0), 5: ('front', 33.7),
         6: ('front', 51.3), 7: ('front', 69.0), 8: ('right', 64.0), 9: ('right', 42.5), 10: ('right', 21.0)}
PULLDOWN = {1: 'R56', 2: 'R57', 3: 'R58', 4: 'R59', 5: 'R60', 6: 'R61', 7: 'R71', 8: 'R72', 9: 'R73', 10: 'R74'}


def port_xy(k, x1, y1):
    """a point given in port 1's absolute coordinates, in port k's frame"""
    edge, s = PORTS[k]
    ax, ay = {'left': (0.0, s), 'front': (s, 85.0), 'right': (85.0, s)}[edge]
    t = math.radians({'left': 270, 'front': 0, 'right': 90}[edge])
    u, w = y1 - 121.0, 100.0 - x1
    return (round(100 + ax + u * math.cos(t) + w * math.sin(t), 4), round(100 + ay - u * math.sin(t) + w * math.cos(t), 4))


def route_port_power(r, k):
    gnd = net_of(r, 'J1', '1')
    n = 100 * k
    J, ESD, TVS, LED = 'J%d' % (n + 1), 'U%d' % (n + 2), 'D%d' % (n + 1), 'D%d' % (n + 2)
    SW, CIN, C2, C3, RSET = 'U%d' % (n + 1), 'C%d' % (n + 1), 'C%d' % (n + 2), 'C%d' % (n + 3), 'R%d' % (n + 1)

    def P(x, y):
        return port_xy(k, x, y)
    # receptacle GND pins, VBUS caps and LED cathode to the shell legs (plated, on every GND plane)
    r.track(F, 0.4, (J, 'A1B12'), (J, '4'))
    r.track(F, 0.4, (J, 'B1A12'), (J, '1'))
    r.track(F, 0.3, (C3, '2'), (J, '4'))
    r.track(F, 0.3, (C2, '2'), (J, '4'))
    r.track(F, 0.3, (LED, '1'), (J, '3'))
    # TPD4E05U06 GND pins tied under the body, one via beyond pin 8 between the D- and CC lanes
    r.track(F, 0.3, (ESD, '3'), (ESD, '8'))
    via_at(r, (ESD, '8'), P(110.75, 121.0))
    # SY6863: GND via under the body; IN on the 5V_BUS plane through 3 vias at its input cap
    via_at(r, (SW, '2'), P(110.0, 114.2))
    r.track(F, 0.5, (CIN, '1'), (SW, '6'))
    # L1 copper from the CIN pad to IN (pin 6): 1.7 A per port; a 0.5 mm track alone runs at > 3.2 A/mm (power.py)
    r.zone(r.net(SW, '6'), F, [P(109.9, 110.95), P(110.75, 110.95), P(111.9, 112.95), P(111.9, 113.55),
                               P(110.8, 113.55), P(109.9, 111.85)], prio=5, name='F_5V_IN_P%d' % k)
    for x, y in ((109.2, 111.0), (109.2, 111.9), (110.1, 110.35)):
        via_at(r, (CIN, '1'), P(x, y), 0.5, PV)
    via_at(r, (CIN, '2'), P(112.55, 111.4))
    via_at(r, (TVS, '2'), P(110.15, 118.4))
    via_at(r, (PULLDOWN[k], '2'), P(113.4, 116.4))
    via_at(r, (RSET, '2'), P(114.1, 114.2))


def route_host_power(r):
    gnd = net_of(r, 'J1', '1')
    r.track(F, 0.4, ('J2', 'A1B12'), ('J2', '4'))
    r.track(F, 0.4, ('J2', 'B1A12'), ('J2', '1'))
    r.track(F, 0.3, ('U7', '3'), ('U7', '8'))
    via_at(r, ('U7', '8'), (120.0, 110.75))
    via_at(r, ('D40', '2'), (122.6, 110.15))
    via_at(r, ('C74', '2'), (124.0, 110.75))
    via_at(r, ('R65', '2'), (126.5, 110.8))
    via_at(r, ('R77', '2'), (117.1, 110.5))
    via_at(r, ('R78', '2'), (115.9, 110.5))


def near(r, ref, num, prefer):
    """via next to a pad (closest legal spot, biased to `prefer`), linked on F.Cu"""
    return r.via_near(ref, num, prefer=prefer, size=SV[0], drill=SV[1], max_r=2.5)


def route_hub_power(r):
    gnd = net_of(r, 'J1', '1')
    v33 = r.net('U4', '5')
    # exposed pads: 4 x 4 (USB2517) and 3 x 3 (USB2514B) GND vias
    r.via_field(gnd, 126.5, 155.5, 129.5, 158.5, pitch=1.0, size=PV[0], drill=PV[1], in_pad=('U4', '65'))
    r.via_field(gnd, 157.0, 156.0, 159.0, 158.0, pitch=1.0, size=PV[0], drill=PV[1], in_pad=('U5', '37'))
    r.track(F, SIG, ('U4', '13'), (125.7, 159.25))
    r.track(F, SIG, ('U4', '19'), (125.25, 160.8), (125.7, 159.3))
    # hub A 3V3 pins to their caps on L1
    r.track(F, SIG, ('U4', '5'), ('C50', '1'))
    r.track(F, SIG, ('U4', '10'), ('C51', '1'))
    r.track(F, SIG, ('U4', '24'), ('C52', '1'), ('C57', '1'))
    r.track(F, SIG, ('U4', '46'), (133.5, 154.25), (134.3, 155.05), ('C53', '1'))
    r.track(F, SIG, ('U4', '52'), (130.25, 150.5), (134.0, 150.5), (134.58, 151.1), ('C54', '1'))
    r.track(F, SIG, ('U4', '57'), (127.75, 149.0), ('C55', '1'))
    r.track(F, SIG, ('U4', '64'), (123.9, 152.2), (122.2, 152.2), ('C56', '1'))
    # hub B
    r.track(F, SIG, ('U5', '5'), ('C64', '1'))
    r.track(F, SIG, ('U5', '10'), (160.0, 153.5), (160.9, 152.6), ('C65', '1'))
    r.track(F, SIG, ('U5', '15'), ('C66', '1'))
    r.track(F, SIG, ('U5', '23'), ('C67', '1'))
    r.track(F, SIG, ('U5', '29'), (156.5, 160.7), (156.2, 161.1), ('C63', '1'))
    r.track(F, SIG, ('U5', '36'), (160.0, 160.5), (160.5, 161.0), ('C62', '1'))
    r.track(F, SIG, ('U6', '3'), ('C73', '1'))
    # 3V3 vias at the caps into the L3 3V3 islands; A <-> B link and the supervisor on L4
    for ref, pref in (('C50', (0, -1)), ('C51', (0, 1)), ('C52', (1, 0)), ('C57', (-1, 0)), ('C53', (0, 1)),
                      ('C54', (0, -1)), ('C55', (-1, 0)), ('C56', (0, -1)), ('C64', (0, -1)), ('C65', (0, -1)),
                      ('C66', (-1, 0)), ('C67', (0, -1)), ('C63', (-1, 0)), ('C62', (0, -1)), ('C70', (0, -1)),
                      ('R75', (-1, 0))):
        near(r, ref, pad_on(r, ref, '3V3')[1], pref)
    c73 = near(r, 'C73', '1', (0, -1))
    a, b = (137.4, 146.0), (149.2, 148.2)
    r.via(a, v33, *PV)
    r.via(b, v33, *PV)
    r.track(B, 0.5, a, (147.0, 146.0), b, net=v33)
    if c73:
        r.track(B, 0.3, c73, (c73[0], 146.0), net=v33)
    r.zone(v33, L3, poly_rect(116.5, 144.5, 138.0, 168.5), prio=2, name='L3_3V3_A')
    r.zone(v33, L3, poly_rect(148.5, 147.5, 167.0, 168.5), prio=2, name='L3_3V3_B')
    # GND pads of the hub parts, supervisor, crystals: a via each, away from the hub
    for ref, pref in (('C50', (-1, 0)), ('C51', (-1, 0)), ('C52', (0, 1)), ('C53', (1, 0)), ('C54', (1, 0)),
                      ('C55', (0, -1)), ('C56', (-1, 0)), ('C57', (0, 1)), ('C58', (0, 1)), ('C59', (-1, 0)),
                      ('C60', (-1, 0)), ('C61', (0, -1)), ('C62', (1, 0)), ('C63', (0, 1)), ('C64', (1, 0)),
                      ('C65', (0, -1)), ('C66', (0, -1)), ('C67', (-1, 0)), ('C68', (0, -1)), ('C69', (1, 0)),
                      ('C70', (-1, 0)), ('C71', (1, 0)), ('C72', (0, 1)), ('C73', (1, 0)), ('R41', (-1, 0)),
                      ('R42', (1, 0)), ('R43', (1, 0)), ('R44', (1, 0)), ('R45', (1, 0)), ('R46', (1, 0)),
                      ('R47', (1, 0)), ('R48', (1, 0)), ('R49', (1, 0)), ('R50', (1, 0)), ('R51', (1, 0)),
                      ('R52', (1, 0)), ('R53', (0, 1)), ('R54', (0, 1)), ('R55', (0, 1)), ('R62', (-1, 0)),
                      ('R66', (1, 0)), ('R67', (-1, 0)), ('R68', (-1, 0)), ('R69', (-1, 0)), ('R70', (0, 1)),
                      ('R76', (1, 0)), ('U6', (1, 0)), ('Y1', None), ('Y2', None), ('TP42', (0, 1))):
        for num in sorted({num for (rf, num) in r.pads if rf == ref and r.net(rf, num) == gnd}):
            near(r, ref, num, pref)


# ---------------------------------------------------------------- blocks
def route_power(r):
    route_pd(r)
    route_buck(r)
    route_3v3(r)
    route_status(r)
    for k in PORTS:
        route_port_power(r, k)
    route_host_power(r)
    route_hub_power(r)


def route_ports(r):
    """10 port clusters + the HOST receptacle's parts: tools/route_ports.py (handoffs in its PORT_HANDOFF)"""
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import route_ports as ports
    ports.route_ports(r)


def _module(name):
    import importlib
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    return importlib.import_module(name)


def route_hub_a(r):
    """Hub A (USB2517, U4): its fan-out, straps, crystal, reset, HOST pair, ports 1-6 pairs/EN/OCS: tools/route_hub_a.py"""
    if not os.environ.get('SKIP_HUB_A'):         # for an isolated scratch iteration of the other hub's module only
        _module('route_hub_a').route(r)


def route_hub_b(r):
    """Hub B (USB2514B, U5): fan-out, straps, crystal, hub A DN7 link, ports 7-10: tools/route_hub_b.py"""
    if not os.environ.get('SKIP_HUB_B'):
        _module('route_hub_b').route(r)


def build(r):
    route_power(r)
    planes(r)
    route_ports(r)
    route_hub_a(r)
    route_hub_b(r)
