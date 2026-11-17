# Layout compliance: each block checked against its reference

Each block is checked against `docs/layout-refs/<part>/`: the datasheet's layout section and figure first, then a vendor or EVM layout.

**Stage 1 covers placement only.**
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
| 6 | HO/SW routed as a pair, LO with PGND; gate traces ≥ 0.65 mm, short | open (routing) | U30 HO at the left side, ~8 mm to the Q30/Q31 gates | |
| 7 | Kelvin ISNS+/VOUT from the shunt, routed as a pair away from SW | open (routing) | R30 at (28.6, 30), ~26 mm from U30: the longest run in the block, a risk to watch | layout-plan s6 |
| 8 | Single-point AGND/PGND at the DAP; 0.3 mm thermal vias in the DAP | open (routing) | 3 x 2 vias reserved | |
| 9 | No sensitive copper under SW on any layer | open (routing) | L3/L4 keepout under x 41-49, y 26-30 | layout-plan s5 |

## TPS54202 3.3 V (TI SLVSD26C s7.4, Fig 7-16; refs p20-21)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | GND/SW/VIN pins on one side; input bypass cap at VIN/GND | ok, with a deviation | C14 100 nF 1.55 mm from VIN; C13 10 uF 4.75 mm | **Deviation:** Fig 7-16 puts the cap's GND end on a top GND pour and moves SW to an inner layer with vias. Here SW stays on L1 to L1 (no SW vias), and C14's GND pad returns through L2 vias at the cap and at pin 1 (~4 mm). The rail is low current. |
| 2 | SW to inductor short | ok (placement) | L1 (30.6, 10) SW pad 4.5 mm from pin 2 | zoom_pd_3v3 |
| 3 | Output caps at the inductor output, separate VOUT path to the FB divider | ok (placement) | C16-C18 at the L1 3V3 pad; R14/R15/C19 at FB on the far side (1.5 mm) | |
| 4 | BOOT cap at BOOT/SW | ok (placement) | C15 1.5 mm | |
| 5 | FB away from SW; Kelvin GND for the divider | open (routing) | | |

## TPS25730 PD sink (TI TPS25730 datasheet layout section, Table 9-1; refs p42, p48-52)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | CC caps on the same side, no via between pin and cap (via after the cap) | ok (placement) | C7 CC1 1.27 mm, C6 CC2 2.23 mm, D3/D4 at J1 | |
| 2 | LDO_3V3 / LDO_1V5 / VIN_3V3 caps at their pins | ok (placement) | C9 1.71, C10 1.95, C11 1.87 | |
| 3 | PPHV output cap close | ok (placement) | C8 2.07 mm from PPHV | |
| 4 | VBUS input cap / TVS near the connector | ok (placement) | D1 at J1 VBUS; C1/C4/C5 between J1 and U1 | |
| 5 | VBUS/VBUS_IN and PPHV pours, ≥ 6 / ≥ 15 vias (8 / 16 mil), Table 9-1 widths | open (routing) | L1 + L3 PD_VBUS and VIN islands reserved | layout-plan s5 |
| 6 | DRAIN pads tied together, isolated, not GND | open (routing) | pins 15/30 = PD_DRAIN | |

## USB2517 hub A (Microchip DS; pin diagram p7, crystal p12/15, package p52-53)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | 0.1 uF at every VDD33/VDDA pin | ok (placement) | VDDA5 C50 2.8, VDDA10 C51 3.5, VDD33CR C52 3.3, VDD33 C53 2.4, VDDA52 C54 4.4, VDDA57 C55 4.4, VDD33PLL C56 2.4 | 0.5 mm pins sit between USB pairs. Each cap is at the first point where the pairs split, so the tighter spots have a reason: the pads cannot sit closer without crossing a pair. |
| 2 | VDD18 / VDD18PLL caps at the pins | ok (placement) | C58 3.4, C59 4.6 | |
| 3 | Crystal and load caps tight to XTAL1/XTAL2 | ok (placement) | Y1 4.5 / 5.4 mm; C60/C61 at the crystal pads | The UP pair and the PLL group share that corner |
| 4 | RBIAS resistor at its pin | ok (placement) | R41 3.3 mm | |
| 5 | ePad soldered with multiple GND vias | open (routing) | 4 x 4 x 0.3 mm | |
| 6 | 90 ohm pairs, no stubs, solid reference | open (routing) | L1 over L2, w 0.26 / s 0.15 (estimate) | layout-plan s3 |

## USB2514B hub B (Microchip DS; pin diagram p4, p9/14, package p44-47)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | 0.1 uF at every VDD33/VDDA pin | ok (placement) | VDDA5 C64 2.2, VDDA10 C65 2.9, VDD33-15 C66 2.7, VDD33-23 C67 1.7, VDDA29 C63 1.4, VDDA36 C62 3.5 | |
| 2 | CRFILT / PLLFILT caps at the pins | ok (placement) | C68 2.8, C69 5.6 | C69 is in the x 63.8 column, behind the crystal traces |
| 3 | Crystal tight to XTALIN/XTALOUT | ok (placement) | Y2 4.4 / 5.1 mm; C71/C72 at its pads | |
| 4 | RBIAS at its pin | ok (placement) | R66 4.5 mm | |
| 5 | ePad vias; 90 ohm pairs | open (routing) | 3 x 3 vias | |

## SY6863 port switch (Silergy DS Fig 4), port 5 measured

The other ports are the same frame, rotated.

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | CIN at the IN pin | ok (placement) | C501 2.1 mm | |
| 2 | COUT near the connector | ok (placement) | C503 100 nF 5.1, C502 22 uF 5.7 mm from the J501 VBUS pad; TVS D501 1.35 mm | The LED sits at the edge between them by plan |
| 3 | RSET and EN pull-down at their pins | ok (placement) | R501 1.2, R60 1.35 | |
| 4 | IN on the 5V_BUS pour, OUT on a wide VBUS trace | open (routing) | ≥ 3 vias to L3 at each IN | |

## TPD4E05U06 ESD (TI DS, layout section)

| # | Rule | Status | Satisfied by | Evidence |
|---|---|---|---|---|
| 1 | At the connector, protected lines straight through | ok (placement) | U502 DP/DM pads 2.0-2.1 mm from J501 | zoom_port5 |
| 2 | Straight-through over the NC pins | **decision needed** | NC pads 6/7/9/10 are `unconnected-` nets in the netlist → DRC short if crossed | layout-plan s6 |
| 3 | Short, wide GND to L2 | open (routing) | pins 3/8 | |
