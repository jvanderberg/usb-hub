# Power design: PD input (TPS25730D) and 3V3 rail (TPS54202)

Status: draft for review (2026-11-16). Not yet approved by the user. Requirements: `docs/requirements.md` s3, s4, s8, s10.
Companion to `docs/power-design.md` (5V_BUS / LM5148), which this file does not change.

Datasheets used (all in `docs/datasheets/`; page = printed page number of that PDF):

| Ref used below | Document |
|---|---|
| TPS25730 | TI TPS25730, SLVSGP9 (Oct 2023), `TPS25730.pdf` |
| SDAA265 | TI app note "TPS257xx/TPS267xx Autonegotiate Sink Configuration", SDAA265 (Apr 2026), `SDAA265_TPS257xx_autonegotiate_sink.pdf` (added) |
| TVS2200 | TI TVS2200, SLVSED5C (Aug 2023), `TVS2200.pdf` |
| ESTVS2200 | ElecSuper ESTVS2200DRVR Rev-1.1, `ESTVS2200DRVR.pdf` (added; from LCSC C42400188) |
| PESD24VS1UL | Nexperia PESD24VS1UL product data sheet, 2 May 2024, `PESD24VS1UL.pdf` (added; from LCSC C477994) |
| TPS54202 | TI TPS54202, SLVSD26C (Feb 2026), `TPS54202.pdf` |
| TPS62933 | TI TPS62933, SLUSEA4D (Aug 2022), `TPS62933.pdf` |
| FXL0630 | Cjiang FXL series catalogue, `FXL0630-100-M.pdf` (added; from LCSC C167223; PDF pages 14 and 27) |

All stock figures: LCSC **global** warehouse, 2026-11-16, via `sourcing.py stock` / `search` (project `sourcing.json`:
JLCPCB, 5 boards, 10 % attrition). "Need" = qty per board x 5 x 1.1, rounded up. Lifecycle (TI product pages via
`part_gate.py`, 2026-11-16): TPS25730DREFR ACTIVE, TPS54202DDCR ACTIVE.

---

## 1. TPS25730DREFR PD sink

### 1.1 Configuration chosen

| Setting | Value | Why |
|---|---|---|
| Minimum voltage | 9 V (ADCIN1 = 1) | Requirement: lowest supported contract is 9 V (requirements s4) |
| Maximum voltage | 20 V (ADCIN2 = 7) | Highest SPR fixed voltage the part supports (Table 8-5, p36) |
| Operating current | 1 A (ADCIN3 = 1) | Capability Mismatch is set when the source cannot meet the *Operating* current (p36 s8.3.13); 1 A keeps the mismatch flag meaning "below 9 V / below 9 W" and not "brick offers less than 5 A". Min power = 1 A x 9 V = 9 W (s8.3.14, p37) |
| Maximum current | 5 A (ADCIN4 = 3) | 100 W brick + 5 A cable; ADCIN3/ADCIN4 = 1/3 -> 1 A / 5 A (Table 8-6, p37) |
| Dead-battery behaviour | AlwaysEnableSink | Every ADCIN1/ADCIN2 combination in Table 8-3 (p35) is AlwaysEnableSink; ADCIN1=1, ADCIN2=7 is a listed row |
| I2C target address | 0x21 | Table 8-3 (p35), row ADCIN1=1 / ADCIN2=7 |

### 1.2 Strap table (ADCINx dividers from LDO_3V3 to GND)

Decoding windows from Table 8-1 (p31): DIV = R_DOWN / (R_UP + R_DOWN). ADCIN pins: abs max 4 V (p8), leakage
+/-1 uA (p17), ADC gain error +/-2.7 % and offset +/-4.1 mV (p16-17), read 10 ms after LDO_3V3 rises (tBOOT, p17).

Worst-case DIV below = 1 % resistors at opposite extremes, then x(1 -/+ 2.7 %) gain error, -/+ leakage x R_thevenin /
3.0 V (lowest LDO_3V3, p12), -/+ 4.1 mV / 3.0 V offset. All four land well inside their windows.

| Pin | Decoded value -> meaning | Window (Table 8-1, p31) | R_UP (LDO_3V3 side) | R_DOWN (GND side) | DIV nominal | DIV with 1 % tolerance | DIV worst incl. ADC error and leakage |
|---|---|---|---|---|---|---|---|
| ADCIN1 (pin 2) | 1 -> min 9 V (Table 8-4, p36) | 0.0229 - 0.0722 (target 0.0475) | 200 k | 10.0 k | 0.04762 | 0.04672 - 0.04853 | 0.0409 - 0.0544 |
| ADCIN2 (pin 3) | 7 -> max 20 V (Table 8-5, p36) | 0.9061 - 1.0 ("tie to LDO_3V3") | **tie directly to LDO_3V3** | none | 1.000 | - | 1.000 |
| ADCIN3 (pin 5) | 1 -> operating 1 A (Table 8-6, p36-37) | 0.0229 - 0.0722 | 200 k | 10.0 k | 0.04762 | 0.04672 - 0.04853 | 0.0409 - 0.0544 |
| ADCIN4 (pin 7) | 3 -> maximum 5 A (with ADCIN3 = 1) | 0.1425 - 0.2372 (target 0.1899) | 200 k | 47.0 k | 0.19028 | 0.18722 - 0.19338 | 0.1681 - 0.2127 |

