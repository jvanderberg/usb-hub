# Port circuits (downstream x10, HOST, PD input connector)

Status: draft (2026-11-16). Hub pins: `docs/hub-design.md`. PD input chip: `docs/power-design-pd-3v3.md`.

## Downstream port (one sheet, used 10 times)

Interface of the sheet: `5V_BUS` and `3V3`, `GND` (rails, power symbols); per instance hierarchical labels `DP`, `DM`
(to the hub port), `EN` (from the hub's PRTPWRn), `OCS_N` (to the hub's OCSn_N).

| Part | Value / MPN | LCSC | Connection | Source |
|---|---|---|---|---|
| J | HRO TYPE-C-31-M-12 (16-pin, 4 TH shell legs) | C165948 | A6/B6 -> DP, A7/B7 -> DM (both pairs tied at the receptacle); A4/A9/B4/B9 VBUS -> VBUS (local net); A1/A12/B1/B12 GND; shell -> GND; SBU not connected | requirements s3 |
| U switch | Silergy SY6863B3ABC | C2687365 | IN = 5V_BUS, OUT = VBUS, EN = EN, OCB = OCS_N, ISET -> RSET -> GND | SY6863 p2 pinout |
| RSET | 1.87 k 1 % 0402 | (Basic, UNI-ROYAL 0402WGF1871TCE) | ISET to GND | ILIM = 7100 / RSET (p2): 3.80 A; datasheet-tested point 1.878 k = 3.47 / 3.78 / 4.08 A (p4) |
| C_IN | 10 uF 0805 X5R 25 V | C15850 (Basic) | IN to GND at the pin | Fig 1 note: 1 uF can spike, add 10 uF (p2) |
| C_OUT | 22 uF 0805 X5R 25 V + 100 nF 0402 | C45783 / C1525 | VBUS to GND near the receptacle | USB-PD cSrcBulk >= 10 uF; datasheet characterised with 10 uF |
| Rp x2 | 10.0 k 1 % 0402 | C25744 | CC1 -> VBUS, CC2 -> VBUS (Type-C "3.0 A" Rp = 10 k to 4.75-5.5 V) | Type-C spec Rp table |
| ESD | TI TPD4E05U06DQAR | C138714 | DP, DM, CC1, CC2 at the receptacle | requirements s8 |
| VBUS TVS | SMF6.0A, SOD-123FL | C123790 | VBUS to GND at the receptacle | backfeed up to ~5.5 V must not conduct (6.0 V standoff) |
| LED | green 0603 + 1.5 k 0402 | KT-0603G C12624 / 0402WGF1501TCE | VBUS -> R -> LED -> GND: lit when the port has power | requirements s5 |

Behaviour:
- EN low (hub not running, reset, port off by uhubctl): the hub's 10 k pull-down on PRTPWR holds EN low; the switch is
  off, OUT is discharged through 115 ohm (p4), Rp goes away with VBUS, so the attached device sees a detach.
- Backfeed (A-to-C charger / self-powered device on VBUS): the SY6863 blocks reverse current on or off (60 mV, p10);
  OVP at 5.6 V on OUT turns the switch off and asserts OCB (hub reports over-current on that port).
- Over-current: limit 3.47-4.08 A; OCB low after 15 ms deglitch (p4); hub OCS input has an internal pull-up to 3V3
  (hub-design.md), no external pull-up.
- Open question (bench): what OCB does while IN (5V_BUS) is off (5 V-only brick): if it pulls low, the hubs report
  over-current on every port in that state. Harmless (ports have no power then), but noisy in the host log.

## HOST (upstream) port

| Part | Value / MPN | LCSC | Connection |
|---|---|---|---|
| J | HRO TYPE-C-31-M-12 | C165948 | A6/B6 -> USB_UP_DP, A7/B7 -> USB_UP_DM; VBUS -> HOST_VBUS (detection only, never joined to any rail) |
| Rd x2 | 5.1 k 1 % 0402 | (Basic, 0402WGF5101TCE) | CC1 -> GND, CC2 -> GND (UFP / sink) |
| ESD | TPD4E05U06DQAR | C138714 | DP, DM, CC1, CC2 |
| VBUS detect | 100 k / 100 k divider HOST_VBUS -> hub A VBUS_DET | C25741 | hub-design.md |
| VBUS TVS | SMF6.0A | C123790 | HOST_VBUS |
| C | 1 uF 0402 on HOST_VBUS | Basic | small, so the hub never presents a big cap to the host |

## PD input connector

GCT USB4105-GF-A (C3020560, 5 A VBUS). VBUS -> TVS + Schottky + caps -> TPS25730 VBUS (power-design-pd-3v3.md);
CC1/CC2 -> TPS25730 CC1/CC2 with 330 pF C0G + PESD24VS1UL each; D+/D- not connected; shell -> GND.


## Capture notes (schematic capture, 2026-11-16)

- **RSET 1.87 k is C270633 (UNI-ROYAL 0402WGF1871TCE), an Extended part**, not Basic as the table above says.
  It was the stocked 1.87 k found at capture; a 1.8 k would give 3.94 A nominal (away from the datasheet's tested
  1.878 k point, SY6863 p4), so the Extended part was kept.
- **TPD4E05U06 NC pins 6, 7, 9, 10 floating** (TPD4E05U06 p4: "Can be left floating or grounded").
- **Port D+/D-**: the hub's DP/DM go to the ESD array; the receptacle's D+/D- join them through local labels
  "DP"/"DM", which KiCad merges with the sheet's hierarchical labels of the same name (checked with netspec).
- **CC2's Rp (R3)** is drawn hanging below CC2 to a VBUS label so it does not cross CC1; same circuit as R2.

## Fit-to-board changes (2026-11-16, user-approved: board 80 x 80, trims)
- Per-port VBUS TVS (SMF6.0A) and the HOST VBUS TVS removed (SY6863 OUT rated 28 V; TPD4E05U06 covers DP/DM/CC).
- Port C_IN 10 uF now 0603 10 V (CL10A106KP8NNNC C19702); port C_OUT 22 uF now 0603 10 V (CL10A226MQ8NRNC C59461).
- Test pads 1.0 mm.
