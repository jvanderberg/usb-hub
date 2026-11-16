# Power design notes

Status: in progress (2026-11-16). Requirements: `docs/requirements.md` s4.

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