E96 note: 200 k and 10.0 k are E96. 47.0 k is an E24 value (Basic part, 1 %); the E96 neighbour 47.5 k (DIV 0.19192,
worst 0.1696 - 0.2145) also works but is an Extended part (C25896, 21,857). The 47.0 k is recommended. Divider load on
LDO_3V3: 3 x 3.4 V / 210-247 k = ~45 uA, against the 5 mA allowed from LDO_3V3 (p9).

Cross-check against TI's own example (Fig 9-3, p42, "20 V at 3 A"): ADCIN1 2.28 k / 198.2 k -> 0.0114 (0 = 5 V);
ADCIN2 191 k / 9.4 k -> 0.953 (7 = 20 V); ADCIN3 38 k / 162 k -> 0.19 (3); ADCIN4 9.5 k / 190 k -> 0.0476 (1) -> 3 A / 3 A.
Our encoding follows the same tables.

### 1.3 Pin-by-pin connections and external parts (TPS25730D pin table p5-6, typical application Fig 9-3 p42)

| Pin(s) | Connection | Part | Value | LCSC | Stock (global, 2026-11-16) | Qty/board | Source |
|---|---|---|---|---|---|---|---|
| - | PD sink IC | TI TPS25730DREFR, WQFN-38 4x6 | - | C22438973 (Ext) | 1,018 (need 6) | 1 | |
| VBUS_IN 23-25, VBUS 32-33 | Shorted together to receptacle VBUS (all 4 VBUS pins of USB4105) | - | - | - | - | - | p9 note 2: "All VBUS and VBUS_IN pins be shorted together" |
| VBUS | C_VBUS bulk | FH 1206B475K500NT, X7R 1206 50 V | 4.7 uF | C29823 (**Basic**) | 546,660 | 1 | C_VBUS 1 / 4.7 / 10 uF min/nom/max, 25 V rating (Table 6.4, p10); Fig 9-3 C1 |
| VBUS | HF decoupling | Samsung CL05B103KB5NNNC, X7R 0402 50 V | 10 nF | C15195 (Basic) | 5,896,899 | 4 | Fig 9-3 C2-C5 (p42) |
| VBUS | Surge TVS | ElecSuper ESTVS2200DRVR | - | C42400188 (Ext) | 10,606 | 1 | s3 below |
| VBUS | Reverse/ground-current Schottky, cathode to VBUS, anode to GND | MDD SS34, 40 V 3 A, SMA | - | C8678 (Basic) | 2,650,914 | 1 | p39 s8.5, Fig 8-27 (p40): "TI recommends that a Schottky diode be placed from VBUS to ground" |
| PPHV 20-22 | VIN rail (feeds LM5148 and TPS54202) | - | - | - | - | - | C_PPHV nom 47 uF, **max 100 uF** (p10); budget in s5 |
| PPHV | Local cap at the pins | Samsung CL32B106KBJNNNE, X7R 1210 50 V | 10 uF | C138687 (Ext, same part as LM5148 C_IN) | 135,974 | 1 | p47-48: nominal capacitance "placed on the board as close to the pin as possible" |
| LDO_3V3 1 | C_LDO_3V3 | Samsung CL21A106KAYNNNE, X5R 0805 25 V | 10 uF | C15850 (Basic) | 8,910,590 | 1 | 5 / 10 / 25 uF, 6.3 V (p10); Fig 9-3 C12 |
| LDO_1V5 4 | C_LDO_1V5 | CL21A106KAYNNNE | 10 uF | C15850 (Basic) | (above) | 1 | 4.5 min / 12 max uF, 4 V (p10). 10 uF chosen instead of TI's 4.7 uF so tolerance + bias cannot drop it below 4.5 uF; +10 % = 11 uF < 12 uF max |
| VIN_3V3 38 | **Not connected to the 3V3 rail**; C_VIN_3V3 only | CL21A106KAYNNNE | 10 uF | C15850 (Basic) | (above) | 1 | 5 / 10 uF (p9). See 2.4: keeps every boot a dead-battery (VBUS-powered) boot. Optional DNP 0R to 3V3 for experiments |
| CC1 28, CC2 29 | To receptacle CC1 (A5) / CC2 (B5) | - | - | - | - | - | Rd is internal (p24, Fig 8-3) |
| CC1, CC2 | C_CCy to GND, same layer, no via between pin and cap (p49) | Samsung CL10C331JB8NNNC, C0G 0603 50 V | 330 pF | C1664 (**Basic**) | 855,022 (search 2026-11-16) | 2 | 200 / 400 / 480 pF incl. all external capacitance (p10); Fig 9-3 C9/C10 330 pF. 50 V rating because CC tolerates 26 V (short-to-VBUS) (p8) |
| CC1, CC2 | ESD diode at the receptacle | Nexperia PESD24VS1UL,315, SOD-882 | - | C477994 (Ext) | 128,999 | 2 | s3 below. Total C_CC = 330 pF + 23 pF typ / 50 pF max = 353-380 pF, inside 200-480 pF |
| ADCIN1 2 | Divider | UNI-ROYAL 0402WGF2003TCE / 0402WGF1002TCE | 200 k / 10.0 k | C25764 / C25744 (Basic) | 3,449,977 / 20,604,878 | 1 / 1 | 1.2 |
| ADCIN2 3 | Direct to LDO_3V3 | - | - | - | - | - | Table 8-1 "tie to LDO_3V3" = 7 |
| ADCIN3 5 | Divider | 0402WGF2003TCE / 0402WGF1002TCE | 200 k / 10.0 k | C25764 / C25744 | (above) | 1 / 1 | 1.2 |
| ADCIN4 7 | Divider | 0402WGF2003TCE / 0402WGF4702TCE | 200 k / 47.0 k | C25764 / C25792 (Basic) | 5,608,712 (47 k) | 1 / 1 | 1.2 |
| RESERVED 26, 27, 36 | 10 k to GND each | 0402WGF1002TCE | 10 k | C25744 | (above) | 3 | Pin table "Tie to ground or LDO_3V3" (p5); Fig 9-3 uses 10 k to GND (R9, R10, R?) |
| I2Ct_SCL 9, I2Ct_SDA 8 | 3.3 k pull-ups to LDO_3V3 + two test pads (bring-up: read contract/status over I2C at 0x21) | 0402WGF3301TCE | 3.3 k | C25890 (Basic) | 1,122,059 | 2 | p5 ("may be grounded if unused"); Fig 9-3 R1/R2 3.3 k. 1 mA per line only while a tool pulls it low; within the 5 mA LDO_3V3 budget (p9) |
| FAULT_IN 18 | 10 k pull-up to LDO_3V3 (1 = keep connection) | 0402WGF1002TCE | 10 k | C25744 | (above) | 1 | p5: "0: Disconnect from port, 1: Maintain connection"; input VIH 1.3 V (p17) |
| SINK_EN 19, CAP_MIS 6, PLUG_EVENT 37 | Open-drain outputs: test pads (CAP_MIS optionally to the "low power" LED, s2.5) | - | - | - | - | - | p5; GPIO 0-5.5 V (p9), VOL 0.4 V at 2 mA (p17), abs max 6 V (p8) |
| PLUG_FLIP 13, DBG_ACC 10 | Leave unconnected (open-drain outputs, no use) | - | - | - | - | - | p5 |
| GND 11, 12, 14, 16, 17, 31, 34, 35 + GND pad 39 | GND plane, vias in pad | - | - | - | - | - | p5; RthJC(bot GND) 1.8 C/W (p11) |
| DRAIN 15, 30 + DRAIN pad 40 | Join on an **isolated top-layer copper island only**; no other net, no vias to other layers' nets | - | - | - | - | - | p6 "Connects to drain of internal FET"; p48 "drain connection pads ... must not be connected to anything and left floating". RthJC(bot DRAIN) 4.6 C/W (p11): island size helps heat |

