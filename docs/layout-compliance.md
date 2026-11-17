# Layout compliance: each block checked against its reference

Each block is checked against `docs/layout-refs/<part>/`: the datasheet's layout section and figure first, then a vendor or EVM layout.

**Stage 1 covered placement; stage 2 (power routing, `tools/route_plan.py`) ticks the power rows below; stage 3 (port
clusters and the HOST receptacle, `tools/route_ports.py`) ticks the SY6863 OUT, TPD4E05U06 and receptacle rows.**
Stage 2 evidence is measured on the built board refilled in a scratch copy: DRC (0 clearance/short/hole errors), `power.py`, `planes.py`, `pour_check.py`, `islands.py` (kicad-board-review). Coordinates are board-relative unless marked absolute.
- Rows marked **ok (placement)** are satisfied by where the parts sit.
- Rows marked **open (routing)** are the rules the routing stage must meet, with the copper this placement reserved for them (see `docs/layout-plan.md` s5).

Distances are pin pad centre to the nearest pad of the part, on the same net, measured on the built board (board-relative mm).

**Renders:** `scratchpad/layout1/zoom_5v_buck.png`, `zoom_pd_3v3.png`, `zoom_hubA.png`, `zoom_hubB.png`, `zoom_port5.png`.

## LM5148 5 V buck (TI LM5148 datasheet s9.4.1, Fig 9-46..9-49; refs p54-58)

| # | Rule (from the reference) | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | Input HF caps at the high-side drain, GND vias at the caps; hot loop minimal, vertical through the GND plane on L2 | ok (placement) | C34/C35 0402 at (45.7/47.3, 19.5) on the Q30 drain pad; Cin C30-C33 row 3.5 mm right of the drain; Q31 source directly below | zoom_5v_buck: loop ~10 mm long over L2 at 0.21 mm ≈ 2 mm² |
| 2 | FETs side by side / stacked, SW copper short, no vias in SW | ok (placement) | Q30 (46.5, 24) source pins face Q31 (46.5, 31.8) drain pad; L30 pad 1 directly left | SW island spans ~x 41-49, y 26-30 |
| 3 | Inductor next to SW, output caps at the inductor/shunt output, toward the load | ok (placement) | L30 (37.8, 27.8) → R30 (28.6, 30) → C42/C43 + C36-C41 row (y 37) | flow right → left → down toward the board centre / L3 5V_BUS |
| 4 | Small-signal parts at their pins (VCC, VDDA, FB divider at FB, RT, EXTCOMP, CNFG) | ok (placement) | C44 VCC 1.8, C45 VDDA 1.6, R35 FB 1.6, C48 EXTCOMP 2.6, R31 RT 3.2, R32 CNFG 3.6, R33 3.4 | row at y 28.9 and column at x 59.6 |
| 5 | CBOOT cap between CBOOT and SW, short | ok (placement) | C46 at (52.9, 36.0), under the CBOOT/SW pins | |
| 6 | HO/SW routed as a pair, LO with PGND; gate traces ≥ 0.65 mm, short | ok (routing) | HO 0.65 mm on L1 at x 50.4 to the Q30 gate with SW 0.65 mm beside it at x 49.5 (U30 pin 14 to Q31 pin 5, branch to C46) | LO: via at U30 → L4 → via at the Q31 gate (48.6, 36.25), over the L3 GND_BUCK region (no other net under it) |
| 7 | Kelvin ISNS+/VOUT from the shunt, routed as a pair away from SW | ok, with a deviation | From the inner edges of the R30 pads; 0.2 mm pair on L4 at y 41.5 / 41.9, then x 58.8 / 59.2 to U30 | L3 keepout around the VOUT via (VOUT meets 5V_BUS only at R30:2). **Deviation:** the FB divider top (R34) is fed from the same Kelvin VOUT line (via at (56.55, 27.5), over L3 GND), not from a separate output-cap tap. pour_check: the pair crosses the L3 GND_BUCK edge at y 41.2 (0.15-0.2 mm over the island gap), DC sense only |
| 8 | Single-point AGND/PGND at the DAP; 0.3 mm thermal vias in the DAP | ok, with a deviation | PGND pin 10 and the GND pins into the EP on L1; C45 (VDDA) and R35 (FB divider) GND to AGND pin 7; 3 x 2 0.3 mm-drill vias in the EP | islands.py: the DAP island (U30 EP + pins 1/2/7/10/16/22-24, C45:2, R35:2) is one F.Cu piece joined to the rest of GND only through the 6 EP vias. **Deviation:** C48, R31/R32, C47 and R37 GND go to L2 through their own vias, not to pin 7 (no L1 room in the 0.5 mm-pitch fan-out) |
| 9 | No sensitive copper under SW on any layer | ok (routing) | L2 solid GND; L3 GND_BUCK region under L30, the SW node and U30; L4 GND pour | No vias in the SW copper (5V_SW has copper on L1 only: pour_check) |

