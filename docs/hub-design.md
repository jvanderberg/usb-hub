# Hub IC design: USB2517 (hub A) + USB2514B (hub B), pin by pin

Revision: 0 - Date: 2026-11-16 - Status: proposal (not yet agreed; decisions for the user in section 10)

Sources (all page numbers below refer to these):

| Short name | Document | File |
|---|---|---|
| 2517 | Microchip USB2517/USB2517I, DS00001598C (2018) | `docs/datasheets/USB2517-JZX.pdf` |
| 2514B | Microchip USB251xB/xBi, DS00001692C (2015) | `docs/datasheets/USB2514B-AEZC-TR.pdf` |
| SY6863 | Silergy SY6863B3, Rev 0.9C (2024) | `docs/datasheets/SY6863B3ABC.pdf` |
| TPS3809 | TI TPS3809x, SLVS228D (2020) | not in the repo yet: downloaded from ti.com/lit/ds/symlink/tps3809.pdf for this work, add it to `docs/datasheets/` |
| 3V3 | `docs/power-design-pd-3v3.md` s4 (TPS54202 3V3 buck, internal 5 ms soft start) | |

Stock: LCSC **global**, 2026-11-16, needed = 5 boards + 10 % attrition (from `docs/sourcing.json`).

## 0. Summary of decisions

| # | Item | Choice | Why (datasheet) |
|---|---|---|---|
| 1 | Configuration mode, both hubs | Internal default + straps: 2517 CFG_SEL[2:0] = 000, 2514B CFG_SEL[1:0] = 00 | 2517 Table 5-2 p15: 000 = "Internal Default Configuration, Strap Options are Enabled". 2514B Table 5-1 p19: 00 = "strap options enabled, self-powered, individual power switching, individual over-current sensing" |
| 2 | Self-powered, MTT, individual power + individual OC sense | Comes from the default ROM; GANG_EN strap (2517 only) = 0 | 2517 Table 7-1 p20: CFG1 (06h) = 9Bh = SELF_BUS_PWR 1, MTT_ENABLE 1, CURRENT_SNS 01 (individual), PORT_PWR 1 (individual) (p23-24). GANG_EN '0' = individual (p11). 2514B CFG1 = 9Bh (p20, p22) |
| 3 | PRTPWR polarity | Active high on both hubs; matches SY6863B3**A**BC (EN active high) | 2517 p10 and s7.1.1.1 p19 "active high power controllers only"; 2514B p12 (no _N suffix = active high, naming rule p12) and Fig 4-1 p17; SY6863 p1 ordering table, p2 |
| 4 | PRTPWR line | 10 k to GND on every PRTPWR net (EN pull-down for SY6863, BC_EN = 0 strap for 2514B) | SY6863 p2 "EN ... Do not leave it floating", layout Fig 4 p11 shows R_ENB; EN VIL 0.4 V (p4) vs hub output leakage up to 10 uA (2517 Table 8-2 p50) -> R <= 40 k; 2514B Fig 3-5 p15 (Strap Low) |
| 5 | Battery charging (2514B BC_EN) | **Off** on all four hub B ports (recommended) | See s4.3 |
| 6 | OCS inputs | No external pull-up: both hubs have an internal pull-up to 3.3 V on OCS; SY6863 OCB wired straight to it | 2517 p12 "Contains internal pull-up to 3.3V supply" (IPU, 35-90 uA, Table 8-2 p49 = 37-94 k equivalent); 2514B p4, p12 (IPU). SY6863 Fig 1 p1 asks for 10 k-100 k: the IPU is in that range |
| 7 | Strap resistors (I/O straps, LED-type straps) | 47 k to GND (all straps are "0") | 2514B Table 3-3 p14: 47-100 k; 2517 Fig 7-3 p42 shows 100 k. 47 k chosen because 100 k x 10 uA worst leakage (Table 8-2 p50) = 1.0 V > VIL 0.8 V; 47 k gives 0.47 V |
| 8 | Hub A LED pins | No hub-driven LEDs; every LED pin that is a strap gets 47 k to GND; LED_B4..B7 (no strap) NC. Port LEDs are driven from each port's switched VBUS as planned | s3.4 |
| 9 | Hub A VBUS_DET | HOST_VBUS -> 100 k -> HUBA_VBUS_DET -> 100 k -> GND | s5.2 |
| 10 | Hub B VBUS_DET | Driven by hub A **PRTPWR7** (net HUBB_VBUS_DET), 10 k to GND; DNP 0R fallback from 3V3 | 2514B p12: "For self-powered applications with a permanently attached host, this pin must be connected to a dedicated host control output, or ... the 3.3 V domain". See s5.3 |
| 11 | Hub B "non-removable" on hub A port 7 | **Not possible by strap.** NON_REM straps cover ports 1-3 only. Proposed: leave all ports removable (NON_REM = 00) | 2517 p13-14 (NON_REM[1:0] -> ports 1, 1-2, 1-3 only); Table 7-1 p20 NRD default 00h. Decision D1 in s10 |
| 12 | Reset | One supervisor TI TPS3809K33DBVR (2.93 V, push-pull, 120-280 ms) drives HUB_RESET_N of both hubs; 100 k to GND on the net | 3V3 rises in ~5 ms (3V3 s4), beyond the 400 us the hubs allow unless RESET_N is actively held low (2517 Note 8-1 p48; 2514B Note 6-2 p40). See s5.1 |
| 13 | RBIAS | 12.0 k 1 % to GND, each hub | 2517 p12; 2514B p12 |
| 14 | Crystal | YXC X322524MOB4SI, 24 MHz, CL 12 pF, +/-10 ppm, 3225, one per hub (C70590). Load caps: hub A 18 pF + 1 M across the crystal; hub B 15 pF, no external 1 M | s5.4 |
| 15 | 1.8 V / filter pins | 2517 VDD18 and VDD18PLL: 1.0 uF each (0603 X5R 50 V). 2514B CRFILT and PLLFILT: 100 nF each | 2517 p15 "must have a 1.0 uF (or greater) +/-20 % (ESR < 0.1 ohm)"; 2514B p14 "can have up to a 0.1 uF low-ESR capacitor ... or be left unconnected" |
| 16 | TEST | 2517 TEST -> GND; 2514B TEST -> NC | 2517 p15 (IPD, test mode); 2514B p14 "treat as a no connect pin or connect to ground. No trace or signal should be routed or attached" |

## 1. Topology, port map and net names

```
HOST USB-C --USB_UP_DP/DM--> hub A USB2517 --HUBA_DN1..6--> P1..P6 (SY6863 EN <- HUBA_PRTPWR1..6, OCB -> HUBA_OCS1..6_N)
                                           '--HUBA_DN7_DP/DM--> hub B USB2514B upstream (on board)
                                           '--HUBA_PRTPWR7 = HUBB_VBUS_DET
                                hub B --HUBB_DN1..4--> P7..P10 (SY6863 EN <- HUBB_PRTPWR1..4, OCB -> HUBB_OCS1..4_N)
HOST_VBUS -> 100k/100k -> HUBA_VBUS_DET           TPS3809K33 -> HUB_RESET_N -> both hubs
```

