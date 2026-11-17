# Layout plan (Stage 0) and placement record (Stage 1)

Board: 85 x 85 mm, origin (100,100), y down; all coordinates below are mm from the outline's top-left.
Placement source: `tools/place.json` only (generated, then `tools/build.sh`). No copper is routed yet.

## 1. Stackup

JLC04161H-7628, 1.6 mm, ENIG. Outer 1 oz (35 um), inner 0.5 oz (17 um).
L1-L2 and L3-L4 prepreg 7628, 0.2104 mm, Er 4.4 (JLC table value). Core between L2 and L3 ~1.065 mm.

## 2. Layer use

| Layer | Use |
|---|---|
| L1 | All parts. Every USB D+/D- pair (L1 only, over L2). Power-stage copper: VIN, SW, 5V_BUS near the buck, PD_VBUS, each port VBUS. Short local signals. |
| L2 | Solid GND. No traces, no splits. Via antipads only. It is the reference plane for every USB pair and the return path for the LM5148's vertical hot loop. |
| L3 | 5V_BUS pour. It covers the perimeter band under every SY6863 IN pin and joins the buck output-cap row. Islands: PD_VBUS (J1 -> U1 VBUS_IN), VIN (U1 PPHV -> buck Cin row, TPS54202 VIN), 3V3 under both hubs (fed from the TPS54202 output), and GND fill elsewhere. No L3 copper under the LM5148 switch node except GND. |
| L4 | Slow signals: 20 PRTPWR/OCS_N lines, HUB_RESET_N, the VBUS_DET lines, the PD I2C/status lines to the test pads, LED/status lines, the 3V3 trunk (TPS54202 -> hub 3V3 island), each receptacle's CC crossing and its short D+/D- A/B-row tie, and (stage 3) each port's VBUS: a 1.0 mm trunk from the switch OUT vias beside the receptacle (in parallel with the L1 band) and a 0.6 mm tie to the B4A9 pad group, crossing under the pair's hub side at local y -7.5. Hub-stage L4 lanes to a port's EN / OCS_N vias arrive from inside the board and must not cross that trunk/tie (the vias sit on the inner side of it). |

**Why L4 is not a USB layer.** L4 is referenced to L3, and L3 is a split power layer (5V_BUS, VIN and 3V3 islands). A pair routed there would cross island gaps, and its return current would have to jump through decoupling capacitors.

So L4 takes only edge-insensitive signals. They are allowed to cross under the L1 pairs because the solid L2 shields them. The one exception is the short (<2 mm) D+/D- A/B-row tie under each receptacle. It is the normal USB-C stub, it sits over the 5V_BUS pour, and it is length-matched within the pair.

## 3. USB 2.0 pair geometry (L1 over L2): 0.26 / 0.15 mm, ~88 ohm per JLC's calculator

Model: edge-coupled microstrip, h = 0.2104 mm, Er 4.4, t = 0.035 mm, optional 15 um solder mask (Er 3.8).

I solved it with a 2-D finite-difference field solver (`scratchpad/zsolve/fd.py`). As a sanity check, the same solver gives a single 0.36 mm trace 52.2 ohm, against 51.1 ohm from the Hammerstad-Jensen formula.

| w / s (mm) | Zdiff, bare | Zdiff, 15 um mask |
|---|---|---|
| 0.20 / 0.15 | 106 | ~101 |
| 0.25 / 0.15 | 97.0 | 91.4 |
| **0.26 / 0.15** | **95.5** | **90.0** |
| 0.28 / 0.15 | 92.5 | 87.4 |
| 0.30 / 0.20 | 94.9 | 90.4 |

**Proposal: w = 0.26 mm, s = 0.15 mm, about 90 ohm.**
- Neck down to 0.2 mm for at most 1 mm at the 0.5 mm-pitch hub pins.
- Keep ≥ 0.6 mm (≈ 3h) between pairs and ≥ 0.45 mm to other copper.
- Keep the length mismatch within a pair ≤ 0.5 mm.
- No pair vias, except the A/B tie described in s2.