## TPS54202 3.3 V (TI SLVSD26C s7.4, Fig 7-16; refs p20-21)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | GND/SW/VIN pins on one side; input bypass cap at VIN/GND | ok, with a deviation | C14 100 nF 1.55 mm from VIN; C13 10 uF 4.75 mm | **Deviation:** Fig 7-16 puts the cap's GND end on a top GND pour and moves SW to an inner layer with vias. Here SW stays on L1 to L1 (no SW vias), and C14's GND pad returns through L2 vias at the cap and at pin 1 (~4 mm). The rail is low current. |
| 2 | SW to inductor short | ok (placement) | L1 (30.6, 10) SW pad 4.5 mm from pin 2 | zoom_pd_3v3 |
| 3 | Output caps at the inductor output, separate VOUT path to the FB divider | ok (placement) | C16-C18 at the L1 3V3 pad; R14/R15/C19 at FB on the far side (1.5 mm) | |
| 4 | BOOT cap at BOOT/SW | ok (placement) | C15 1.5 mm | |
| 5 | FB away from SW; Kelvin GND for the divider | ok (routing) | Divider at FB; 3V3 sensed on L4 from the output caps (via (37.9, 4.9) to (40.1, 17.9)); R15 GND to L2 through its own via | SW on L1 (0.8 mm) to L1, nothing under it but L2 GND |

## TPS25730 PD sink (TI TPS25730 datasheet layout section, Table 9-1; refs p42, p48-52)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | CC caps on the same side, no via between pin and cap (via after the cap) | ok (placement) | C7 CC1 1.27 mm, C6 CC2 2.23 mm, D3/D4 at J1 | |
| 2 | LDO_3V3 / LDO_1V5 / VIN_3V3 caps at their pins | ok (placement) | C9 1.71, C10 1.95, C11 1.87 | |
| 3 | PPHV output cap close | ok (placement) | C8 2.07 mm from PPHV | |
| 4 | VBUS input cap / TVS near the connector | ok (placement) | D1 at J1 VBUS; C1/C4/C5 between J1 and U1 | |
| 5 | VBUS/VBUS_IN and PPHV pours, ≥ 6 / ≥ 15 vias (8 / 16 mil), Table 9-1 widths | ok (routing) | PD_VBUS: L1 pours at both J1 VBUS groups and at U1 VBUS_IN, 36 vias (0.6/0.3) to the L3 PD_VBUS island; PPHV → VIN: L1 pour over C8 and the Cin row, 20 vias to the L3 VIN island (8 at the pour + 12 in the Q30 drain pad); CC 0.2 mm, CC caps via-after-cap | power.py VIN at 5 A (TPS25730 limit): 11.4 mV drop, max via 0.36 A; a 5.5 A/mm corner peak at the PPHV pour's inside corner (52.6, 21.0), set by the C8 / C8-GND-via placement |
| 6 | DRAIN pads tied together, isolated, not GND | ok (routing) | pins 15/30 = PD_DRAIN, tied to each other on L1 only | DRC: no unconnected PD_DRAIN item |

## USB2517 hub A (Microchip DS; pin diagram p7, crystal p12/15, package p52-53)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | 0.1 uF at every VDD33/VDDA pin | ok (placement) | VDDA5 C50 2.8, VDDA10 C51 3.5, VDD33CR C52 3.3, VDD33 C53 2.4, VDDA52 C54 4.4, VDDA57 C55 4.4, VDD33PLL C56 2.4 | 0.5 mm pins sit between USB pairs. Each cap is at the first point where the pairs split, so the tighter spots have a reason: the pads cannot sit closer without crossing a pair. |
| 2 | VDD18 / VDD18PLL caps at the pins | ok (placement) | C58 3.4, C59 4.6 | |
| 3 | Crystal and load caps tight to XTAL1/XTAL2 | ok (placement) | Y1 4.5 / 5.4 mm; C60/C61 at the crystal pads | The UP pair and the PLL group share that corner |
| 4 | RBIAS resistor at its pin | ok (placement) | R41 3.3 mm | |
| 5 | ePad soldered with multiple GND vias | ok (routing) | 4 x 4 vias, 0.3 mm drill, in the ePad | Paste over the vias: see the decision below |
| 6 | 90 ohm pairs, no stubs, solid reference | open (routing) | L1 over L2, w 0.26 / s 0.15 (estimate) | layout-plan s3 |