Layout notes carried to the layout brief (p48-52): VBUS/VBUS_IN/PPHV pours on top, >= 15 x 0.2/0.4 mm vias for
VBUS_IN and PPHV, >= 6 for VBUS; CC traces >= 8 mil (10 mil recommended), CC cap on the same side as the IC with the via
after the cap; routing-width table 9-1 (p52).

Dissipation at 5 A: R_PPHV 16 / 19 mOhm at 25 C, 24 / 29 mOhm at 125 C (p12) -> P = 5^2 x 0.029 = 0.73 W worst.
With R_thetaJA 57.4 C/W (JEDEC board, p11): Tj ~ 50 C internal air + 42 C = ~92 C, below TJ_PPHV 150 C (p9). Current
rating 7 A at <= 45 C ambient, 6 A at <= 65 C (p9): 5 A is inside both.

---

## 2. Behaviour, LEDs and open risks

### 2.1 Which PDO is requested inside 9-20 V

- The TPS25730 datasheet does **not** state the selection rule. It says only that min/max voltage and operating
  current bound the request and set Capability Mismatch (s8.3.11-8.3.14, p35-37), and that min power = operating
  current x min voltage (p37).
- TI's family app note SDAA265 (TPS257xx/TPS267xx Autonegotiate Sink, p5 Table 2-1 bit 0): "The PD controller will find
  the set of PDO's that fulfill the voltage requirements. From that set of PDO's it will pick the one with higher
  power. If two acceptable PDO's have the same power, Fixed Supply Type is preferred ... then this bit determines which
  PDO is selected. 0h = Higher voltage" (default 0, p6). Example p6-7: 30 W source with 15 V/2 A and 20 V/1.5 A -> 20 V
  chosen. It also says the controller never requests more than its max current (p5, bits 21-12) and PPS is off by
  default (p4, bit 64).
- Expected result here (if the TPS25730 strap firmware uses the same Autonegotiate Sink engine, which the datasheet's
  section titles suggest but do not state): **highest-power fixed PDO between 9 and 20 V, ties go to the higher
  voltage**. With common bricks that is 20 V (65 W 20 V/3.25 A; 100 W 20 V/5 A; 45 W 20 V/2.25 A ties 15 V/3 A -> 20 V).
  A 20 W 9 V/2.22 A brick gives 9 V. Either way VIN is 9-20 V, which the LM5148 design covers.

### 2.2 5 V-only (or non-PD) source

- Dead-battery start with AlwaysEnableSink (Table 8-3, p35): "The device always enables the sink path regardless of
  the amount of current the attached source is offering." The board always starts this way because VIN_3V3 is not
  powered (s2.4).
- Evidence the path is on at 5 V before any contract: Fig 9-10 (p47) shows PPHV following VBUS from the 5 V step
  before the 20 V transition; Fig 9-8 (p45) shows SINK_EN low (path enabled) while CAP_MIS toggles (mismatch).