**Checked with JLC's impedance calculator (jlcpcb.com/pcb-impedance-calculator, 2026-11-17).** Inputs: Rigid,
4 layers, 1.6 mm, inner 0.5 oz, outer 1 oz, "Differential Pair (Non coplanar)" on L1 with L2 as reference, spacing
0.15 mm, stackup tab JLC04161H-7628 (Standard). JLC's trace width for each target:

| Target Zdiff | JLC width at s 0.15 mm |
|---|---|
| 90 ohm | 0.2474 mm |
| 88 ohm | 0.2619 mm |
| 87 ohm | 0.2690 mm |

So JLC puts our 0.26 / 0.15 mm at **about 88 ohm**, 2 ohm under target and 2 ohm under the field-solver estimate above.
That is inside USB 2.0's 90 ohm +-15 % (76.5-103.5 ohm), with JLC's +-10 % fabrication tolerance still inside it
(79-97 ohm). **Kept at 0.26 / 0.15 mm**: the ports were already routed at that width, and the hubs were being routed
at it. A board ordered with impedance control could move to 0.25 mm. That change is the two numbers in
`tools/build.sh` plus `USB_W` / `USB_GAP` in `tools/route_ports.py` and the hub modules.

The USB net class is set to this geometry in `tools/build.sh` (stage 3): track 0.26 mm (board_setup) and diff pair 0.26 / 0.15 mm (`tools/netclass_dp.py`, since board_setup has no diff-pair keys).

## 4. Floorplan (Stage 1, as placed)

| Block | Where | Why |
|---|---|---|
| HOST J2 + ESD U7, Rd, VBUS_DET divider, TP41 | back edge, x = 20 | User plan. The UP pair drops straight down the x 14-20 corridor, which is free between the port 1/2 clusters and the buck output caps, to hub A at (27, 52.5). |
| PWR IN J1 (GCT USB4105) | back edge, x = 62, flush | User plan. Origin 4.973 mm inside the edge = the drawing's 2.60 mm in front of the front stakes. |
| TPS25730 U1 | (54, 14.2) | Between J1 and the buck. VBUS_IN/VBUS face J1, PPHV faces down toward the buck input, CC pins face J1 (C7/C6 at 1.3 / 2.2 mm). Straps are in a column on the left; test pads TP1, TP3-TP8 are in a row at y = 3 (TP8 = GND). |
| LM5148 buck | Cin C30-C33 row (y 21-25, x 50-63) and HF caps C34/C35 at the Q30 drain; FET column Q30/Q31 at x 46.5; L30 (37.8, 27.8); shunt R30 (28.6, 30); output caps C36-C41 row at y 37 and C42/C43 toward the centre; controller U30 (55, 32.6) beside the FETs | Back-centre, next to PWR IN. The input comes from U1 PPHV straight down into the Cin row. The power flow runs right -> left toward the board centre. The output-cap row feeds the L3 5V_BUS pour. The ~10 mm L30 is under the ~20 mm lid. |
| TPS54202 U2 + L1 | (36, 14.5), between power-in and the hubs | VIN taps the U1 PPHV/VIN island. The 3V3 output caps are at L1's 3V3 pad. The 3V3 trunk runs on L4 to the hub islands. TP2 (3V3) is beside it. |
| Status LEDs D5/D6 | back edge, x 37-40 | Requirements s5 ("PD OK / low power near the back"). |
| Hub A U4 (USB2517) | (28, 57), rot 270 | DN1-5 face the left/front-left ports. UP, DN7 and DN6 leave the top. The crystal and PLL group sit in the top-left corner. Straps are in two columns on the right. VDDA caps sit where the DN pairs split. |
| Hub B U5 (USB2514B) | (58, 57), rot 90 | DN1-4 face the right edge, in board order (DN1 at the bottom -> port 7 ... DN4 at the top -> port 10). UP (from hub A DN7) and the crystal are on the bottom side. |
| Supervisor U6 + TP40/TP42 | (45, 57), between the hubs | HUB_RESET_N reaches both hubs on L4. TP42 = GND beside TP40. |
| Ports 1-10 | left y 21/42.5/64; front x 16/33.7/51.3/69; right y 64/42.5/21 | User plan. Centres are 16-21 mm from the corners (≥ 13 mm), side pitch 21.5 mm, front pitch 17.7 mm. Shells overhang ~1.0 mm per the HRO drawing (origin 4.084 mm inside). Each cluster sits clockwise of its receptacle: ESD right behind the signal pins; Rp and TVS beside it; LED at the edge; 22 uF/100 nF VBUS caps; SY6863 (OUT toward the edge) with its 10 uF IN cap, RSET and EN pull-down inward. |