## USB2514B hub B (Microchip DS; pin diagram p4, p9/14, package p44-47)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | 0.1 uF at every VDD33/VDDA pin | ok (placement) | VDDA5 C64 2.2, VDDA10 C65 2.9, VDD33-15 C66 2.7, VDD33-23 C67 1.7, VDDA29 C63 1.4, VDDA36 C62 3.5 | |
| 2 | CRFILT / PLLFILT caps at the pins | ok (placement) | C68 2.8, C69 5.6 | C69 is in the x 63.8 column, behind the crystal traces |
| 3 | Crystal tight to XTALIN/XTALOUT | ok (placement) | Y2 4.4 / 5.1 mm; C71/C72 at its pads | |
| 4 | RBIAS at its pin | ok (placement) | R66 4.5 mm | |
| 5 | ePad vias; 90 ohm pairs | ePad ok (routing); pairs open | 3 x 3 vias, 0.3 mm drill, in the ePad | Pairs: USB stage |

## SY6863 port switch (Silergy DS Fig 4), port 5 measured

The other ports are the same frame, rotated.

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | CIN at the IN pin | ok (placement) | C501 2.1 mm | |
| 2 | COUT near the connector | ok (placement) | C503 100 nF 5.1, C502 22 uF 5.7 mm from the J501 VBUS pad; TVS D501 1.35 mm | The LED sits at the edge between them by plan |
| 3 | RSET and EN pull-down at their pins | ok (placement) | R501 1.2, R60 1.35 | |
| 4 | IN on the 5V_BUS pour, OUT on a wide VBUS trace | ok (routing), with a deviation | IN: L1 copper CIN → IN plus 3 vias (0.6/0.3) to the L3 5V_BUS plane. OUT (stage 3, `tools/route_ports.py`): 0.9 mm L1 band OUT → TVS → A4B9 over the switch's edge-side pins, 3 vias (0.6/0.3, 1.25 mm pitch so the L2/L3 antipads do not merge) to a 1.0 mm L4 trunk in parallel, then a 0.6 mm L4 tie to two vias at the B4A9 / Rp side; C_OUT / LED column 0.5 mm on L1 | power.py, 3 A into the receptacle split 1.5 / 1.5 A between A4B9 and B4A9 (ports 1, 5, 9): worst drop 25.8 mV (to B4A9), max via 0.93 A. **Deviation:** the datasheet's layout guide (p11, item 1) asks for 2 oz VBUS copper; the stackup (JLC04161H-7628, user-frozen) has 1 oz outer layers, so the width (0.9 mm L1 + 1.0 mm L4 in parallel) carries it instead |
| 5 | COUT at the connector and to the GND plane; CIN to GND at the IC | ok (routing) | C503/C502 on the VBUS column 2-3 mm from A4B9, GND to the shell legs (plated, every GND plane); CIN GND via at the pad | |
| 6 | RSET at ISET, EN pull-down at EN | ok (routing) | ISET pin 5 → R501 straight (0.25 mm, 1.2 mm); EN pin 4 → R60 (0.2 mm) | EN and OCS_N end on handoff vias to L4 (see the receptacle section) |

