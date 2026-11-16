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
| FB divider | 53.6 k / 10 k | Vout actual 5.09 V, tolerance 2.97 % |
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