Port numbering follows the agreed plan (left 1-3, front 4-7, right 8-10). **requirements.md s5 still says "Front 1-4, Left 5-7"; it should be updated.**

## 5. Reservations (keep these clear when routing)

- **LM5148 hot loop.** C34/C35 (0402) sit at the Q30 drain with GND vias; the Q31 source pads get a via row to L2. The loop is the vertical one in TI Fig 9-47 (L1 down to L2 at 0.21 mm), about 10 mm long and about 2 mm² in area. No other L1 copper between the Q30 drain/C34/C35 and the Q31 source vias.
- **Switch node.** The 5V_SW copper (Q30 source, Q31 drain, L30 pad 1) stays on L1 only, short, with no vias. L3/L4 under it: no signals, GND/blank only. The FB, ISNS+ and VOUT traces and the hub pairs keep ≥ 3 mm away.
- **Thermal vias.**
  - LM5148 DAP: 3 x 2 vias of 0.3 mm to L2.
  - Q30 drain pad: ≥ 8 vias to the L3 VIN island. Q31 source: ≥ 6 vias to L2.
  - USB2517 ePad: 4 x 4 vias of 0.3 mm. USB2514B ePad: 3 x 3.
  - TPS25730 GND pad: 3 x 3. Its DRAIN pads 15/30 are a floating copper island, not GND.
- **TPS25730 pours.** VBUS/VBUS_IN: ≥ 6 vias of 8 mil to the L3 PD_VBUS island. PPHV: ≥ 15 vias of 16 mil to the L3 VIN island (Table 9-1 widths).
- **Crystals Y1/Y2.**
  - On L1, only the XTAL traces and the load caps C60/C61 and C71/C72 within 1 mm of the crystal.
  - On L4, nothing under the crystal or its traces.
  - L3 under them stays the quiet 3V3 island.
- **5V_BUS.** The L3 pour runs from the output-cap row (y 35-39) out to the perimeter band and reaches every SY6863 IN pin and its 10 uF cap with ≥ 3 vias each. Each switch is limited to 3.8 A, and the total is 17 A, so the DC drop must be checked with the solver before release.
- **VIN path.** J1 VBUS -> D1 TVS -> L1+L3 PD_VBUS island -> U1 VBUS_IN; U1 PPHV -> L1+L3 VIN island -> C8 -> C34/C35 + Cin row -> Q30 drain. C12 and the TPS54202 tap off the same island.
- **Lanes.**
  - UP pair: corridor x 14-20 from J2 down to y ~42, then over to x 27.
  - DN1/DN2: up the left at x 14-19 (DN1 inside DN2, both right of the port clusters).
  - DN3-DN5 go down from hub A's left side. DN5 turns right under hub A at y ~67 to port 5.
  - DN6/DN7 go up out of hub A's top and right over the strap columns at y 49-50.5, then down at x 38.8-42.5. DN7 runs right at y ~65 into hub B's UP pins (57, 60). DN6 runs right at y ~69 to port 6.
  - Hub B DN1-4 go right. DN3 and DN4 go up the x 66-71.5 corridor (kept clear of the buck), DN4 on the inside.
  - The 20 PRTPWR/OCS_N lines leave both hubs through via rows to L4 and fan out radially to each switch's EN (pull-down R) and OCB pins.

## 6. Escape check