## TPD4E05U06 ESD (TI DS, layout section)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | At the connector, protected lines straight through (TI s7.4.1) | ok (routing) | U502 DP/DM pads 2.0-2.1 mm from J501; A6/A7 → pins 1/2 → over the pads to pins 10/9 on one axis each (0.2 mm through the 0.5 mm pitch), CC1 pins 4 → 7, CC2 5 → 6 the same way | Every port and the HOST (U7) use the same code (`route_data` / `route_cc`) |
| 2 | Straight-through over the NC pins | ok (routing) | NC pins 6/7/9/10 carry CC2/CC1/DM/DP in the schematic (commit 09fcf1f); the tracks run over them | DRC: no short, no unconnected item on any port's DP/DM/CC net between the receptacle and the ESD |
| 3 | Short, wide GND to L2 | ok (routing) | Pins 3-8 tied under the body (0.3 mm), one via beyond pin 8 | The via (kept where stage 2 put it) sits 0.24 mm from the 0.26 mm DM track |
| 4 | No sharp corners between the TVS and the connector; unprotected traces away from the protected ones | ok, with a deviation | Only DP/DM/CC2 (and VBUS, which has its own TVS) run between U502 and J501 | **Deviation:** the 0.75 mm D+/D- jog from A6/A7 onto pins 1/2 uses two 43° chamfered bends, not radiused arcs (router.py writes straight segments) |

## TYPE-C-31-M-12 receptacles (HRO drawing; 10 ports + HOST), `tools/route_ports.py`

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | Both D+ (A6/B6) and both D- (A7/B7) pads tied, short stubs | ok (routing) | A6/A7 are the through path to the ESD on L1; B7 and A7 get vias 0.29 mm past the pad ends (row 1), A6 and B6 0.6 mm further (row 2), each pair tied by a 1.0 mm L4 track under the receptacle body (layout-plan s2: the L4 A/B tie) | Stub beyond the pad ends: DM 0.29 + 1.0 + 0.29 mm, DP 0.89 + 1.0 + 0.89 mm on copper, plus two via barrels (~1.6 mm each). Pair length match receptacle → handoff: 0.04 mm |
| 2 | CC1 crosses the D+/D- pair | ok (routing) | A5 → via under the body → L4 (below the tie, up between B6's and CC2's vias) → via at ESD pin 7 → Rp. HOST: the 3V3 trunk (route_3v3) runs on L4 under J2, so HOST CC1 goes straight in on L4 at x(A5) and comes up beside ESD pin 7; HOST CC2 stays on L1 | CC2 on the ports hops on L4 under the B4A9 link to a via below its Rp |
| 3 | Both VBUS pad groups tied | ok (routing) | Ports: L4 tie (0.6 mm) A4B9/TVS side → B4A9 side, over the pair's hub side (L4 under L2). HOST (detection only): 0.15 mm link past the locating peg to a via under the body, L4 around the start of the 3V3 trunk | power.py above |
| 4 | Vias under the receptacle | ok | 5 signal vias (0.45/0.2) per receptacle under the body, between the pad ends and the locating pegs; the board tents vias on both sides | The shell sits on solder mask over them |
| 5 | Pair handoff to the USB stage | ok (routing) | Coupled pair 0.26 / 0.15 mm from just past ESD pins 10/9 (DM steps 0.09 mm in to the 0.41 mm pitch), ends 1.73 mm past the hub-side pins; `PORT_HANDOFF[k]` in `tools/route_ports.py` (and printed in the router log) | Handoffs, board-relative: port 1 DP (11.08, 20.00); port 5 DP (32.70, 73.92); port 9 DP (73.92, 43.50); HOST DP (21.00, 11.08); DM 0.41 mm beside each. EN / OCS_N: via at the switch (EN 1.13 mm above pin 4, OCS_N beside the TVS); HUBA_VBUS_DET: via 0.98 mm beyond TP41 |

## Stage 2 decisions and deviations

| Item | Status | Detail |
|---|---|---|
| Paste over thermal vias | **decision needed** | board_lint: 54 PASTE ON HOLE (U4 16, U5 9, U1 9, U30 6, Q30 12, D1 2 vias, 0.3 mm drill, in exposed pads with 100 % paste). Either order the vias filled and capped (JLC via-in-pad, `--vias-filled`) or split the paste into windows with `paste_clear.py` |
| Small-signal GND | deviation | The LM5148 small-signal GND (except C45/R35) and all TPS25730 strap GNDs go to L2 through a via at each pad |
| Placement moves for routing | done | `tools/place_gen.py` comments: C1/C4-C7, R7/R8, R1-R6/R12, R10/R11, TP3-TP5, R31/R32, R36/R37, TP31 (lane order, via room, silk clearance) |
| 5V_BUS L1 at the shunt | risk | power.py: 4.6 A/mm over ~9 mm of the L1 output copper from R30:2 to the via strip (outer threshold 3.2); set by the output-cap placement. Total 5V_BUS copper loss 0.43 W |