| User port | Hub / port | uhubctl address (Linux) | Data nets | Power nets |
|---|---|---|---|---|
| P1-P6 | A / 1-6 | `-l <A> -p 1..6` | HUBA_DNn_DP / HUBA_DNn_DM | HUBA_PRTPWRn, HUBA_OCSn_N |
| P7-P10 | B / 1-4 | `-l <A>.7 -p 1..4` | HUBB_DNn_DP / HUBB_DNn_DM (n = port - 6) | HUBB_PRTPWRn, HUBB_OCSn_N |
| (hub B) | A / 7 | `-l <A> -p 7` cycles hub B and with it P7-P10 | HUBA_DN7_DP / HUBA_DN7_DM | HUBA_PRTPWR7 = HUBB_VBUS_DET |

Default USB IDs from the internal ROM: hub A 0424:2517 (2517 Table 7-1 p19), hub B 0424:2514 DID 0BB3 (2514B p19).
Both are on uhubctl's list (EVB-USB2517; 0424:2514 on Raspberry Pi 3B+ / reTerminal).

Which receptacle gets which user number is a layout choice; the table above is the logical map. Hub A's PRT_SWP straps
(s3.2) can swap D+/D- per port if a pair crosses during routing; hub B has no swap strap (EEPROM only, 2514B p29).

## 2. Hub A: USB2517-JZX (C1521556), QFN-64 9x9 - pin table

Pin numbers from Fig 3-1 p7 (checked against the rendered page) and Table 5-1 p10-15.