- With a 5 V-only PD source nothing in 9-20 V exists -> the request is 5 V with Capability Mismatch set (s8.3.11,
  p35), and per Fig 9-8 the sink path stays enabled. VIN = ~5 V, the 3V3 buck runs, the hubs enumerate.
- The 5 V buck must stay off: that is done by the LM5148 EN/UVLO divider (~8 V), not by the TPS25730. There is no
  "power good" pin on the TPS25730 (pin table p5-6). The block diagram in requirements s3 ("PD sink -> PG -> 5 V
  buck enable") should read "VIN -> LM5148 EN/UVLO divider".
- Caution: SDAA265 (p5 bit 6, p6 defaults) says the TPS257xx family default is AutoDisableSinkUponCapabilityMismatch = 1
  (path disabled on mismatch). The TPS25730 datasheet shows the opposite in Fig 9-8 and Table 8-3. Bench check 1
  below settles it.

### 2.3 Status pins and the two LEDs

| Pin | Meaning (p5) | Usable as |
|---|---|---|
| SINK_EN (19) | 0 = sink path enabled | Not "contract OK": it is low at 5 V before the contract too (AlwaysEnableSink, Fig 9-8 p45) |
| CAP_MIS (6) | "Toggled Output: Capability Mismatch"; Fig 9-8 (p45) shows a square wave, ~1 s high / ~1 s low (read from the 1 s grid) | "Low power" LED that **blinks** (LED from 3V3 through resistor into CAP_MIS). Not driven for a non-PD (Rp-only) 5 V source, because no PD request is made (not stated in the datasheet; inferred) |
| PLUG_EVENT (37) | 1 = connection present | Attach only |
| (none) | - | No pin says "PD contract OK" |

Recommendation (user decision D3): drive both LEDs from the rails, so they show what the user cares about (ports
powered or not) for every source type, PD or not:

| LED | Circuit | Current | Parts |
|---|---|---|---|
| "PD OK" (green) | 5V_BUS -> 1.5 k -> LED -> GND. Lit only when the LM5148 runs, i.e. contract >= 9 V | (5.1 - 2.0...3.0 V) / 1.5 k = 1.4-2.1 mA | KT-0603G C12624 (Ext, 220,269); 0402WGF1501TCE C25867 (Basic, 1,213,160) |
| "Low power" (red) | P-FET AO3401A: source = 3V3, gate = 5V_BUS (+ 100 k gate-to-GND so it is defined with the buck off), drain -> 1.0 k -> LED -> GND. On when 3V3 is up and 5V_BUS is not; off when 5V_BUS = 5.1 V (Vgs = +1.8 V) | (3.3 - 1.9) / 1.0 k = ~1.4 mA | AO3401A C15127 (Basic, 1,489,380); KT-0603R C2286 (Basic, 5,637,779); 0402WGF1001TCE C11702 (Basic); 0402WGF1003TCE C25741 (Basic) |

The red LED flashes for the ~0.5-1 s between attach and the 20 V contract on a good brick; that is expected.
Alternative (datasheet-defined, fewer parts): red LED + 1.0 k from 3V3 into CAP_MIS (blinks on mismatch, ~1.4 mA,
within the 2 mA VOL spec, p17), green LED as above. Misses non-PD 5 V sources.
LEDs must not hang off LDO_3V3 (5 mA total, p9).

### 2.4 VIN_3V3 left unpowered (decision taken here, flag if you disagree)

VIN_3V3 is the "optional" system 3.3 V input (Fig 9-1/9-2, p41). In a dead-battery boot the VIN_3V3 switch stays open
until a host clears the dead-battery flag over I2C (p27-28, s8.3.2), so feeding it from our 3V3 rail gains nothing.
It could also make a reboot during a PD hard reset (VBUS -> 0 V while 3V3 is still decaying) a non-dead-battery boot,
whose behaviour without a host the datasheet does not describe (AlwaysEnableSink is listed as the *dead battery*
configuration, Table 8-3). Leaving it at just C_VIN_3V3 keeps every boot identical. Footprint a DNP 0R to 3V3.

### 2.5 Open risks (none blocks schematic capture)

1. PDO selection rule comes from the family app note, not the TPS25730 datasheet (2.1).
2. ADCIN2 encoding: Table 8-5 (p36), Table 8-3 (p35) and Fig 9-3 (p42) say 7 = 20 V, but the examples in Table 8-7 and
   Table 8-8 (p37) use ADCIN2 = 4 / 6 for 15 V / 20 V. Three sources agree on 7; bench check 2 confirms.
3. "This functionality is firmware controlled and subject to change" (s8.3.6, p30).
4. Mismatch behaviour (2.2): the sink path is expected to stay enabled at 5 V; bench check 1.
5. Non-PD 5 V sources: CAP_MIS probably silent; the rail-based LED design covers it.
6. Capacitor DC-bias values in s5 are estimates (no curve in the Samsung LCSC spec sheet for C138687); confirm with
   Samsung's characteristic-data tool before freezing the bulk-cap value.
7. TVS: 28.0 V max clamp at 40 A (ESTVS2200 p3) equals the TPS25730 VBUS/PPHV abs max of 28 V (p8). The datasheet
   itself recommends this class (p8 note 4). Clone part (TI original: 2 in stock, s3).
8. 3V3 at 5 V input has 0.13 V margin to the TPS54202's 4.5 V minimum (s4.2).
9. A PD hard reset or brick overload drops VBUS and therefore the 3V3 rail too: the hubs reset with it. That is
   inherent to "3V3 from VIN" and matches the accepted overload behaviour (requirements s4).
10. LM5148 EN/UVLO (other block): turn-on must stay below the lowest 9 V contract after cable + TPS25730 drop at full
    load (~9 V x 0.95 - 3 A x ~0.2 Ohm = ~8.0 V). "~8 V" is right at that edge: check it in the LM5148 design.

Bench checks: (1) 5 V-only PD brick and a non-PD 5 V source: VIN ~5 V, 3V3 up, hubs enumerate, LM5148 off, red LED on;
(2) 100 W brick: VIN = 20 V, I2C address 0x21 responds; (3) brick whose 15 V and 20 V PDOs have equal power: note
which is chosen; (4) 20 W 9 V brick: VIN 9 V, ports power up; (5) hot-plug the real cable with a scope on VBUS (TVS).

---

## 3. TVS and ESD on the PD input

### 3.1 VBUS surge TVS

TPS25730 requirement (p8, abs max table note 4): VBUS_IN/VBUS/CC abs max 28 / 28 / 26 V; "A TVS with a break down
voltage falling between the Recommended max and the Abs max value is recommended such as TVS2200." So V_BR must sit
in 22 V (recommended max VBUS, p9) .. 28 V.

| Candidate | V_RWM | V_BR (1 mA) | V_clamp (8/20 us) | IEC 61000-4-2 | LCSC / stock (global, 2026-11-16) | Verdict |
|---|---|---|---|---|---|---|
| TI TVS2200DRVR | 22 V | 24.6 / 25.9 / 27.6 V (TVS2200 p5) | 27.6 typ / 28.0 max at 40 A; 28.35 max at 35 A, 125 C (p5) | +/-17 kV contact (p4) | C523793: **2** (need 6; cn 10,000 does not count) | Not orderable for 5 boards |
| **ElecSuper ESTVS2200DRVR** | 22 V | 24.6 / 25.8 / 27.6 V (ESTVS2200 p3) | 26.6 max at 10 A, 27.5 max at 20 A, 28.0 max at 40 A (p3) | +/-30 kV contact (p2) | **C42400188: 10,606** | **Chosen**: same pinout as TI (GND 1-3, IO 4-6, pad GND; p2), fully specified |
| Maxinmicro TVS2200DRVR | 22 V | only a series summary (26.1 V "Vc") | not tabulated | - | C55616459: 8,674 | Datasheet too thin |
| SMAJ20A-class standard TVS | 20 V | 22.2-24.5 V | ~32 V at rated Ipp | - | many | Clamp well above 28 V; rejected |

Margin: realistic VBUS events here (hot-plug ringing on a 1-2 m cable, ESD) are a few amps, where the clamp is
<= 26.6 V (10 A row), 1.4 V under the TPS25730 abs max. At the full 40 A rating the clamp reaches the abs max with no
margin; TI accepts that for its own recommendation. Downstream parts on VIN: TPS54202 VIN abs max 30 V (TPS54202 p4)
and the LM5148 input caps rated 50 V are above the clamp. Note TVS2200 slew-rate caution: edges > 2.5 V/us make it
conduct briefly (TVS2200 p9); harmless, PD voltage transitions are slow. Place at the receptacle, short wide GND
(TVS2200 p11).

The Schottky from VBUS to GND (SS34, 40 V) is TI's separate recommendation for ground-current surges on sudden
disconnect (TPS25730 p39-40); its 40 V rating is above the 28 V clamp.

### 3.2 CC1 / CC2 ESD

- TPS25730 ESD rating is only +/-1000 V HBM / +/-500 V CDM (p9) - a manufacturing level, not IEC 61000-4-2 at a
  touchable connector. External ESD is needed.
- CC abs max is 26 V (p8): the IC survives CC shorted to a 20 V VBUS (damaged/odd cable). A 5.5 V-standoff ESD array
  like the TPD4E05U06 used on the downstream ports would conduct and burn in that fault, so the PD-input CC lines get a
  24 V part instead.
- **Nexperia PESD24VS1UL,315** (C477994, 128,999, Ext, $0.021): V_RWM 24 V (> 20-21 V VBUS short), V_BR 26.5-27.5 V
  (p4), C_d 23 pF typ / 50 pF max (p4), IEC 61000-4-2 +/-23 kV contact (p3), unidirectional, SOD-882. Its V_BR is a
  little above the 26 V CC abs max; that is the DC rating, while the diode only has to clamp ns-scale ESD energy.
- Alternative: onsemi ESD7241N2T5G (C556454, 22,075, Ext): 24 V, 1 pF, bidirectional, TLP clamp 38 V at 8 A. Fine
  too; more expensive, and the low capacitance buys nothing next to the 330 pF CC caps.
- The 330 pF C0G caps at the pins plus 23-50 pF of diode stay within 200-480 pF (TPS25730 p10).

---

## 4. 3V3 regulator: TPS54202DDCR

### 4.1 Choice: TPS54202 over TPS62933

| | TPS54202DDCR | TPS62933DRLR |
|---|---|---|
| VIN range | 4.5-28 V; UVLO rising 3.9 / 4.2 / 4.4 V, falling 3.4-3.9 V (TPS54202 p4-5) | 3.8-30 V; UVLO rising 3.4-3.8 V (TPS62933 p6) |
| VIN abs max | 30 V (p4) | 32 V (p5) |
| Low-VIN behaviour | 100 % duty while BOOT-SW > 2.1 V (p11) | on-time extension to 7 us (p16) |
| Current limit (HS) | 2.5 / 3.2 / 3.9 A (p5) -> inductor Isat >= 3.9 A | 4.2 / 5 / 5.8 A (p6) -> Isat >= 5.8 A, bigger inductor |
| Parts | VIN cap, BOOT cap, L, Cout, FB divider (+ C_ff); EN floats | + SS cap (>= 6.8 nF, must not float, p4) + RT |
| Stock / price | C191884: 236,487, $0.17 | C3200405: 7,416, $0.48 |

Worst 5 V corner for the TPS54202 (solved, not divided): Type-C vSafe5V is >= 4.75 V at the source. 3V3 load
0.65 A -> input ~0.49 A at ~94 % (s4.3). Drops: cable round trip ~0.2 Ohm x 0.49 A = 0.10 V (assumed 2 m cable),
TPS25730 29 mOhm x 0.49 A = 0.014 V (p12), copper ~0.01 V -> **VIN_min ~ 4.63 V**: above the 4.5 V minimum (0.13 V
margin) and above UVLO rising max 4.4 V. Real dropout is far lower: 3.3 V + 0.65 A x (0.148 x 1.4 hot + 0.068) =
3.48 V at 100 % duty (p5, p11).

Decision: **TPS54202** (cheaper, 32x the stock, smaller inductor, fewer parts, in spec for every compliant PD/Type-C
5 V source). Switch to the TPS62933 only if the hub must also run from out-of-spec 5 V sources (a PC port sagging to
~4.4 V, a weak non-PD charger) - user decision D2.

### 4.2 Design (TPS54202 s7.2.3, p14-17; fsw 500 kHz typ, 390-630 kHz, p5)

Design point: VOUT 3.3 V, IOUT 1 A (load 0.615 A max hubs + ~0.02 A LEDs, requirements s4), VIN 4.63-21 V
(20 V PDO + 5 %), transient clamp 28 V.

| Item | Equation (TPS54202 page) | Result | Chosen part |
|---|---|---|---|
| EN | "Float the EN pin to enable" (pin table p3; s6.3.5 p9). Internal UVLO is what we want (must run at 5 V input). Abs max 7 V (p4) - never tie to VIN | EN unconnected (short stub, keep away from SW) | - |
| FB divider | VOUT = Vref x (1 + R2/R3), Vref 0.596 V (0.581-0.611 V, p5) (Eq 3/7, p10, p14); R2 ~100 k (p14) | R2 = 100 k, R3 = 22.0 k -> **3.305 V** nominal; worst incl. Vref and 1 % resistors 3.170-3.444 V (within +/-5 %: 3.135-3.465 V). TI's 22.1 k (Table 7-2, p17) gives 3.293 V but is Extended | R2 0402WGF1003TCE C25741 (Basic, 10,008,531); R3 0402WGF2202TCE C25768 (Basic, 1,232,796) |
| Inductor value | L_MIN = VOUT (VIN_MAX - VOUT) / (VIN_MAX x K_IND x IOUT x fsw) (Eq 8, p15). With IOUT = 1 A, K = 0.3: 18.5 uH. With the part's 2 A rating (as Table 7-2): 9.3 uH | **10 uH** - TI's validated value for 3.3 V (Table 7-2, p17); the internal compensation is characterised with it. 15 uH would need Isat >= 3.9 A in a bigger part (FXL0630-150 is only 3.5 A) | Cjiang FXL0630-100-M, molded, 7.0 x 6.6 x 3.0 mm, C167223 (Ext, 337,102) |
| Ripple | dI = VOUT (VIN - VOUT) / (VIN L fsw) | 0.556 A p-p at 21 V (10 uH, 500 kHz); worst 0.891 A (8 uH -20 %, 390 kHz); 0.19 A at 4.63 V | - |
| Peak / RMS | I_L(PK) = IOUT + VOUT (VIN_MAX - VOUT)/(VIN_MAX L fsw 1.6) (Eq 10, p15); I_L(RMS) Eq 9 | 1.35 A peak; 1.02 A RMS at 1 A | - |
| Isat check | Isat > high-side current limit max 3.9 A (p5) | FXL0630-100-M Isat 4.9 A (-30 % L, FXL0630 p14, definition p27) > 3.9 A (+ ~0.2 A of delay overshoot at 21 V) | OK |
| Irms / DCR | | Irms 3.8 A (dT 20 C, p14/27) >> 1.02 A; DCR 68 mOhm max -> 71 mW at 1 A, 29 mW at 0.65 A | OK |
| Output cap (crossover) | f_o = 3.95 / (VOUT x C_OUT), keep < 40 kHz (Eq 14, p16) -> C_OUT,eff >= 29.9 uF | 3 x 22 uF 0805 25 V X5R: ~36-39 uF effective at 3.3 V (est. 55-60 % of 66 uF) -> f_o 31-33 kHz; 18 kHz if no derating | Samsung CL21A226MAQNNNE C45783 (Basic, 3,976,362), qty 3 |
| Output cap (load step) | C_O = 2 dI_OUT / (fsw dV_OUT) (Eq 11, p15) | 0.5 A hub step, 0.1 V (3 %): 20 uF <= 36 uF | OK |
| Output cap (ripple) | C_O = I_ripple / (8 fsw V_ripple) (Eq 12, p16) | 30 mV: 4.6 uF (7.4 uF worst ripple) | OK; Eq 15 RMS 0.054 A per cap |
| Feed-forward C6 | C6 = 1 / (2 pi f_o R2) (Eq 16, p17) | at 33 kHz: 48 pF -> **47 pF** (Table 7-2 uses 56 pF at 44 uF nominal) | FH 0402CG470J500NT C1567 (Basic, 570,058) |
| Input cap | >= 10 uF ceramic + optional 0.1 uF, rated above max VIN (p14) | 10 uF 50 V X7R 1210 (same part as LM5148 C_IN and the PPHV local cap); ~6.5 uF effective at 20 V | CL32B106KBJNNNE C138687 (Ext, 135,974) + CL05B104KB54PNC 100 nF 50 V C307331 (Basic, 19,338,656) |
| Input ripple / RMS | dV_IN = IOUT x 0.25 / (C_BULK fsw) + IOUT x ESR (Eq 4); I_CIN(RMS) = IOUT / 2 (Eq 5, p14) | 77 + ~5 mV at 20 V (6.5 uF); 54 mV at 5 V; 0.5 A RMS | OK (1210 X7R carries several A) |
| Bootstrap | 0.1 uF X7R/X5R ceramic BOOT-SW (p11, p14); BOOT-SW abs max 7 V (p4) | 100 nF 16 V | CL05B104KO5NNNC C1525 (Basic, 37,285,054) |
| Compensation | Internal (p8, s6.3.3); only C6 external | - | - |
| Soft start | Internal 5 ms (p5, p10) | - | - |
| Loop-break R | 49.9 Ohm optional (p14) | Omitted (or 0R footprint if a Bode measurement is wanted) | - |

### 4.3 Losses and temperature

| Corner | IC loss (estimate) | Inductor DCR | Efficiency | Tj (R_thetaJA 57.2 C/W EVM / 118.6 JEDEC, p4), 50 C air |
|---|---|---|---|---|
| 21 V in, 1 A (design) | HS 1^2 x 0.207 x 0.157 = 0.03 W; LS 1^2 x 0.109 x 0.84 = 0.09 W; switching 0.5 x 21 x 1 x 20 ns x 500 kHz = ~0.1 W; total ~0.25 W | 0.07 W | ~90 % | 64 C / 80 C |
| 21 V in, 0.65 A (real max) | ~0.13 W | 0.03 W | ~92 % | 57 C / 65 C |
| 4.63 V in, 0.65 A | ~0.1 W (D ~0.72) | 0.03 W | ~94 % | 56 C / 62 C |

R_DS(on) 148 / 78 mOhm at 25 C (p5) x 1.4 for heat (Fig 5-3/5-4, p6). Switching edges are estimated (not in the
datasheet). Input current from VIN: ~0.12 A at 21 V, ~0.49 A at 4.63 V.

Layout (p20-21): input cap at VIN/GND pins, small SW copper, FB from the output cap with Kelvin GND, FB away from SW and
the inductor.

### 4.4 3V3 parts summary

| Function | Part | Value | LCSC | Stock (global, 2026-11-16) | Qty/board |
|---|---|---|---|---|---|
| Buck | TI TPS54202DDCR SOT-23-6 | - | C191884 (Ext) | 236,487 | 1 |
| Inductor | Cjiang FXL0630-100-M | 10 uH, Isat 4.9 A, 68 mOhm | C167223 (Ext) | 337,102 | 1 |
| C_IN | Samsung CL32B106KBJNNNE 1210 X7R 50 V | 10 uF | C138687 (Ext, shared with LM5148) | 135,974 | 1 |
| C_IN HF | Samsung CL05B104KB54PNC 0402 X7R 50 V | 100 nF | C307331 (Basic) | 19,338,656 | 1 |
| C_BOOT | Samsung CL05B104KO5NNNC 0402 X7R 16 V | 100 nF | C1525 (Basic) | 37,285,054 | 1 |
| C_OUT | Samsung CL21A226MAQNNNE 0805 X5R 25 V | 22 uF | C45783 (Basic) | 3,976,362 | 3 |
| R2 (top) | UNI-ROYAL 0402WGF1003TCE | 100 k 1 % | C25741 (Basic) | 10,008,531 | 1 |
| R3 (bottom) | UNI-ROYAL 0402WGF2202TCE | 22.0 k 1 % | C25768 (Basic) | 1,232,796 | 1 |
| C6 (feed-forward, across R2) | FH 0402CG470J500NT C0G 50 V | 47 pF | C1567 (Basic) | 570,058 | 1 |

---

## 5. Capacitance on PPHV (VIN) against the 100 uF limit

Limit: C_PPHV nom 47 uF, **max 100 uF** (TPS25730 p10). Note 1 (p10): table values exclude derating, i.e. they are
effective capacitance. Note 4: 100 uF is the USB PD cSnkBulkPd limit after a contract. The relevant moment is the
5 V -> 20 V transition (the caps charge through the closed switch), so the budget is shown at 20 V and, as the
conservative case, at 5 V (where ceramics have their highest capacitance).

DC-bias factors used (estimates, see risk 6): 10 uF 50 V X7R 1210 -> 9.3 uF at 5 V, 6.5 uF at 20 V (the 6.5 uF at
21 V is WEBENCH's own derated figure for the LM5148 C_IN: 4 x 10 uF = 26 uF, `docs/power-design.md`); worst case adds
+10 % tolerance (K parts). Aluminium electrolytic: no DC-bias loss, +20 % tolerance.

| Item on PPHV | Qty | Nominal | Eff. at 20 V | Eff. at 5 V | Worst (+tol) at 20 V | Worst (+tol) at 5 V |
|---|---|---|---|---|---|---|
| TPS25730 local, 10 uF 1210 | 1 | 10 | 6.5 | 9.3 | 7.2 | 10.2 |
| LM5148 C_IN, 10 uF 1210 (WEBENCH) | 4 | 40 | 26.0 | 37.2 | 28.6 | 40.9 |
| LM5148 HF 100 nF | 2 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 |
| TPS54202 C_IN, 10 uF 1210 | 1 | 10 | 6.5 | 9.3 | 7.2 | 10.2 |
| TPS54202 HF 100 nF | 1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 |
| **Ceramic subtotal** | | 60.3 | **39.3** | **56.1** | **43.3** | **61.6** |
| + bulk 47 uF electrolytic | 1 | 47 | 47 | 47 | 56.4 | 56.4 |
| = total with 47 uF bulk | | | 86.3 | 103.1 | 99.7 | **118.0 - fails** |
| + bulk 33 uF | 1 | 33 | 33 | 33 | 39.6 | 39.6 |
| = total with 33 uF bulk | | | 72.3 | 89.1 | 82.9 | **101.2 - marginal** |
| + bulk 22 uF | 1 | 22 | 22 | 22 | 26.4 | 26.4 |
| = total with 22 uF bulk | | | **61.3** | **78.1** | **69.7** | **88.0 - complies** |

Result: the ceramics alone (6 x 10 uF 1210 + HF) comply with margin at both corners (43-62 uF worst). **A bulk
electrolytic of 22 uF (+/-20 %) keeps the worst case at 88 uF; 47 uF does not comply and 33 uF is marginal at 5 V.**
Candidate bulk: KNSCHA RVT22UF50V67RV0028, 22 uF 50 V, SMD 6.3 x 5.4 mm, C2836438 (Ext, 127,110, 2026-11-16).

What to do (decision for the LM5148 block, D4): use <= 22 uF of bulk on VIN, or drop the bulk and rely on the
ceramics. Trade-off: the bulk's ESR damps the PD cable inductance against the LM5148 input caps (input-filter
interaction is worst at the 9 V contract, where the converter's input impedance is ~V^2/P = 81/95 = 0.85 Ohm).
22 uF electrolytic gives some damping; full "C_damp >= 4 x C_in" damping would need ~160 uF, which the 100 uF limit
forbids. So: 22 uF bulk, and add a bench check of VIN ringing during a full-load step on a 9 V contract. Do not put
bulk on the connector side of the TPS25730 either: C_VBUS max is 10 uF (p10).

VBUS side (before the switch): 4.7 uF 1206 50 V (est. ~2.3 uF at 20 V, ~4.3 uF at 5 V) + 4 x 10 nF + TVS 115 pF ->
inside C_VBUS 1-10 uF (p10).

---

## 6. Decisions for the user

| # | Decision | Recommendation |
|---|---|---|
| D1 | Operating current strap: 1 A (mismatch only below 9 V / 9 W) vs higher | 1 A (ADCIN3 = 1, ADCIN4 = 3 -> 1 A / 5 A) |
| D2 | 3V3 buck: TPS54202 (in spec for compliant 5 V sources, 0.13 V margin) vs TPS62933 (runs down to ~3.8 V) | TPS54202 unless out-of-spec 5 V sources must work |
| D3 | LEDs: rail-based (green = 5V_BUS up, red = 3V3 up and 5V_BUS down, works for every source) vs CAP_MIS blink for "low power" | Rail-based |
| D4 | VIN bulk capacitor <= 22 uF (to keep PPHV <= 100 uF) | 22 uF 50 V electrolytic |
| D5 | VIN_3V3 of the TPS25730 not connected to the 3V3 rail (DNP 0R) | As proposed |

## 7. Unique parts added by these two blocks

Extended (loading fee each): TPS25730DREFR, ESTVS2200DRVR, PESD24VS1UL, TPS54202DDCR, FXL0630-100-M,
CL32B106KBJNNNE (shared with LM5148), KT-0603G (probably shared with port LEDs), RVT22UF50V67RV0028 (if used).
Everything else is Basic.


## Capture notes (schematic capture, 2026-11-16)

- **DBG_ACC (10) and PLUG_FLIP (13) open**: open-drain status outputs, Hi-Z (pin table p5); not used.
- **TPS25730 VBUS (32, 33) and VBUS_IN (23-25) on one net** (PD_VBUS) with C1 4.7 uF + 4x 10 nF, as Fig 9-3 (p42).
- **USB4105 D+/D- (A6/B6/A7/B7) and SBU (A8/B8) unconnected**: power-only input.
- **PPHV/VIN**: C8 10 uF/50 V ceramic + C12 22 uF/50 V electrolytic + test pad TP1, as section 5 sizes it.
- **Test pads TP1-TP8 are bare pads** (TestPoint_Pad_D1.5mm), not in the BOM or the position file.
- **Red LED D6 (KT-0603R)**: its JLC footprint has pad 1 = anode, so it uses its own symbol (A = 1), not Device:LED.