| Part | Package / pads | Result |
|---|---|---|
| USB2517 U4 | QFN-64 9 x 9, 0.5 mm pitch, pads 0.8 x 0.25 (0.25 gap: no trace between pads) | All pins escape outward on L1. **Left:** 5 pairs; VDDA 5/10 caps in the DN2/DN3 and DN4/DN5 splits; GND 13 to the ePad; strap 15 runs down beside the row to R55. **Bottom:** 9 PRTPWR/OCS lines to two staggered 0.45/0.2 via rows at y 62.4-63.6, split around the VDD33CR/VDD18 cap traces (pins 24/25). **Right:** straps on L1 to the columns at x 35/37.3; RESET, VBUS_DET, PRTPWR6, OCS5/6 to vias in the 1.1 mm channel between the pad ends and the column. **Top:** UP/DN7/DN6 on L1, PLL caps and crystal to the left, straps 49-51 under the DN6/DN7 run. **Feasible.** |
| USB2514B U5 | QFN-36 6 x 6, 0.5 mm pitch, pads 0.28 x 1.1 | Right: 4 pairs, VDDA C64 in the DN2/DN3 split. Top: PRTPWR1-3/OCS1-2 to vias in the 1.5 mm channel under the cap row. Left: OCS3/PRTPWR4/OCS4 to vias in the 1.0 mm channel; straps to the x 52.9 column; RESET and VBUS_DET to L4. Bottom: UP from below, crystal, PLLFILT/RBIAS/VDDA to the x 63.8 column. **Feasible.** |
| TPS25730 U1 | WQFN, 0.4 mm pitch, pads 0.2 x 0.6 | CC1/CC2 go to C7/C6 on L1 (no via between pin and cap), then a via after the cap to L4 under the PD_VBUS pour to J1. VBUS/VBUS_IN/PPHV go to pours with via counts as in s5. The left-side straps/ADC/I2C go to the x 49-51 column and TPs. **Feasible.** |
| LM5148 U30 | VQFN-24, 0.5 mm pitch | The small-signal parts sit at their pins: C44 VCC 1.8 mm, C45 VDDA 1.6, R35 FB 1.6, C48 EXTCOMP 2.6, R31 RT 3.2, R32 CNFG 3.6. HO/SW and LO run to Q30/Q31 gates (~8 mm) as ≥ 0.65 mm traces, HO paired with SW. CBOOT goes to C46 below. **Feasible.** Risk: the ISNS+/VOUT Kelvin pair to R30 is ~26 mm. Route it as a tight pair away from SW (L1, or L4 under L3 GND fill). |
| TPD4E05U06 (U_k02, U7) | USON-10, 0.5 mm pitch; DP, DM, CC1, CC2 on the connector-side row, NC 6/7/9/10 behind | Connector side: direct. Hub side: the datasheet's straight-through routing crosses the NC pads. **Those pads carry their own `unconnected-` nets in the netlist, so DRC will flag the crossing as a short.** Decision for the user: (a) tie pins 10/9/7/6 to DP/DM/CC1/CC2 in the schematic (TI's intended use, pin-decisions already says "used for straight-through routing"), or (b) enter pins 1/2 around the package end. Recommend (a). |

**Lane order per hub (no pair crosses another pair on L1).**
- Hub A, counter-clockwise from the top: DN6 (-> port 6), DN7 (-> hub B), UP (-> J2), DN1, DN2, DN3, DN4, DN5. This matches the board's own order: J2, then ports 1-5 on the left/front, then hub B and port 6.
- Hub B, from the bottom up its right side: DN1 (port 7), DN2 (port 8), DN3 (port 9), DN4 (port 10). UP comes in from below.
- What does have to cross: each receptacle's CC line over the D+/D- pair (the ESD has both CC pins on one side), the per-port VBUS pad tie (u ±2.4) and the A/B-row D+/D- tie. All of these go on L4 under the receptacle.

None of the frozen decisions is infeasible. The TPD4E05U06 NC-pin netlist issue is the only open decision.