| Pin | Name | Function in this design | Net | External part (value, to) | Ref |
|---|---|---|---|---|---|
| 1 | USBDN1_DM / PRT_DIS_M1 | Port 1 D-; PRT_DIS strap left at default (port enabled) | HUBA_DN1_DM -> P1 | none | p10 |
| 2 | USBDN1_DP / PRT_DIS_P1 | Port 1 D+ | HUBA_DN1_DP -> P1 | none | p10 |
| 3 | USBDN2_DM / PRT_DIS_M2 | Port 2 D- | HUBA_DN2_DM -> P2 | none | p10 |
| 4 | USBDN2_DP / PRT_DIS_P2 | Port 2 D+ | HUBA_DN2_DP -> P2 | none | p10 |
| 5 | VDDA33 | 3.3 V analog PHY supply | 3V3 | 100 nF to GND at pin | p15 |
| 6 | USBDN3_DM / PRT_DIS_M3 | Port 3 D- | HUBA_DN3_DM -> P3 | none | p10 |
| 7 | USBDN3_DP / PRT_DIS_P3 | Port 3 D+ | HUBA_DN3_DP -> P3 | none | p10 |
| 8 | USBDN4_DM / PRT_DIS_M4 | Port 4 D- | HUBA_DN4_DM -> P4 | none | p10 |
| 9 | USBDN4_DP / PRT_DIS_P4 | Port 4 D+ | HUBA_DN4_DP -> P4 | none | p10 |
| 10 | VDDA33 | 3.3 V analog | 3V3 | 100 nF | p15 |
| 11 | USBDN5_DM / PRT_DIS_M5 | Port 5 D- | HUBA_DN5_DM -> P5 | none | p10 |
| 12 | USBDN5_DP / PRT_DIS_P5 | Port 5 D+ | HUBA_DN5_DP -> P5 | none | p10 |
| 13 | CFG_SEL2 | Config select bit 2 = 0 (pure input, type I) | GND | tied directly to GND | p13, Table 5-2 p15 |
| 14 | LED_B7_N | Amber LED port 7, no strap -> unused | NC | none | p11 |
| 15 | LED_A7_N / PRT_SWP7 | Strap PRT_SWP7 = 0 (port 7 = hub link, normal polarity) | HUBA_PRT_SWP7 | 47 k to GND | p11, Fig 7-3 p42 |
| 16 | LED_B6_N | unused | NC | none | p11 |
| 17 | LED_A6_N / PRT_SWP6 | Strap PRT_SWP6 = 0 | HUBA_PRT_SWP6 | 47 k to GND | p11 |
| 18 | LED_B5_N | unused | NC | none | p11 |
| 19 | TEST | Test mode off | GND | tied directly to GND (pin is IPD, low = normal) | p15 |
| 20 | PRTPWR4 | Port 4 power enable | HUBA_PRTPWR4 -> SY6863 EN (P4) | 10 k to GND | p10 |
| 21 | OCS4_N | Port 4 over-current in | HUBA_OCS4_N <- SY6863 OCB (P4) | none (internal pull-up) | p12 |
| 22 | OCS3_N | Port 3 over-current in | HUBA_OCS3_N <- OCB (P3) | none | p12 |
| 23 | PRTPWR3 | Port 3 power enable | HUBA_PRTPWR3 -> EN (P3) | 10 k to GND | p10 |
| 24 | VDD33CR | 3.3 V input of the internal core regulator | 3V3 | 100 nF (+ the hub's 10 uF bulk placed here) | p15 |
| 25 | VDD18 | Internal 1.8 V core output | HUBA_VDD18 | 1.0 uF X5R 0603 to GND, nothing else | p15 |
| 26 | PRTPWR2 | Port 2 power enable | HUBA_PRTPWR2 -> EN (P2) | 10 k to GND | p10 |
| 27 | OCS2_N | Port 2 over-current in | HUBA_OCS2_N <- OCB (P2) | none | p12 |
| 28 | OCS1_N | Port 1 over-current in | HUBA_OCS1_N <- OCB (P1) | none | p12 |
| 29 | PRTPWR1 | Port 1 power enable | HUBA_PRTPWR1 -> EN (P1) | 10 k to GND | p10 |
| 30 | PRTPWR5 | Port 5 power enable | HUBA_PRTPWR5 -> EN (P5) | 10 k to GND | p10 |
| 31 | LED_A5_N / PRT_SWP5 | Strap PRT_SWP5 = 0 | HUBA_PRT_SWP5 | 47 k to GND | p11 |
| 32 | LED_B4_N | unused | NC | none | p11 |
| 33 | LED_A4_N / PRT_SWP4 | Strap PRT_SWP4 = 0 | HUBA_PRT_SWP4 | 47 k to GND | p11 |
| 34 | LED_B3_N / GANG_EN | Strap GANG_EN = 0 = individual sensing and switching | HUBA_GANG_EN | 47 k to GND | p11 |
| 35 | OCS5_N | Port 5 over-current in | HUBA_OCS5_N <- OCB (P5) | none | p12 |
| 36 | PRTPWR7 | Port 7 power enable = "VBUS" for hub B | HUBB_VBUS_DET (through 0R) | 10 k to GND on HUBB_VBUS_DET | p10; 2514B p12 |
| 37 | OCS7_N | Port 7 has no switch | NC (internal pull-up keeps it high) | none | p12 |
| 38 | OCS6_N | Port 6 over-current in | HUBA_OCS6_N <- OCB (P6) | none | p12 |
| 39 | PRTPWR6 | Port 6 power enable | HUBA_PRTPWR6 -> EN (P6) | 10 k to GND | p10 |
| 40 | SDA / SMBDATA / NON_REM1 | Strap NON_REM1 = 0 (no SMBus, no EEPROM) | HUBA_NON_REM1 | 47 k to GND | p13 |
| 41 | SCL / SMBCLK / CFG_SEL0 | Strap CFG_SEL0 = 0 | HUBA_CFG_SEL0 | 47 k to GND | p13, Table 5-2 p15 |
| 42 | HS_IND / CFG_SEL1 | Strap CFG_SEL1 = 0 (HS_IND then active high) | HUBA_CFG_SEL1 | 47 k to GND (optional LED, s3.4) | p13, Table 5-2 p15 |
| 43 | RESET_N | Hardware reset in (Schmitt) | HUB_RESET_N | from TPS3809K33; 100 k to GND on the net | p14, s7.6 p42-43 |
| 44 | VBUS_DET | Upstream VBUS detect | HUBA_VBUS_DET | 100 k from HOST_VBUS, 100 k to GND | p10, s7.1.2 p19 |
| 45 | SUSP_IND / LOCAL_PWR / NON_REM0 | Strap NON_REM0 = 0 (LOCAL_PWR unused: dynamic power off) | HUBA_NON_REM0 | 47 k to GND | p14, CFG2 p24 |
| 46 | VDD33 | 3.3 V digital I/O | 3V3 | 100 nF | p15 |
| 47 | LED_A3_N / PRT_SWP3 | Strap PRT_SWP3 = 0 | HUBA_PRT_SWP3 | 47 k to GND | p11 |
| 48 | LED_B2_N / BOOST1 | Strap BOOST1 = 0 | HUBA_BOOST1 | 47 k to GND | p12 |
| 49 | LED_A2_N / PRT_SWP2 | Strap PRT_SWP2 = 0 | HUBA_PRT_SWP2 | 47 k to GND | p11 |
| 50 | LED_B1_N / BOOST0 | Strap BOOST0 = 0 | HUBA_BOOST0 | 47 k to GND | p12 |
| 51 | LED_A1_N / PRT_SWP1 | Strap PRT_SWP1 = 0 | HUBA_PRT_SWP1 | 47 k to GND | p11 |
| 52 | VDDA33 | 3.3 V analog | 3V3 | 100 nF | p15 |
| 53 | USBDN6_DM / PRT_DIS_M6 | Port 6 D- | HUBA_DN6_DM -> P6 | none | p10 |
| 54 | USBDN6_DP / PRT_DIS_P6 | Port 6 D+ | HUBA_DN6_DP -> P6 | none | p10 |
| 55 | USBDN7_DM / PRT_DIS_M7 | Port 7 D- -> hub B upstream D- | HUBA_DN7_DM | none | p10 |
| 56 | USBDN7_DP / PRT_DIS_P7 | Port 7 D+ -> hub B upstream D+ | HUBA_DN7_DP | none | p10 |
| 57 | VDDA33 | 3.3 V analog | 3V3 | 100 nF | p15 |
| 58 | USBUP_DM | Upstream D- | USB_UP_DM -> HOST receptacle (via its ESD clamp) | none | p10 |
| 59 | USBUP_DP | Upstream D+ | USB_UP_DP -> HOST receptacle | none | p10 |
| 60 | XTAL2 | Crystal out (drives nothing else) | HUBA_XTAL2 | crystal, 18 pF to GND, 1 M to XTAL1 | p14, Fig 9-1 p52 |
| 61 | XTAL1 / CLKIN | Crystal in | HUBA_XTAL1 | crystal, 18 pF to GND | p14, Fig 9-1 p52 |
| 62 | VDD18PLL | Internal 1.8 V PLL output | HUBA_VDD18PLL | 1.0 uF X5R 0603 to GND, nothing else | p15 |
| 63 | RBIAS | PHY bias | HUBA_RBIAS | 12.0 k 1 % to GND, short trace | p12 |
| 64 | VDD33PLL | 3.3 V input of the PLL regulator | 3V3 | 100 nF | p15 |
| EP | VSS (thermal slug) | Only ground of the package | GND | via array to L2 GND | Fig 3-1 p7 |

Hub A totals: 14 x 47 k, 7 x 10 k (PRTPWR1-6 and HUBB_VBUS_DET), 2 x 100 k, 1 x 12.0 k, 1 x 1 M, 7 x 100 nF,
2 x 1.0 uF, 1 x 10 uF, 2 x 18 pF, 1 x crystal, 1 x 0R (PRTPWR7 link). Six PRTPWR/OCS pairs go to switches.

## 3. Hub A configuration explained

### 3.1 What CFG_SEL = 000 loads (2517 Table 5-2 p15, Table 7-1 p19-21)

| Register | Default | Decoded | Ref |
|---|---|---|---|
| CFG1 06h | 9Bh = 1001 1011b | bit7 SELF_BUS_PWR = 1 self-powered; bit5 HS_DISABLE = 0; bit4 MTT_ENABLE = 1 (one TT per port); bit3 EOP_DISABLE = 1; bits2:1 CURRENT_SNS = 01 individual; bit0 PORT_PWR = 1 individual | p23-24 |
| CFG2 07h | 20h | DYNAMIC = 0 (LOCAL_PWR ignored), OC_TIMER = 10 = 8 ms, COMPOUND = 0 | p24-25 |
| CFG3 08h | 00h | PRTMAP_EN = 0, LED_MODE = 00 (USB mode), STRING_EN = 0 (no strings) | p25 |
| NRD 09h | 00h | all removable unless NON_REM straps say otherwise | p26 |
| PDS/PDB 0Ah/0Bh | 00h | no port disabled unless PRT_DIS straps say otherwise | p26-27 |
| MAXPS 0Ch / HCMCS 0Eh | 01h | 2 mA from upstream VBUS (self-powered) | p27-28 |
| PWRT 10h | 32h | power-on-to-good 100 ms reported to the host (SY6863 rise 1.5-4.5 ms, p4) | p28 |
| BOOST F6h-F8h, PRTSP FAh | 00h | normal drive, no swap (straps can override boost and swap) | p31-33 |

CFG_SEL2 = 0, CFG_SEL1 = 0, CFG_SEL0 = 0 is the only row of Table 5-2 that keeps straps enabled and does not force
bus power (010) or ganged switching (111). 100/101 would turn on dynamic power switching; avoid.

### 3.2 Straps sampled at RESET_N negation (Table 5-1 p10-14; setup/hold 16.7 ns / 1400 ns max, Table 7-6 p43)

| Strap | Pin(s) | Value | Resistor | Effect |
|---|---|---|---|---|
| CFG_SEL[2:0] | 13, 42, 41 | 000 | 13 to GND direct; 42, 41: 47 k to GND | internal default + straps |
| GANG_EN | 34 | 0 | 47 k to GND | individual sensing and switching; LED_B3_N active high (p11) |
| NON_REM[1:0] | 40, 45 | 00 | 47 k to GND each | all ports removable; SUSP_IND active high (p13-14) |
| PRT_SWP[7:1] | 15, 17, 31, 33, 47, 49, 51 | 0 each | 47 k to GND each | normal D+/D- polarity per port; LED_Ax active high (p11). Layout may strap a port to 1 (47 k to 3V3 instead) to un-cross its pair |
| BOOST[1:0] | 48, 50 | 00 | 47 k to GND each | no PHY boost (p12; boost "could result in non-USB compliant parameters", p31) |
| PRT_DIS_P/M[7:1] | USB data pins | 0 | none ("To disable, pull up with 10K resistor to 3.3V", p10) | all ports enabled |

### 3.3 Port 7 "non-removable": not available by strap

NON_REM[1:0] can only mark ports 1, 1-2 or 1-3 non-removable (p13-14); the NRD register (p26) that could mark port 7
needs an EEPROM or SMBus, which the architecture excludes. Being marked removable has no functional effect on a hub
(the host enumerates and powers it the same; uhubctl does not look at it). Proposal: keep hub B on port 7 with
NON_REM = 00. Alternative: move hub B to hub A port 1 and strap NON_REM = 01 (pin 45 47 k to 3V3); the hub then
reports itself as a compound device (Note on CFG2 COMPOUND, p25) and SUSP_IND becomes active low (p14). Decision D1.

### 3.4 LED pins

Every LED_A pin and LED_B1-B3 doubles as a strap, so each must have its 47 k pull-down (Fig 7-3 p42: the 100 k is
always present, the LED is optional in parallel). No LEDs are hung on them:

- Hub B (2514B) has no port LED pins at all, so hub-driven LEDs would cover only ports 1-6.
- The pin text says LEDs are active "when LED support is enabled via EEPROM or SMBus" (p11), while CFG3 = 00h (USB
  mode, p25) is loaded in default mode too: whether the port LEDs toggle in strap mode is not stated.
- A LED on the port's switched VBUS shows what uhubctl actually switched.

LED_B4..B7 (pins 32, 18, 16, 14) are pure outputs with no strap: NC.

Optional, costs one LED + one resistor: a "HOST" LED on pin 45 SUSP_IND (asserted = configured and not suspended,
p14) or pin 42 HS_IND (asserted = linked at high speed, p13): LED + 1 k to GND in parallel with the 47 k strap
(both straps are 0 -> active high, the pad sources the current; 12 mA buffer, Table 5-3 p16). Not in the BOM (D5).

## 4. Hub B: USB2514B-AEZC-TR (C16251), QFN-36 6x6 - pin table

Pin numbers from Fig 3-3 p9 (checked against the rendered page) and Table 3-1 p10-11.

| Pin | Name | Function in this design | Net | External part (value, to) | Ref |
|---|---|---|---|---|---|
| 1 | USBDM_DN1 / PRT_DIS_M1 | Port 1 D- | HUBB_DN1_DM -> P7 | none | p12 |
| 2 | USBDP_DN1 / PRT_DIS_P1 | Port 1 D+ | HUBB_DN1_DP -> P7 | none | p12 |
| 3 | USBDM_DN2 / PRT_DIS_M2 | Port 2 D- | HUBB_DN2_DM -> P8 | none | p12 |
| 4 | USBDP_DN2 / PRT_DIS_P2 | Port 2 D+ | HUBB_DN2_DP -> P8 | none | p12 |
| 5 | VDDA33 | 3.3 V analog | 3V3 | 100 nF | p14 |
| 6 | USBDM_DN3 / PRT_DIS_M3 | Port 3 D- | HUBB_DN3_DM -> P9 | none | p12 |
| 7 | USBDP_DN3 / PRT_DIS_P3 | Port 3 D+ | HUBB_DN3_DP -> P9 | none | p12 |
| 8 | USBDM_DN4 / PRT_DIS_M4 | Port 4 D- | HUBB_DN4_DM -> P10 | none | p12 |
| 9 | USBDP_DN4 / PRT_DIS_P4 | Port 4 D+ | HUBB_DN4_DP -> P10 | none | p12 |
| 10 | VDDA33 | 3.3 V analog | 3V3 | 100 nF | p14 |
| 11 | TEST | unused | NC (no trace) | none (IPD) | p14 |
| 12 | PRTPWR1 / BC_EN1 | Port 1 power enable; BC_EN1 strap = 0 | HUBB_PRTPWR1 -> SY6863 EN (P7) | 10 k to GND | p12, Fig 3-5 p15 |
| 13 | OCS_N1 | Port 1 over-current in | HUBB_OCS1_N <- OCB (P7) | none (IPU) | p12 |
| 14 | CRFILT | Core regulator filter | HUBB_CRFILT | 100 nF X7R to GND | p14 |
| 15 | VDD33 | 3.3 V digital | 3V3 | 100 nF (+ the hub's 10 uF bulk here) | p14 |
| 16 | PRTPWR2 / BC_EN2 | Port 2 power enable; BC_EN2 = 0 | HUBB_PRTPWR2 -> EN (P8) | 10 k to GND | p12 |
| 17 | OCS_N2 | Port 2 over-current in | HUBB_OCS2_N <- OCB (P8) | none | p12 |
| 18 | PRTPWR3 / BC_EN3 | Port 3 power enable; BC_EN3 = 0 | HUBB_PRTPWR3 -> EN (P9) | 10 k to GND | p12 |
| 19 | OCS_N3 | Port 3 over-current in | HUBB_OCS3_N <- OCB (P9) | none | p12 |
| 20 | PRTPWR4 / BC_EN4 | Port 4 power enable; BC_EN4 = 0 | HUBB_PRTPWR4 -> EN (P10) | 10 k to GND | p12 |
| 21 | OCS_N4 | Port 4 over-current in | HUBB_OCS4_N <- OCB (P10) | none | p12 |
| 22 | SDA / SMBDATA / NON_REM1 | Strap NON_REM1 = 0 | HUBB_NON_REM1 | 47 k to GND | p13, Table 3-3 p14 |
| 23 | VDD33 | 3.3 V digital | 3V3 | 100 nF | p14 |
| 24 | SCL / SMBCLK / CFG_SEL0 | Strap CFG_SEL0 = 0 | HUBB_CFG_SEL0 | 47 k to GND | p13, Table 5-1 p19 |
| 25 | HS_IND / CFG_SEL1 | Strap CFG_SEL1 = 0 | HUBB_CFG_SEL1 | 47 k to GND | p13, Table 5-1 p19 |
| 26 | RESET_N | Hardware reset in | HUB_RESET_N | shared supervisor | p13, s5.5 p35-36 |
| 27 | VBUS_DET | Upstream VBUS detect = hub A port 7 power | HUBB_VBUS_DET | 10 k to GND (shared with hub A pin 36); DNP 0R to 3V3 | p12 |
| 28 | SUSP_IND / LOCAL_PWR / NON_REM0 | Strap NON_REM0 = 0 | HUBB_NON_REM0 | 47 k to GND | p14 |
| 29 | VDDA33 | 3.3 V analog | 3V3 | 100 nF | p14 |
| 30 | USBDM_UP | Upstream D- | HUBA_DN7_DM | none | p12 |
| 31 | USBDP_UP | Upstream D+ | HUBA_DN7_DP | none | p12 |
| 32 | XTALOUT | Crystal out (1.2 Vpp, < 1 mA) | HUBB_XTALOUT | crystal, 15 pF to GND | p13, Fig 7-1 p44 |
| 33 | XTALIN / CLKIN | Crystal in | HUBB_XTALIN | crystal, 15 pF to GND (1 M is internal, p44) | p13, p44 |
| 34 | PLLFILT | PLL regulator filter | HUBB_PLLFILT | 100 nF X7R to GND | p14 |
| 35 | RBIAS | PHY bias | HUBB_RBIAS | 12.0 k 1 % to GND | p12 |
| 36 | VDDA33 | 3.3 V analog | 3V3 | 100 nF | p14 |
| EP | VSS | Only ground of the package, "multiple vias" | GND | via array | p14 |

Hub B totals: 4 x 47 k, 4 x 10 k, 1 x 12.0 k, 8 x 100 nF (6 supply + CRFILT + PLLFILT), 1 x 10 uF, 2 x 15 pF,
1 x crystal, 1 x DNP 0R.

### 4.1 What CFG_SEL = 00 loads

Table 5-1 p19 states it outright: straps enabled, self-powered, individual power switching, individual OC sensing.
Default ROM (p19-20): CFG1 9Bh (same decode as hub A, p22), CFG2 20h (OC_TIMER 8 ms, p23), CFG3 02h (strings off,
p23), NRD 00h, BC_EN register D0h = 00h (p28), boost and swap 00h.

### 4.2 Straps

| Strap | Pins | Value | Resistor | Ref |
|---|---|---|---|---|
| CFG_SEL[1:0] | 25, 24 | 00 | 47 k to GND each | Table 5-1 p19 |
| NON_REM[1:0] | 22, 28 | 00 (P7-P10 are user ports) | 47 k to GND each | p13-14 |
| BC_EN[4:1] | 12, 16, 18, 20 | 0000 | 10 k to GND each (also the SY6863 EN pull-down) | p12, Fig 3-5 p15 |
| PRT_DIS | USB data pins | 0 | none | p12 |

Section 3.3.1.1 (p15) says an I/O strap needs no part for "low" because "the internal pull-down provides the
resistor", but the buffer table lists those pins as plain I/O (p13-14, Table 3-4 p16). The explicit 47 k works
either way.

### 4.3 Battery charging: recommendation OFF

With BC_EN = 1 a port "turns on port power as soon as the power on reset and hardware configuration process has
completed. The hub does not need to be enumerated nor does VBUS_DET need to be asserted" (s4.1 p17), and USB bus
reset no longer negates PRTPWR (s5.5.2 p38). After an over-current with no host, PRTPWR only comes back from the
host or a RESET_N toggle (s4.1.1 p17). Reasons to leave it off:

1. P1-P6 (USB2517, no BC support) cannot do it, so four ports would behave differently from six.
2. Ports would be powered before and without a host, while the rest of the hub keeps ports dark until the host
   powers them; it would also change what `uhubctl -a off` on hub B means. Whether the host can still switch a BC
   port off is not stated in the datasheet.
3. The gain is small: every port already advertises 3 A through Type-C Rp; BC1.2 only helps legacy devices on
   C-to-micro-B cables.

Compatibility if you ever want it: Strap High is "R k" to +V with the internal pull-down (Fig 3-5 p15, R = 10 k per
Table 3-3 p14). A 10 k pull-up fighting the 10 k EN pull-down gives only 1.65 V (VIH 2.0 V, Table 6-1 p40), so the
pull-down would have to be removed on any port switched to BC. A port with BC on also starts powered during reset,
which the SY6863 accepts (EN 1.0 V VIH, p4).

## 5. Shared circuits

### 5.1 RESET_N (both hubs) - supervisor, no RC

- The hubs allow a 3.3 V rise time of at most 400 us when relying on the internal POR (2517 p48 tRT; 2514B p39
  tRT33). The 3V3 rail here rises in ~5 ms (TPS54202 internal soft start, 3V3 s4).
- Longer rise (up to 100 ms) is allowed "if RESET_N is controlled low during the 3.3V rise time and driven high after
  VDD33 is stable" (2517 Note 8-1 p48) / "actively driven low, typically by another IC, until 1 us after all
  supplies are within operating range" (2514B Note 6-2 p40). An RC is not "actively driven" and only just holds
  below VIL 0.8 V on a 5 ms ramp, so it is not used.
- Part: **TI TPS3809K33DBVR** (C61364, Extended, 4,832 global 2026-11-16; need 6): VIT- 2.87/2.93/2.99 V, hysteresis
  40 mV, push-pull active-low output, RESET held low from VDD = 1.1 V (VOL <= 0.2 V), td = 120/200/280 ms after VDD
  crosses VIT (TPS3809 p1, p3, p4, p5, p6). 100 nF on its VDD (TPS3809 p4). 3-pin SOT-23: 1 GND, 2 RESET, 3 VDD.
- 100 k from HUB_RESET_N to GND so the net is low below 1.1 V too (R12).
- One supervisor drives both RESET_N pins. Holding hub B in reset until hub A is up is not needed and not asked for
  by either datasheet: hub B cannot attach until hub A powers port 7 (s5.3). Test point on HUB_RESET_N
  (requirements s3 bring-up table).
- Timing check: td min 120 ms >> the 1 us minimum assertion (2517 Table 7-6 p43; 2514B p36); straps are read at the
  rising edge (setup 16.7 ns, hold <= 1.4 us).
- Note: the hubs are specified from 3.0 V (2517 p48, 2514B p39). The supervisor releases at 2.91-3.03 V and resets
  below 2.87-2.99 V, so in a slow brownout the hub can run a few tens of mV under spec before reset. The 3V3 rail
  sits at 3.17-3.44 V worst case (3V3 s4), so this only matters while the rail is collapsing.

### 5.2 Hub A VBUS_DET (pin 44)

- Wiring: HOST_VBUS (HOST receptacle VBUS, nothing else attached) -> 100 k -> HUBA_VBUS_DET -> 100 k -> GND.
  Test point on HUBA_VBUS_DET.
- The 2517 says "connect to VBUS" for a detachable hub (p10), and its I/O pins tolerate 5.5 V (p47). Microchip
  suggests a 2:1 divider with two 100 k for the same function on the 2514B (p12); used here for margin and to cut
  the current into an unpowered chip.
- Levels (1 % resistors): VBUS 4.40 V (lowest USB 2.0 hub-port voltage) -> 2.18 V min > VIH 2.0 V (TTL, Table 8-2
  p49). VBUS 5.5 V -> 2.75 V. VBUS off (< 0.8 V) -> < 0.4 V < VIL 0.8 V.
- Host present, hub unpowered (no PD brick): the pin sees up to 2.75 V from a 50 k source with VDD33 = 0. Within the
  absolute maximum (-0.5 to 5.5 V on any I/O pin, p47, not referenced to VDD). The operating limit of
  "VDD33 + 0.5 V when a 3.3 V supply is below 3.0 V" (p48) is a functional limit, and nothing works in that state
  anyway. Worst-case injection if the pin has a clamp to VDD33: ~(2.75 - 0.5) / 50 k = 45 uA into a dead 3V3 rail.
  Bench check.
- Hub powered, host absent: the pin reads 0 V, the hub does not pull D+ up (s7.1.2 p19), stays unconfigured, ports
  stay unpowered. This is the intended "enumerates when host VBUS is seen" (requirements s3).
- The divider draws 25-27 uA from the host, below the 2 mA a self-powered hub may take (p23).

### 5.3 Hub B VBUS_DET (pin 27) = hub A PRTPWR7

- 2514B p12: with a permanently attached host, VBUS_DET "must be connected to a dedicated host control output, or
  connected to the 3.3 V domain that powers the host". Hub A's PRTPWR7 is that control output: it is asserted
  exactly when the host has powered hub A port 7 (O12 output, VOH >= 2.4 V, 2517 Table 8-2 p50, VIH 2.0 V on the
  2514B, Table 6-1 p40).
- Net HUBB_VBUS_DET: hub A pin 36 -> 0R (fitted) -> hub B pin 27; 10 k to GND; DNP 0R from 3V3 (fallback: remove
  the series 0R, fit the DNP to tie VBUS_DET to 3V3 as the datasheet's other option).
- Why not just 3V3:
  1. Hub B attaches only after hub A is configured and port 7 powered. With 3V3, hub B's 1.5 k D+ pull-up could be
     on pin 56 (USBDN7_DP / **PRT_DIS_P7**) when hub A samples its straps, which can read as "port 7 disabled"
     (p10: "To disable, pull up with 10K resistor to 3.3V").
  2. `uhubctl -l <A> -p 7 -a cycle` then gives hub B a real VBUS loss and re-attach, which resets hub B and with it
     P7-P10.
- Side effect: `uhubctl -l <A> -a off` (all ports of hub A) also drops hub B and P7-P10. That is the expected
  behaviour for a hub tree; document it on the case or in the README.

### 5.4 Crystals

Requirement: parallel resonant, fundamental, 24 MHz +/-350 ppm (2517 s9.1 p52; 2514B s7.1 p44). The 2517's XTAL2
"must not be used to drive any external circuitry other than the crystal circuit" (p14), so each hub gets its own.

Part: **YXC X322524MOB4SI** (C70590, Extended, 316,421 global 2026-11-16; need 11): 24 MHz, CL 12 pF, +/-10 ppm,
+/-20 ppm over temperature, ESR 50 ohm, SMD3225-4P (LCSC listing; the YXC datasheet has not been read, check the
pad numbering against the footprint: normally 1 and 3 = crystal, 2 and 4 = case/GND). 12 pF chosen over the 20 pF
X322524MSB4SI (C15643) because smaller load caps mean more oscillator margin; neither datasheet sets an ESR or drive
limit. No 24 MHz crystal is a JLC Basic part, so this adds one Extended loading.

Board stray CB is estimated at 3 pF per pin (short traces, crystal within 5 mm).

- Hub A (Fig 9-1/9-2 p52): CL = (C1 + CS1)(C2 + CS2) / (C1 + CS1 + C2 + CS2), CS = CB + CXTAL, CXTAL = 2 pF max
  (Table 8-3 p51) -> CS = 5 pF. Symmetric: C = 2 CL - CS = 24 - 5 = 19 pF -> **18 pF** C0G (effective CL 11.5 pF).
  Fig 9-1 shows a **1 M** resistor across the crystal: fitted (XTAL1 to XTAL2).
- Hub B (Fig 7-2 p44): C1 = 2 (CL - C0) - CS1 with C0 = 0 (Note 7-1), CS = CB + CXTAL, CXTAL = 6 pF max
  (Table 6-8 p42) -> CS = 9 pF: C = 24 - 9 = **15 pF** C0G (effective CL 12.0 pF; 13.5 pF if CXTAL is only 3 pF).
  The 1 M feedback resistor is internal ("internal 1 M resistor between the XTALIN and XTALOUT pins", p44): none
  fitted. Note 7-2 says "typically around 18 pF", consistent with this range.
- Frequency error from a +/-2 pF load mismatch is a few tens of ppm, against a 350 ppm budget.

### 5.5 Decoupling and regulator outputs

| Hub | Pins | Part | Why |
|---|---|---|---|
| A | 5, 10, 52, 57 (VDDA33), 24 (VDD33CR), 46 (VDD33), 64 (VDD33PLL) | 100 nF X7R 0402 each, at the pin, via straight to GND | One per supply pin; the datasheet gives no decoupling table (pins p15) |
| A | 24 area | 10 uF X5R 0603 10 V bulk (one per hub) | 460 mA load steps (Table 8-2 p50); the 3V3 buck's 3 x 22 uF is on the other side of the board. 0603 because a 0402 10 uF 6.3 V keeps only a fraction at 3.3 V |
| A | 25 VDD18, 62 VDD18PLL | 1.0 uF X5R 0603 50 V (CL10A105KB8NNNC) each, nothing else on these nets | p15 "1.0 uF (or greater) +/-20 % (ESR < 0.1 ohm)"; 0603 50 V keeps ~1 uF at 1.8 V where an 0402 1 uF would fall below 0.8 uF |
| B | 5, 10, 29, 36 (VDDA33), 15, 23 (VDD33) | 100 nF each | one per supply pin (p14) |
| B | 15 area | 10 uF 0603 bulk | as hub A (155 mA) |
| B | 14 CRFILT, 34 PLLFILT | 100 nF X7R each | p14 "up to a 0.1 uF low-ESR capacitor"; "or left unconnected" is allowed but the cap is the documented filter |
| shared | TPS3809 VDD | 100 nF | TPS3809 p4 |

No 1.2 V rail is needed: the 2514B makes its core voltage internally (CRFILT, p14; 1.2 V regulator in Fig 2-1 p6),
the 2517 makes 1.8 V internally (VDD18/VDD18PLL). The requirements' tentative 1V2 rail (s4) can be dropped.

## 6. Interface-line states (R12)

"3V3 off" = no PD brick (VIN absent); 5V_BUS is then off too, because both come from VIN and 5V_BUS needs VIN >= 7.5 V.
"Reset" = 3V3 rising and the 120-280 ms supervisor delay. "Idle" = out of reset, host absent or hub not yet
configured.

| Net | 3V3 off | Reset | Idle (no host / unconfigured) | Running | What defines it |
|---|---|---|---|---|---|
| HUBA_PRTPWR1-6 | 0 V (10 k) | low: "PRTPWR power to downstream devices is removed" (2517 p42) + 10 k | low until the host sets PORT_POWER; USB reset negates it (p46) | high = port on | 10 k to GND; SY6863 EN VIL 0.4 V (p4) |
| HUBB_PRTPWR1-4 / BC_EN | 0 V (10 k) | input with internal pull-down (IPD p12) + 10 k = low, read as BC_EN = 0 | low (p35, p38) | high = port on | 10 k to GND |
| HUBB_VBUS_DET (= HUBA_PRTPWR7) | 0 V | low | low: hub B stays detached | high once the host powers A port 7 | 10 k to GND |
| HUBA_OCS1-6_N, HUBB_OCS1-4_N | ~0 V (internal pull-up to a dead rail); SY6863 unpowered too | high via IPU | high via IPU; low only on SY6863 fault (OC > 15 ms, OVP, OTP, p10) | same | hub IPU 35-90 uA to 3.3 V (2517 p12, Table 8-2 p49; 2514B p12, p40). External pull-up, if ever added, goes to **3V3**, never 5V_BUS (I/O max = VDD + 0.5 V when 3.3 V < 3.0 V, 2517 p48, 2514B p39) |
| HUB_RESET_N | 0 V (100 k) | low (TPS3809 from VDD 1.1 V, p1, p5) | high | high | supervisor, 100 k to GND |
| HUBA_VBUS_DET | 0 V or up to 2.75 V if a host is plugged in (s5.2) | follows host VBUS | follows host VBUS | follows host VBUS | 100 k/100 k |
| Strap nets (47 k) | 0 V | 0 V, sampled at the rising edge | hub may drive LED/IND outputs; 47 k load = 70 uA | same | 47 k to GND |

PRTPWR is active high on both hubs (verified: 2517 p10, p19; 2514B p12, Fig 4-1 p17). OCS: both hubs have internal
pull-ups, so the SY6863 open-drain OCB needs no external part.

Open point: the SY6863 datasheet does not say what OCB does while its IN (5V_BUS) is unpowered. If it pulls low,
the hubs report over-current on every port while 5V_BUS is still off (start-up before the PD contract, or a 5 V-only
brick). Bench check B4.

## 7. Parts list (both hubs and shared)

All 0402 unless noted. Stock: LCSC global, 2026-11-16; need = per board x 5 x 1.1.

| Value | Use | Package | Hub A | Hub B | Shared | Per board | Need | LCSC | MPN | Class | Stock |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 nF 16 V X7R | supply pins, CRFILT, PLLFILT, TPS3809 VDD | 0402 | 7 | 8 | 1 | 16 | 88 | C1525 | Samsung CL05B104KO5NNNC | Basic | 37,284,558 |
| 10 uF 10 V X5R | hub bulk | 0603 | 1 | 1 | - | 2 | 11 | C19702 | Samsung CL10A106KP8NNNC | Basic | 11,363,514 |
| 1.0 uF 50 V X5R | 2517 VDD18, VDD18PLL | 0603 | 2 | - | - | 2 | 11 | C15849 | Samsung CL10A105KB8NNNC | Basic | 12,975,150 |
| 18 pF 50 V C0G | hub A crystal | 0402 | 2 | - | - | 2 | 11 | C1549 | FH 0402CG180J500NT | Basic | 928,005 |
| 15 pF 50 V C0G | hub B crystal | 0402 | - | 2 | - | 2 | 11 | C1548 | FH 0402CG150J500NT | Basic | 957,395 |
| 12.0 k 1 % | RBIAS | 0402 | 1 | 1 | - | 2 | 11 | C25752 | UNI-ROYAL 0402WGF1202TCE | Basic | 783,751 |
| 1 M 1 % | 2517 crystal feedback | 0402 | 1 | - | - | 1 | 6 | C26083 | 0402WGF1004TCE | Basic | 2,263,737 |
| 47 k 1 % | strap pull-downs | 0402 | 14 | 4 | - | 18 | 99 | C25792 | 0402WGF4702TCE | Basic | 5,608,670 |
| 10 k 1 % | PRTPWR / EN / BC_EN pull-downs, HUBB_VBUS_DET | 0402 | 7 | 4 | - | 11 | 61 | C25744 | 0402WGF1002TCE | Basic | 20,604,601 |
| 100 k 1 % | VBUS_DET divider (2), HUB_RESET_N pull-down (1) | 0402 | 2 | - | 1 | 3 | 17 | C25741 | 0402WGF1003TCE | Basic | 10,008,555 |
| 0R | PRTPWR7 -> HUBB_VBUS_DET link (fitted) + 3V3 fallback (DNP) | 0402 | 1 | 1 DNP | - | 1 (+1 DNP) | 6 | C17168 | 0402WGF0000TCE | Basic | 15,188,799 |
| 24 MHz 12 pF | crystals | 3225-4P | 1 | 1 | - | 2 | 11 | C70590 | YXC X322524MOB4SI | Extended | 316,421 |
| Supervisor 2.93 V | HUB_RESET_N | SOT-23 | - | - | 1 | 1 | 6 | C61364 | TI TPS3809K33DBVR | Extended | 4,832 |
| Hub A | | QFN-64 | 1 | - | - | 1 | 6 | C1521556 | USB2517-JZX | Extended | 3,035 |
| Hub B | | QFN-36 | - | 1 | - | 1 | 6 | C16251 | USB2514B-AEZC-TR | Extended | 10,035 |

Notes:
- The 18 pF and 15 pF C0G are Fenghua Basic parts; the Samsung equivalents (CL05C180JB5NNNC C307443, CL05C150JB5NNNC
  C86285) are Extended. Samsung CL05/CL10 for everything else.
- New Extended types from this block: crystal and supervisor (+2 loading fees, about $6 per order). A cheaper
  supervisor (onsemi MAX809STRG C9965, 27,692; 2.93 V, push-pull) is pin-compatible but its datasheet has not been
  read.
- Not counted here: SY6863 switches and their RSET/CIN/COUT, port LEDs, ESD, receptacles (port circuit design).

## 8. 3V3 current budget

| Load | Typ | Max | Source |
|---|---|---|---|
| USB2517, 7 ports HS, configured | 420 mA | 460 mA | 2517 Table 8-2 p50 (IHCH7, all supplies combined; max measured at VDD + 20 %, Note 8-6 p51) |
| USB2517 unconfigured / suspend / reset | 95 mA / 0.36 mA / 0.11 mA | - / 0.61 / 0.40 mA | Table 8-2 p50 |
| USB2514B, 4 ports HS, configured | 70 + 3 x 25 = 145 mA | 80 + 3 x 25 = **155 mA** | 2514B Table 6-4 p41 (1-port base + 25 mA per extra port) |
| USB2514B unconfigured HS / suspend / reset | 45 / 0.55 / 0.75 mA | 50 / 1.2 / 1.4 mA | Tables 6-2, 6-6, 6-7 p41-42 |
| Strap and pull-down loads | ~3 mA | ~6 mA | 11 x PRTPWR high into 10 k (0.33 mA each) + 18 x 47 k worst case driven high (0.07 mA each) |
| TPS3809 | 9 uA | - | TPS3809 p1 |
| **Total 3V3, both hubs** | **~570 mA** | **~620 mA** | fits the TPS54202 1 A design point (3V3 s4: 0.615 A hubs + LEDs) |

Port LEDs run from switched VBUS (5V_BUS), not from 3V3.

Thermal: USB2517 at 460 mA x 3.3 V = 1.5 W, theta-JA 27 C/W (Table 8-1 p49) -> +41 C; with < 50 C inside the case
the junction is ~91 C. The commercial part is rated for 0-70 C ambient (Note 8-3 p48), so this is fine, but the
exposed pad needs a full via array to L2. USB2514B: 0.51 W x 40.1 C/W = +20 C (p43).

## 9. Risks and bench checks

Risks found in the datasheets:

1. Port 7 cannot be marked non-removable without an EEPROM (s3.3). Cosmetic; see D1.
2. PRT_DIS straps sit on the USB data pins (2517 p10, 2514B p12). With nothing attached they read 0 because of the
   PHY pull-downs (implied by "pull up with 10K to disable"). The datasheet does not say whether the PHY pull-downs
   are active during reset. A downstream device that pulls D+ up without VBUS (non-compliant) at the moment of reset
   could disable its port until the next reset. Hub B cannot do this to port 7 because of s5.3.
3. In strap mode, whether the 2517 LED pins toggle is ambiguous (p11 vs CFG3 p25). It does not matter with no LEDs
   attached, but straps must be fitted on every LED_A and LED_B1-B3 pin, or that port's polarity, boost or gang mode
   becomes random.
4. The SY6863 datasheet is Rev 0.9 (preliminary). It does not give the EN input current or OCB behaviour while IN
   is unpowered.
5. Supervisor threshold 2.87-2.99 V is slightly under the hubs' 3.0 V minimum (s5.1).
6. The crystal's pinout and parameters are from the LCSC listing; its datasheet has not been read.
7. The TPS3809 datasheet is not in `docs/datasheets/` yet.

Bench checks (first assembled board):

| # | Check | Pass |
|---|---|---|
| B1 | `lsusb -v` on both hubs (0424:2517, 0424:2514): wHubCharacteristics | "Per-port power switching", "Per-port overcurrent protection", "TT per port"; bmAttributes self-powered; bDeviceProtocol 2 (MTT) |
| B2 | `uhubctl` lists both hubs; `uhubctl -l <A> -p n -a cycle` for n = 1-6 and `-l <A>.7 -p n` for n = 1-4 | only that port's VBUS and LED go off and come back; the others stay up |
| B3 | Every port, every C orientation: HS device (flash drive) and FS/LS device (keyboard) | all enumerate at the right speed (confirms PRT_SWP and PRT_DIS straps read 0) |
| B4 | 5 V-only brick (5V_BUS off, 3V3 on) and the first second after power-up: scope HUBA_OCS1_N and check `dmesg` | no over-current reports. If there are, the SY6863 pulls OCB low when unpowered; decide whether to accept it or gate it |
| B5 | Scope 3V3 and HUB_RESET_N at power-up | RESET_N rises 120-280 ms after 3V3 crosses ~2.97 V; no glitch high during the ramp |
| B6 | Host plugged in, no PD brick: 3V3 rail and HUBA_VBUS_DET | 3V3 < 0.3 V (no back-powering), VBUS_DET <= 2.75 V; nothing enumerates |
| B7 | Host unplugged/replugged with the PD brick on: HUBA_VBUS_DET 0 V / 2.2-2.75 V | hub detaches and re-attaches |
| B8 | `uhubctl -l <A> -p 7 -a cycle` | hub B disconnects and re-enumerates, P7-P10 VBUS off then back on (s5.3) |
| B9 | Short one port through a >4 A load | only that port reports over-current (SY6863 OCB after 15 ms, p4; hub OC_TIMER 8 ms), the others keep running |
| B10 | USB2517 case temperature with 7 HS ports busy, lid on | < ~85 C case |
| B11 | Strap voltages with RESET_N held low (short HUB_RESET_N to GND at its test point) | all 47 k straps < 0.5 V |

## 10. Decisions for the user

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | Hub B on hub A port 7 cannot be strapped "non-removable" | (a) keep port 7, all ports removable (no functional effect); (b) move hub B to hub A port 1 and strap NON_REM = 01 (correct compound-device descriptor, user ports become hub A 2-7) | (a): keeps the agreed port 7 architecture |
| D2 | Battery charging on hub B ports | off / on (needs pull-up instead of pull-down per port) | Off (s4.3) |
| D3 | Hub B VBUS_DET | hub A PRTPWR7 (fitted 0R, DNP 3V3 fallback) / tie to 3V3 | PRTPWR7 (s5.3) |
| D4 | Hub reset source | TPS3809K33 supervisor (+1 Extended part) / RC (outside the hubs' rise-time rule with a 5 ms 3V3 ramp) | Supervisor |
| D5 | Hub LEDs | none (straps only) / add one "HOST" LED on hub A SUSP_IND or HS_IND (LED + 1 k in parallel with the strap) | None per port; HOST LED optional, your call |
| D6 | Requirements s4 lists a tentative 1V2 rail | drop it (both hubs regulate internally) | Drop |


## Capture notes (schematic capture, 2026-11-16)

- **OCS inputs typed passive in the hub symbols**: OCSn_N have a 35-90 uA internal pull-up (2517 p12) and are driven
  only by the switches' open-drain OCB; KiCad ERC does not count open-collector pins as drivers.
- **Hub A port 7 -> hub B upstream** is drawn as labels HUBA_DN7_DP / HUBA_DN7_DM so the pair gets the USB net class.
- **USB2514B CRFILT / PLLFILT** caps (C68, C69) drawn on the left side with the straps (pin table p14).
- **Crystal pinout**: X322524MOB4SI pins 1/3 = crystal, 2/4 = GND, checked symbol vs. JLC footprint with
  fpcheck.py; the YXC datasheet itself was not read (LCSC listing only).
- **TPD4E05U06 (U7) NC pins 6, 7, 9, 10 floating**: "Can be left floating or grounded" (TPD4E05U06 p4).
- **HOST D+/D-** reach the hub through labels on both sides of U7 (no crossing wires); electrically identical.
