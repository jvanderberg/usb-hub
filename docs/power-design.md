# Power design notes

Status: 5 V stage parts chosen (2026-11-16); PD sink + 3V3 in docs/power-design-pd-3v3.md. Requirements: `docs/requirements.md` s4.

## 5V_BUS converter: LM5148 synchronous buck controller

### WEBENCH run (2026-11-16, logged in as the user)

Inputs: Vin 8.5-21 V, Vout 5.1 V, Iout 17 A, ambient 50 C, ceramic capacitors, shielded inductors, Balanced.
38 designs returned, all controllers or 20 A converters. The integrated LM654B0-Q1 (20 A, 266 mm2, 15 parts) has
no LCSC global stock (LM654 / PLM65460 variants: 0, 2026-11-16), so it is out.

Gate of the WEBENCH list (LCSC global, 2026-11-16): LM5148RGYR C7470701 51,164 ($0.92, ACTIVE); LM5149 6,018;
LM5146 5,471; LM25148 1,584; LM5145 0 (cn 30,000 does not count); LM25145 58; LM25149 33; TPS53819A 1,484
(PMBus, 3x3); LM5117 1,406. **LM5148 chosen**: cheapest, most stock, precise EN/UVLO, shunt current sense.

WEBENCH's default LM5148 design ran at 2.08 MHz (92.7 %). Customised to **405 kHz** (User Preferred Frequency 0.4 MHz):

| Item | WEBENCH value | Note |
|---|---|---|
| Efficiency at 21 V, 17 A | 96.6 % | Total loss 3.03 W |
| Duty cycle | 24.7 % | at 21 V |
| Rt | 53.6 k | 405.7 kHz |
| Rconfig (CNFG) | 40.2 k | |
| L1 | 1.5 uH, 1.6 mOhm, Coilcraft XAL1010-152MEB (IDC 36.6 A) | ripple 6.39 A p-p (37.6 %) at 21 V; L loss 0.47 W |
| Peak switch current | 20.2 A | inductor Isat must exceed the current limit, not this |
| M1 (high side) | CSD17553Q5A, 1.26 W (0.76 sw + 0.50 cond), Tj 113 C | not stocked at LCSC global -> substitute (CSD17578Q5A 6,460 / CSD17577Q5A 836) and re-check losses |
| M2 (low side) | CSD17573Q5B, 0.77 W, Tj 88.5 C | C202231, 1,179 in stock |
| Rsense | 2.451 mOhm | current limit: see below |
| Cin | 4x 10 uF 50 V X7R 1210 (26 uF derated) | Cin RMS 7.39 A; Vin ripple 306 mV p-p |
| Cout | 160 uF derated ceramic (custom) | Cout RMS 1.84 A; Vout ripple 12.4 mV p-p |
| Compensation | Rcomp 5.23 k, Ccomp 5.1 nF, Ccomp2 110 pF | phase margin 61 deg, crossover 38.9 kHz, gain margin -13.3 dB |
| FB divider | ~~53.6 k~~ **54.9 k** / 10 k | WEBENCH: 53.6 k, Vout 5.09 V, tolerance 2.97 %. Changed to 54.9 k (C11626) by user decision 2026-11-17 (review D3): Vout 5.19 V nominal, 5.07-5.33 V worst case (VREF 795-808 mV, 1 % resistors), below the SY6863 OVP (5.6 V typ, p4); port VBUS at 3 A worst case 4.81 V (was 4.71 V). The divider ratio changes loop gain by 2 % (5.09/5.19): negligible against 61 deg phase margin |
| Cvcc / Cvdda / Cboot | 2.2 uF / 100 nF / 100 nF | |
| Load step | 8.5 A step: -121 mV / +67 mV | |
| IC | Pd 0.52 W, Tj 68 C (theta-JA eff. 34.8 C/W assumed) | |
| Input current avg | 4.27 A at 21 V | |

To do: substitute stocked FETs/inductor/capacitors with equal or better ratings and re-run Operating Values; check at
Vin 8.5 V; current-limit tolerance (LM5148 ISNS threshold 60 mV, 49-73 mV per datasheet p8, from the candidate
research) -> with 2.45 mOhm the peak limit is ~20-30 A; decide where to sit it relative to the 100 W brick.

### Current limit (LM5148 datasheet: VCS-TH 49 / 60 / 73 mV, ISNS+ to VOUT, cycle-by-cycle peak; hiccup after 512 cycles, restart after 16384 cycles)

With Rsense 2.45 mOhm: peak limit 20.0 / 24.5 / 29.8 A (min/typ/max). DC output limit = peak - ripple/2 (3.2 A at
21 V): **~16.8 / 21.3 / 26.6 A**. Min guarantees the 17 A design load; typical (~109 W at 5.1 V) is above what a
100 W brick supplies, so in the typical part the brick, not the converter, trips first on a 100 W brick (whole-hub
reset, as accepted). Inductor Isat must exceed the max peak (~30 A + propagation-delay overshoot). Overload
behaviour: ~1.3 ms of current limiting, then off ~40 ms, then soft-start retry (hiccup).

### Parts chosen (stock: LCSC global, 2026-11-16; need 6 = 5 boards + 10 %)

| Function | Part | LCSC | Stock | Why |
|---|---|---|---|---|
| Controller | TI LM5148RGYR | C7470701 | 51,154 | WEBENCH design |
| M1 high side | TI CSD17505Q5A | C553150 | 2,752 | WEBENCH alternate: 1.43 W, Tj 121 C at 21 V/17 A/50 C (WEBENCH's CSD17553Q5A: 0 stock; CSD17306Q5A/CSD17305Q5A: 0 global; CSD17578Q5A not offered by WEBENCH). Genuine TI only, no "-TP/-HXY/(ES)" second-source clones |
| M2 low side | TI CSD17573Q5B | C202231 | 1,179 | WEBENCH pick |
| L1 | Coilcraft XAL1010-152MED, 1.5 uH | C6753479 | 154 | WEBENCH pick (MEB suffix = obsolete reel code). DCR 1.60/1.76 mOhm, Isat 36.6 A (30 % drop, 25 C), Irms 31 A (20 C rise) - datasheet Doc 804-1 p1 (docs/datasheets/XAL1010.pdf, rev 09/08/15 copy) |
| Rsense | 2.5 mOhm 1 % 3 W 2512 (Milliohm HoJLR2512-3W-2.5mR-1%) | C2904234 | 13,073 | nearest stocked to WEBENCH's 2.45 mOhm |
| Cin | 4x 10 uF 50 V X7R 1210, Samsung CL32B106KBJNNNE | C138687 | 135,974 | as WEBENCH (4x C3225X7R1H106); RMS 8.3 A at 8.5 V, 7.4 A at 21 V shared by 4 |
| Cout | 8x 47 uF 10 V X5R 1210, Samsung CL32A476KPJNNNE | C525654 | 6,037 | WEBENCH asks 160 uF derated; ~21 uF each at 5.1 V (est. -55 % DC bias) -> ~170 uF. 10 V rating for 2x margin over 5.1 V |

Current limit with 2.5 mOhm (VCS-TH 49/60/73 mV): peak 19.6 / 24.0 / 29.2 A; DC output ~16.4 / 20.8 / 26.0 A at
21 V (ripple 6.39 A p-p), more at lower Vin (ripple 3.3 A at 8.5 V). Inductor Isat 36.6 A > 29.2 A max peak.

WEBENCH with CSD17505Q5A + CSD17573Q5B (17 A out, 50 C ambient):

| Vin | Eff | Total Pd | M1 Pd / Tj | M2 Pd / Tj | L ripple | Peak | Cin RMS | Phase margin |
|---|---|---|---|---|---|---|---|---|
| 21 V | 96.5 % | 3.16 W | 1.43 W / 121 C | 0.77 W / 88 C | 6.39 A | 20.2 A | 7.39 A | 61.3 deg |
| 8.5 V | 97.0 % | 2.69 W | 1.59 W / 130 C | 0.43 W / 72 C | 3.28 A | 18.6 A | 8.31 A | 61.0 deg |

(8.5 V at 17 A is not reachable in practice: a 9 V PD contract is at most 3 A, ~25 W.) WEBENCH's theta-JA is its
own board; the board-review heat model decides the real FET temperature.

### EN / UVLO divider (LM5148 datasheet s8.3.3, Eq. 2-3; VEN 0.95/1.0/1.05 V, IHYS 8/10/12 uA, p6 table)

Target: on at 7.5 V, off at 6.5 V (a 5 V-only source, <= 5.5 V, never enables; a 9 V contract arrives >= ~8.2 V
after cable drop).
- RUV1 = (VIN(on) - VIN(off)) / IHYS = 1.0 V / 10 uA = 100 k
- RUV2 = RUV1 x VEN / (VIN(on) - VEN) = 100 k x 1 / 6.5 = 15.38 k -> **15.4 k** (E96)
- With 100 k / 15.4 k: VIN(on) = 1.0 x (1 + 100/15.4) = 7.49 V (7.12-7.87 V over VEN tolerance);
  VIN(off) = VIN(on) - IHYS x RUV1 = 6.49 V (hysteresis 0.8-1.2 V).
- EN abs max 80 V: fine at 21 V.

The requirements' "PD sink power-good enables the buck" is replaced by this divider: the TPS25730 has no
power-good pin (docs/power-design-pd-3v3.md).


## Capture notes (schematic capture, 2026-11-16)

Decisions taken while drawing hw/buck_5v.kicad_sch where this document was silent or the sources disagreed:

- **CNFG = 41.2 k (C26978)**, not WEBENCH's 40.2 k: LM5148 Table 8-2 (p24) bins CNFG by resistor; 41.2 k is the
  "primary, DRSS spread spectrum on" value that Fig 9-17 (p42) also uses. 40.2 k sits at a bin edge.
- **VCCX tied to AGND** (internal VCC regulator). VCCX = VOUT would save VCC LDO loss, but "VIN must be greater than
  the external bias" (p17) and a PD source can sag or drop out while Cout still holds 5V_BUS. Fig 9-17 (p42) allows
  "Tie to VOUT or GND".
- **PFM/SYNC tied to VDDA**: diode-emulation (PFM) at light load (pin table p4); the hub idles at a few hundred mA.
- **PG: 100 k pull-up to VDDA** (p17 "100 kOhm typical to the relevant logic rail") + test pad TP31. Since
  2026-11-18 PG (net BUCK_PG) also drives U8's OVLO pin: buck regulating = host path off ("Host-powered mode" below).
- **NC pins 1, 2, 22-24 to GND at the exposed pad** (pin table p3-4); drawn as hidden pins of the AGND/EP pin.
- **Rcomp 5.23 k = FOJAN FRC0402F5231TS (C2933105)**: the UNI-ROYAL 5.23 k had only 4 in stock.
- **Kelvin sense**: ISNS+ from the L30/R30 node (net 5V_ISNS), VOUT from the R30 output end (p4).
- **Net classes**: HighCurrent = 5V_SW and 5V_ISNS, clearance 0.2 mm (the LM5148 QFN pads SW/CBOOT and
  EN/ISNS+/VOUT are 0.22 mm apart; 0.3 mm would fail DRC at the IC). VIN and 5V_BUS are in the Power class.

## Host-powered mode (U8 TPS259470ARPWR, 2026-11-18)

User request 2026-11-18: with no PD brick the hub should still enumerate and pass data from the host's VBUS. U8, an
eFuse with true reverse-current blocking, feeds HOST_VBUS onto 5V_BUS while the LM5148 is not regulating; D41 feeds
VIN (the TPS54202 3V3 buck) back from 5V_BUS. Hub sheet (hw/hubs.kicad_sch); on the board U8 sits south-east of
the HOST receptacle, its footprint corrected to TI's land pattern (tools/land_fp.py).
Datasheet: docs/datasheets/TPS25947.pdf (SLVSFC9C, May 2026); lifecycle ACTIVE (ti.com, 2026-11-18).

### Behaviour

| Source on PWR IN | Host | VIN | LM5148 / BUCK_PG | U8 | 5V_BUS | 3V3 |
|---|---|---|---|---|---|---|
| none | yes | 5V_BUS - D41 (~4.5 V) | EN 0.60 V < 1.0 V: off, PG low | on | host, <= 1.78 A | TPS54202 from VIN via D41 |
| 5 V-only brick | yes | 5 V (brick) | off (< 7.5 V), PG low | on | host, <= 1.78 A | TPS54202 from the brick |
| 5 V-only brick | no | 5 V | off, PG low | off (no IN) | dark, "low power" LED (as before) | from the brick |
| PD >= 9 V | either | 9-20 V | regulating, PG released (Hi-Z, 100 k to VDDA) | off: OVLO = VDDA 5 V > 1.20 V | buck 5.19 V | TPS54202 from VIN |
| PD >= 9 V, soft start / hiccup | yes | 9-20 V | PG low | on | host assists (<= 1.78 A) until PG | TPS54202 from VIN |

Hand-over: a host's VBUS may be anywhere in 4.75-5.25 V, i.e. above the buck's 5.19 V, so U8's reverse
comparator (VREVTH -29.3 mV, p10) cannot be relied on to hand over and is only the backstop; OVLO from BUCK_PG is
what turns U8 off (tOVLO 1.2 us, p11). In the
OVLO state IN draws IQ(OVLO) 190 / 267 uA from the host (p9) and OUT sinks IOUTLKG(OVLO) 319 / 443 uA from 5V_BUS to
GND (p9): nothing flows from 5V_BUS to the host. With no host attached and a brick up, U8 is unpowered and leaks
IREVLKG(OFF) 4.86 uA typ (no max given, p10) out of OUT; if it all came out of IN, the two HOST_VBUS dividers
(R64 + R65 200 k parallel R79 + R80 147 k = 84.7 k) sit at 0.41 V and VBUS_DET at 0.21 V: low (bench check 3).

In host mode the ports are powered too (the hubs drive PRTPWR as usual), from the host's budget: the hub itself
takes ~0.5 A at 5 V (3V3 0.635 A max via the TPS54202 at ~94 %, s4.3 of power-design-pd-3v3.md), leaving ~1.3 A of
U8's limit for devices. A host port that supplies less (a 500 / 900 mA USB-A port, a Type-C default-power port)
trips or sags with its own protection when devices draw more: the same accepted overload behaviour as on the brick
(requirements s4), with the host's limiter in place of the converter's.

### Values (TPS25947 SLVSFC9C; page numbers of the PDF)

| Item | Equation (page) | Result | Part |
|---|---|---|---|
| EN/UVLO divider | VIN(on) = VUVLO(R) x (1 + R79/R80), VUVLO(R) 1.183 / 1.20 / 1.223 V, VUVLO(F) 1.076 / 1.09 / 1.116 V (p9) | 100 k / 47 k: **on 3.75 V** (3.70-3.83 V), **off 3.41 V** (3.37-3.49 V); any host >= vSafe5V min 4.75 V enables it, the ~0.4 V leakage level never does. EN abs max 6.5 V: 1.76 V at 5.5 V | R79 C25741 100 k, R80 C25792 47 k |
| OVLO | OVLO = BUCK_PG: LM5148 PG, open drain, R38 100 k to VDDA. VOV(R) 1.20 V, VOV(F) 1.09 V (p9); OVLO abs max 6.5 V | buck regulating: 5 V on OVLO, U8 off; buck off, standby or soft start: PG low, U8 on | (R38 existing) |
| Current limit | RILM = 3334 / ILIM (Eq 5, p30); ILIM 1.800 / 2.028 / 2.200 A at RILM 1.65 k (p9) | 1.87 k: **1.78 A** (1.58-1.93 A scaled from the p9 row). Active current limit (TPS259470x, p31), thermal shutdown at 154 C, auto-retry after 110 ms (TPS25947xA, tRST p11) | R81 C270633 1.87 k 1 % |
| Inrush (dVdt) | CdVdt (pF) = 2000 / SR (V/ms) (Eq 4, p29) | 10 nF: **0.2 V/ms**, 0 -> 5 V in 25 ms. Load charged: 477 uF nominal on 5V_BUS + 82 uF on VIN through D41 = 559 uF -> **0.11 A** inrush from the host (well under a 500 mA port; USB inrush limit). FET energy ~ 0.11 A x 2.5 V avg x 25 ms = 7 mJ | C75 C15195 10 nF |
| Overcurrent blanking (ITIMER) | tITIMER = dVITIMER x CITIMER / IITIMER (Eq 6, p30); dVITIMER 1.286 / 1.51 / 1.741 V, IITIMER 1.2 / 1.8 / 2.5 uA (p10) | 5.1 nF: **4.3 ms** (2.6-7.4 ms): a device's plug-in inrush through its SY6863 passes; a sustained overload is then current-limited. Pin rating 4 V (p8): 50 V part | C76 C47118429 5.1 nF |
| Output cap | TI layout guidance (s8.4.1): >= 1 uF at OUT | C77 1 uF at the OUT column | C77 C52923 1 uF / 25 V |
| Input cap | TI layout guidelines (p62): >= 0.1 uF closest to IN / GND | C78 100 nF on the IN trunk (C74 1 uF stays at the receptacle TVS, 7.4 mm away) | C78 C1525 100 nF / 16 V |
| VIN feed (D41) | SS34 VF ~0.40 V at 0.5 A typ (Fig 3, SS34 p2); VR 40 V vs VIN 21 V + the 28 V TVS clamp | VIN = HOST_VBUS - cable - U8 - D41: 5.0 V host: 5.0 - 0.06 - 0.02 - 0.40 = **~4.5 V**; 4.75 V host: **~4.27 V**. Loss 0.2 W | D41 C8678 SS34 (SMA) |
| D41 leakage bleed | IR 0.5 mA max at 40 V, 25 C (SS34 p1); typ ~1.5 uA at 20 V, 25 C and ~0.6 mA at 100 C (Fig 2) | In brick mode D41 is reverse biased by up to 15 V; the LM5148 in diode emulation cannot sink that leakage at no load. 2.2 k holds 5V_BUS: 5.19 V / 2.2 k = **2.4 mA**, 12 mW; 0.6 mA x 2.2 k = 1.3 V with the buck off | R83 C25879 2.2 k |

**Risk (bench check 1): the 3V3 buck from a weak host.** The TPS54202 starts at UVLO rising 3.9 / 4.2 / 4.4 V and
its recommended minimum is 4.5 V (power-design-pd-3v3.md s4.2); once running it regulates down to ~3.5 V in (100 %
duty). A 5.0 V host gives ~4.5 V: starts at a typical UVLO. A host at the 4.75 V vSafe5V minimum gives ~4.27 V:
below the 4.4 V UVLO maximum, so a worst-case part may not start and the hub stays off in host-only mode (brick
operation is unaffected). A lower-VF Schottky gains < 0.1 V; the full fix is the TPS62933 alternative (runs to
~3.8 V, user decision D2 in power-design-pd-3v3.md) - the user's call if the bench shows it.

**LM5148 in host mode:** VIN ~4.5 V on its 100 k / 15.4 k EN divider gives EN 0.60 V: below VEN 0.95 V (off), above
the 0.5 V shutdown level, so VCC may come up in standby (a few mA from VIN) with PG low. Either state keeps BUCK_PG
low, which is all U8 needs (bench check 2).

### Bench checks

1. Host only, no brick: 3V3 starts from a 5.0 V host and from a bench supply on HOST at 4.75 V; record VIN.
2. Host only: LM5148 EN / VCC / PG levels; BUCK_PG low; U8 on.
3. Brick only (>= 9 V), no host: HOST_VBUS and HUBA_VBUS_DET (expect < 0.5 V); the hub does not attach.
4. Host first, then the brick: 5V_BUS hand-over without a hub reset (BUCK_PG high, U8 off); brick removed: U8
   takes 5V_BUS back (VIN drops to the D41 feed, 3V3 may brown out: note whether the hubs re-enumerate).
5. Brick mode, no port load, warm board: 5V_BUS stays at 5.19 V (D41 leakage vs the R83 bleed).
6. Host only: overload a port: U8 current-limits at ~1.78 A or the host port trips; recovery after removal.
