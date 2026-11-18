# 10-port USB-C bench hub - requirements and architecture

Revision: 0 - Date: 2026-11-16 - Status: agreed (interview complete; parts provisional until schematic capture)

Scope: hobby/personal project. Not designed or reviewed for safety-critical, medical, automotive, on-board mains or
certified use.

## 1. Purpose

- What it does: USB 2.0 (480 Mbps) bench hub. One USB-C upstream (host) port, ten USB-C downstream ports, one
  USB-C PD input that powers the hub and every downstream port. Baseline: 5 V on every downstream port, advertised
  through the Type-C CC pins, with a current limit on each port and a shared total budget. PD output on one or two ports is
  still open (decide at the power level).
- Users: the owner, on their own bench (dev boards, flash drives, keyboards, phones charging)
- Quantity: 5 fabricated, 2-5 assembled
- Budget: ~$100-150 total for the order
- Timeline: no deadline
- Project type: tool
- Existing prototype / firmware: none
- Host port: data only. The hub does not supply power or PD back to the host. With no PD brick it runs from the
  host's VBUS instead (host-powered mode, 2026-11-18: docs/power-design.md "Host-powered mode").

## 2. Usage and environment

| Item | Requirement |
|---|---|
| Location | Indoor, on a bench |
| Ambient temperature | 0 to 40 C |
| Enclosure | 3D-printed case (material TBD; PLA softens ~55-60 C, PETG/ASA safer). Needs vents over the 5 V converter (Q30/Q31/L30/U30) and hub A (U4, 0.8-1.4 W whenever a host is connected): review-2026-11-17 D1 |
| Mounting | Screw bosses in the printed case (hole positions set at physical level) |
| Vibration / moisture / dust | None |
| External connections | 10x USB-C downstream (plugged/unplugged all day), 1x USB-C host, 1x USB-C PD input; cables ~1-2 m |
| User-touchable parts (ESD) | Every USB-C receptacle (12). ESD clamp on every port at the connector |
| Long cables (> 1 m) | USB cables up to ~2 m on every port; ESD/hot-plug, no surge beyond that |
| Mains proximity | None (PD brick is a certified external adapter) |
| Thermal budget | Up to ~75-100 W through the hub; ~5-8 W lost in the 5 V converter at full load. Inside a printed box: case surface warm at most, internal air < ~50 C |

Connector strength: USB-C receptacles with through-hole shell legs (bench use, frequent plugging).

Backfeed / wrong-cable cases (protect for these):
- C-to-C charger plugged into a downstream port: harmless by design. Both ends present Rp (source), neither sees Rd,
  so a compliant charger never turns VBUS on and PD never starts.
- USB-A charger with an A-to-C cable into a downstream port: VBUS is always on (5 V, legacy) -> the port power switch
  must block reverse current; downstream VBUS must never reach the PD input or the 5 V converter output unblocked.
- Non-compliant "always hot" C cables/chargers and self-powered devices: assume up to 5.5 V backfed on a port VBUS.
  A >5.5 V fault on a downstream port is not designed for (TVS clamps transients only).

## 3. Functional blocks

### Block diagram

```
PD IN (USB-C, Rd sink) --> [TVS] --> [TPS25730 PD sink, strap-set, internal power switch] --> VIN (5 V before
                                                                         contract, then 9-20 V)
                                                                                |  '--> [3V3 buck, any VIN]
                                                                                |
                                                                          [5 V buck, ~15-18 A]  (vented area)
                                                                                |
                                   5V_BUS --+--> [port switch x10: I-limit, reverse-block, FLT] --> VBUS port 1..10
                                            '--> [3.3 V LDO] --> hub ICs, LEDs (+1.2 V if a hub IC needs it)

HOST (USB-C, Rd, data only) --D+/D- 480M--> [hub A, MTT] --D+/D- 480M--> [hub B, MTT]   (topology TBD at parts:
   VBUS -> divider -> hub VBUS_DET only     |                                |              e.g. 7-port + 4-port)
   (never tied to 5V_BUS)                   '-- downstream D+/D- ------------'--> port 1..10 (both C pair positions
                                                PRTPWR/OCS per port <-> port switches          tied at receptacle)
                                                LED per port                         CC1/CC2: Rp to 5 V (current adv.)
```

### Blocks

| Block | Function | Key requirements |
|---|---|---|
| Processor | None | Everything standalone / strap-configured |
| Connectivity | USB 2.0 hub, 1 upstream + 10 downstream, 2 cascaded hub ICs | High speed 480 Mbps; multi-TT (one TT per port); individual (non-ganged) port power switching so `uhubctl` can cycle ports |
| Sensors | None | |
| Display | None | |
| Actuators / loads | 10 downstream VBUS outputs | Per-port current limit, reverse-current blocking, fault flag to hub OCS |
| Storage | None (or hub config EEPROM only if the chosen hub IC needs it) | Default strap config |
| User interface | Per-port LED (port powered / fault), power-input status LED | |
| Debug / programming | None needed; test points on every rail | |
| Expansion | None | |

### Interfaces

| From | To | Interface | Speed | Length / notes |
|---|---|---|---|---|
| Host USB-C | Hub A upstream | USB 2.0 D+/D- | 480 Mbps | 90 ohm differential; short |
| Hub A downstream | Hub B upstream | USB 2.0 D+/D- | 480 Mbps | 90 ohm differential; tier depth 2 hubs |
| Hub A/B downstream | Ports 1-10 | USB 2.0 D+/D- | 480 Mbps | 90 ohm differential; length set by layout, match within pair |
| Hub A/B | Port switches | PRTPWR (enable) / OCS (fault) | DC | Individual per port |
| Hub A/B | Port LEDs | GPIO / LED pins | DC | |
| Host VBUS | Hub VBUS_DET | Divider | DC | |
| Host VBUS | 5V_BUS | U8 TPS259470 eFuse | DC | On only while the buck is not regulating (BUCK_PG low on OVLO); 1.78 A limit; reverse blocking: never backfeeds the host |
| VIN | 5 V buck EN | UVLO divider 100k/15.4k | DC | Buck on at 7.5 V, off at 6.5 V: off on 5 V-only sources |
| Crystal | Each hub IC | XTAL | 12/24 MHz (per IC) | Close to IC |

### Startup and control

- Must work before the main processor runs: there is no processor. The PD sink negotiates standalone; the 5 V buck
  starts when VIN passes its 7.5 V EN/UVLO divider; the hub ICs start from 3.3 V and enumerate when host VBUS is seen.
  Without a brick, U8 turns on when HOST_VBUS passes 3.75 V and ramps 5V_BUS at 0.2 V/ms; D41 then feeds VIN and
  the 3V3 buck starts.
- How each is configured without it: resistor/strap configuration only.

### External connections (user-facing)

| Connection | Connector or pad | Label | Polarity / keying | Side |
|---|---|---|---|---|
| Ports 1-10 | USB-C receptacle, TH shell legs | 1..10 (silk + case) | Type-C (reversible) | Left 1-3 (back to front), front 4-7 (left to right), right 8-10 (front to back): as placed and silk-labelled |
| Host | USB-C receptacle | HOST | Type-C | Back |
| Power in | USB-C receptacle | PWR IN / PD | Type-C | Back |

### Bring-up test points

| Rail or signal | Test point (pad, side) | Ground pad nearby | Expected value |
|---|---|---|---|
| VIN (after PD sink) | TP, top | yes | negotiated PD voltage |
| 5V_BUS | TP, top | yes | 5.0-5.2 V |
| 3V3 | TP, top | yes | 3.3 V |
| 1V2 (if any) | TP, top | yes | 1.2 V |
| 5V_BUS power-good (LM5148 PG) | TP | | high when 5 V in regulation |
| Hub reset (each) | TP | | high after reset |
| Host VBUS_DET | TP | | high with host attached |

## 4. Power

- Source(s): USB-C PD input, any brick up to 100 W (20 V / 5 A, needs a 5 A e-marked cable; a 3 A cable caps a
  20 V source at 60 W). Must run on smaller bricks too: the 5 V budget follows the negotiated contract, not a fixed
  number. Lowest supported source: a PD brick offering 9 V or more. 5 V-only sources are not supported: the 5 V
  converter stays off, ports stay dark, a "low power" LED lights. Host-powered mode (2026-11-18): with no brick or a
  5 V-only one, an attached host powers the hub and its ports through U8 (1.78 A limit; the host's own port limit
  usually binds first). The hub itself takes ~0.5 A at 5 V. Weak-host start-up of the 3V3 buck is a bench check
  (power-design.md "Host-powered mode").
- Downstream: every port advertises up to 3 A (Rp on CC). Oversubscribed on purpose: 10 x 15 W = 150 W of
  advertisement against at most ~90 W of 5 V. Fixed Rp (3 A) on every port, no budget controller. Per-port current
  limit ~3 A is the only enforcement. Accepted consequence (user, 2026-11-16): if total draw exceeds what the brick
  or the converter can supply, the 5 V rail sags / the converter hiccups / the brick trips, and ports (or the whole
  hub) reset. No hardware damage.
- Charging: none
- Protection: PD input TVS + fuse or eFuse; input current limited to the PD contract so the brick never trips;
  per-port current limit (~3 A) with reverse-current blocking (backfeed up to ~5.5 V); ESD on every connector;
  host VBUS used for detection, and as the host-powered-mode feed through U8 (eFuse: 1.78 A, 0.2 V/ms inrush,
  reverse blocking, off whenever the buck regulates).
- Battery life target / sleep current: n/a

### Rails

| Rail | Voltage | Tolerance | Source | Regulator type (tentative) | Noise-sensitive loads |
|---|---|---|---|---|---|
| VIN | PD contract, 5-20 V | per PD spec | PD brick via sink controller | - | - |
| 5V_BUS | 5.1 V (headroom for cable/switch drop) | +/-3 % | VIN (9-20 V) | Buck, ~17 A limit, 2-phase or 2 paralleled; enabled only when VIN >= ~8 V | - |
| 3V3 | 3.3 V | +/-5 % | VIN, tapped before the input eFuse (independent of 5V_BUS) | Small buck, >= 1 A | Hub ICs (PLL, PHY) |

### Power budget

| Rail | Load | Avg mA | Peak mA | Datasheet tables summed (table, page; what each excludes) |
|---|---|---|---|---|
| 5V_BUS | Ports 1-10 (3 A advertised each, oversubscribed) | - | 30000 advertised, limited to budget | budget = contract power x eta - electronics |
| VIN | 3V3 buck from VIN: USB2517 420/460 mA (Tbl 8-2 p50, all supplies, excl. LED load) + USB2514B 155 mA max (Tbl 6-4 p41) + LEDs | 500 | 650 | sum of the two hub tables + ~20 mA LEDs |
| | **Max 5 V deliverable** | | ~18000 at 100 W in (92 % eta) | 100 W x 0.92 / 5.1 V ~ 18 A, minus electronics |

Deliverable 5 V budget by source (eta 0.92, minus ~1.5 W electronics):

| PD source | Max in | 5 V total available | = ports at 3 A |
|---|---|---|---|
| 100 W (20 V 5 A, 5 A cable) | 100 W | ~90 W / 17.6 A | ~5.9 |
| 65 W (20 V 3.25 A) | 65 W | ~58 W / 11.4 A | ~3.8 |
| 60 W (20 V 3 A, any 3 A cable) | 60 W | ~54 W / 10.5 A | ~3.5 |
| 45 W | 45 W | ~40 W / 7.8 A | ~2.6 |
| 30 W | 30 W | ~26 W / 5.1 A | ~1.7 |
| 20 W (9 V 2.22 A) | 20 W | ~17 W / 3.3 A | ~1.1 |

Input power check: all ten ports at 3 A (150 W at 5 V) cannot be met by any supported source -> fails by design
(oversubscribed, accepted by user 2026-11-16). Mitigations kept without an MCU: converter current limit set just
under the 100 W brick's capability (~17 A) so on a 100 W brick the converter sags before the brick trips; hub ICs
fed from VIN by their own regulator so a port-rail sag does not drop data. On smaller bricks an overload trips the
brick and resets everything.

## 5. Physical

| Item | Requirement |
|---|---|
| Board outline | **85 x 85 mm** square (user, 2026-11-16; after area check: ~2,800 mm2 of parts = ~40 % of one side less hole keepouts) |
| Area budget | Perimeter band ~10 mm deep for USB-C receptacles + port switch/ESD/Rp (3 sides) and host/PD (4th); 4 corner mounting keepouts ~8 mm dia; interior ~50 x 50 mm for PD sink, 17 A 2-phase buck (~25 x 30 mm), 3V3 regulator, 2 hub ICs + crystals |
| Connector positions | Left edge: ports 1-3 (top to bottom). Front (bottom) edge: ports 4-7 (left to right). Right edge: ports 8-10 (bottom to top). Back (top) edge: HOST (left, x=20) and PWR IN (right, x=62). Port k = schematic instance portk; hub A ports 1-6 -> 1-6, hub B -> 7-10 |
| Mounting holes | 4 x M3 (3.2 mm) in the corners, into heat-set inserts in printed bosses |
| Height limits | Lid ~15-20 mm above board top; tallest parts are buck inductors (~8-10 mm). Bottom: standoff height only |
| Assembly side | Top only |
| Through-hole parts | USB-C receptacle shell legs (12 connectors), JLC-assembled |
| Assembly method per part | All JLC-assembled |
| LEDs | Top-mount LED behind each port, visible through a light pipe / hole in the lid near that port; port numbers on lid. "Low power" and "PD OK" LEDs near the back |

## 6. Manufacturing

| Item | Choice |
|---|---|
| Fab | JLCPCB (international) |
| Assembly | JLC economic, top side only, JLC fits the through-hole connector legs |
| Assembler's stock region | global (international JLCPCB) - recorded in `docs/sourcing.json` |
| Quantity | 5 fabricated / 5 assembled |
| Surface finish, colour | ENIG (fine-pitch QFN hub ICs, USB-C pins), green |
| Smallest package | 0402 |
| Part policy | in stock at LCSC (global) for 5 boards + attrition; prefer Basic / Preferred Extended |

## 7. Stackup

| Item | Choice |
|---|---|
| Layers | 4 |
| Reason | 90 ohm USB 2.0 HS differential pairs need a solid reference plane; 17 A buck needs a ground plane under its hot loop |
| JLC stackup | JLC04161H-7628 (the default build) |
| Thickness | 1.6 mm |
| Copper | outer 1 oz, inner 0.5 oz (standard; user 2026-11-16). 5 V distribution as a wide pour; verify drop/heat with the DC solver in power design |
| Layer use | L1 signal + power stage / L2 GND / L3 5V_BUS pour + GND / L4 signal |
| Controlled impedance | USB D+/D- 90 ohm differential (widths from JLC impedance calculator) |
| Design rules | track/space 0.15 mm (0.1 mm only in QFN fan-out if needed), via 0.3/0.6 mm (0.2/0.45 free on 4 layer), copper to edge 0.3 mm |

Values from kicad-skills jlcpcb-stackups.md (checked Oct 2026); re-check on jlcpcb.com before ordering.

## 8. Component candidates

All stock: LCSC **global**, 2026-11-16. All Extended, all economic-assembly OK. Prices USD (LCSC unit).
Datasheets in `docs/datasheets/`. Front-runner first in each block; nothing here is approved yet.

| Block | Candidate (front-runner first) | LCSC | Stock (region, date) | Class | Package | Why / concerns |
|---|---|---|---|---|---|---|
| Hub A (7-port) | Microchip USB2517-JZX | C1521556 | 3,035 (global, 2026-11-16) | Ext | QFN-64 9x9 0.5 mm | MTT; individual port power + sensing by default straps (CFG_SEL=000, reg 06h=9Bh, p15/p20/p23); PRTPWR active-high only (p10); 3.3 V only, internal 1.8 V; 24 MHz xtal; 420/460 mA typ/max (Tbl 8-2 p50); green+amber LED pin per port. $4.13. USB2517I (C478081, 3,530) is the -40 C grade |
| Hub B (4-port) | Microchip USB2514B-AEZC-TR | C16251 | 10,041 (global, 2026-11-16) | Ext | QFN-36 6x6 0.5 mm | MTT; individual power/sense at CFG_SEL=00 (Tbl 5-1 p19); 3.3 V only; 24 MHz; 155 mA max at 4 HS ports (Tbl 6-4 p41); no per-port LED pins; PRTPWRx double as BC_EN straps. $1.81 |
| Hub fallback | WCH CH338X (7) + CH335F (4) | C42387265 / C5137013 | 74 / 4,683 | Ext | QFN-64 / QFN-28 0.4 mm | CH338X stock too low; CH335F has no VBUS_DET; not in uhubctl list |
| Port switch x10 | Diodes AP22815AWT-7 | C2150007 | 850 (global, 2026-11-16) | Ext | TSOT-25 | Fixed 3.1/3.6/4.2 A; 40 mOhm; reverse block on AND off (65 mV, p13); OUT abs max 28 V; FLG open-drain 7 ms blanking; EN active-high ("A"). OVP lockout at 5.6 V on OUT. $1.02 |
| Port switch alt | Silergy SY6863B3ABC | C2687365 | 2,049 (global, 2026-11-16) | Ext | SOT-23-6 | 3.47-4.08 A with 1.878 k RSET; reverse block on/off; EN active-high; datasheet Rev 0.9C. $0.47 |
| Port switch (Type-C source ctrl) | TI TPS25810RVCR | C473913 | 6,044 | Ext | WQFN-20 | Cold socket + 3 A Rp built in, but reverse blocking only specified when disabled -> fails backfeed-when-on requirement. Not recommended |
| ESD x12 | TI TPD4E05U06DQAR | C138714 | 25,311 | Ext | USON-10 | D+/D-/CC1/CC2 per port; 5.5 V VRWM; 0.5 pF. $0.084 |
| VBUS TVS x10 | SMF6.0A | C123790 | 79,361 | Ext | SOD-123FL | Downstream VBUS; datasheet not yet read |
| USB-C x11 (ports + host) | HRO TYPE-C-31-M-12 | C165948 | 520,296 | Ext | 16-pin, 4 TH legs | 7.35 deep x 8.94 wide; overhang not dimensioned (measure at placement). $0.19 |
| USB-C PD input | GCT USB4105-GF-A | C3020560 | 16,538 | Ext | 16-pin, TH stakes | VBUS 5 A, 48 V rated (p1). $1.02 |
| PD sink | TI TPS25730DREFR | C22438973 | 1,018 | Ext | QFN-38 4x6 | Strap-only; 9-20 V window; 5 A max current strap; integrated 16 mOhm path with OVP/RCB, 7 A <=45 C / 6 A <=65 C; PPHV max 100 uF; which PDO in the window it picks is NOT stated. $3.39 |
| PD sink alt | WCH CH224Q | C46061833 | 21,881 | Ext | DFN-10 2x2 | 20 V by resistor; PG open-drain; fallback behaviour and requested current undocumented. $0.46 |
| 5 V converter (option 1) | TI TPS56A37RPAR x2, two independent 5-port rails | C22392669 | 12,272 | Ext | HotRod 3x3 | 4.5-28 V, 10 A each, 500 kHz, 94-95 % at 19 V->5 V; precise EN for 8 V UVLO; valley limit 10-13.8 A. Each inductor Isat >= ~17 A. $2.08 each |
| 5 V converter (option 2) | TI LM5148RGYR, one 17 A rail (or 2 in dual-phase) | C7470701 | 51,164 | Ext | VQFN-24 | Controller + 2 FETs + shunt; settable limit (+/-20 %); more area. $0.92 |
| 3V3 | TI TPS54202DDCR | C191884 | 236,487 | Ext | SOT-23-6 | 4.5-28 V, 2 A; needs ~1 A (hubs ~615 mA max). $0.17 |
| 3V3 alt | TI TPS62933DRLR | C3200405 | 7,416 | Ext | SOT-583 | 3.8-30 V in, 3 A. $0.48 |
| Input TVS | TVS2200-type clone (ElecSuper ESTVS2200DRVR) | C42400188 | 10,616 | Ext | SON | 22 V standoff, 28 V clamp (TI spec; clone unverified). 28 V = TPS25730 VBUS abs max -> no margin |
| Input eFuse | TI TPS259827ONRGER | C2155761 | 2,922 | Ext | QFN | 2.7-24 V, 15 A, adjustable limit +/-8 %, inrush slew. Set ~5.2 A: becomes the whole-hub limit with a 100 W brick. $4.76 |

### Cost estimate (rough, 2026-11-16; LCSC unit prices, JLC fees from jlcpcb-stackups.md)

| Item | Per board | 5 assembled | 2 assembled |
|---|---|---|---|
| Hub ICs (USB2517 + USB2514B) | 5.94 | 29.70 | 11.88 |
| Port switches (SY6863 x10) | 4.70 | 23.50 | 9.40 |
| 5 V stage (LM5148, FETs, shunt, inductor, caps) | ~5.00 | 25.00 | 10.00 |
| PD sink TPS25730 + TVS | 3.70 | 18.50 | 7.40 |
| Connectors (11 HRO + 1 GCT) | 3.11 | 15.55 | 6.22 |
| ESD, VBUS TVS, 3V3 buck, crystals, LEDs, passives | ~3.50 | 17.50 | 7.00 |
| **Parts subtotal** | **~26** | **~130** | **~52** |
| Extended-part loading (~18 unique x $3.07, per order) | | ~55 | ~55 |
| Setup + stencil + through-hole joints | | ~14 | ~14 |
| 4-layer ENIG PCB, 5 pcs (unverified, check quote) | | ~25 | ~25 |
| Shipping (unverified) | | ~20 | ~20 |
| **Total** | | **~245** | **~165** |

## 9. Decisions

| Decision | Choice | Reason | Agreed by user (date) |
|---|---|---|---|
| Data speed | USB 2.0 high speed (480 Mbps) on all ports | Bench use; avoids 3 tiered USB3 hubs, SS muxes, 90 ohm SS pairs | 2026-11-16 |
| Host port power | Data only, no charging of the host | Keeps it a hub, not a dock; no PD source on upstream | 2026-11-16 |
| Enclosure | 3D-printed case, vented | User choice | 2026-11-16 |
| Port connectors | Through-hole-shell USB-C, ESD clamp on every port | Bench plugging all day | 2026-11-16 |
| Backfeed protection | Reverse-current-blocking port switches; CC as Rp-only source on downstream | User: protect against a charger plugged into a port | 2026-11-16 |
| Processor | None, all standalone (reconfirmed after discussing an adaptive-budget MCU) | User accepts brownout/reset on overload | 2026-11-16 |
| Port control | LED per port, individual port power switching via hub (uhubctl), no buttons | Default accepted | 2026-11-16 |
| Hub TT | Multi-TT hubs | Several FS devices at once | 2026-11-16 |
| Downstream power | 5 V only, up to 3 A advertised on every port, oversubscribed ("gym membership") | User: nobody pulls it all at once | 2026-11-16 |
| PD input | Up to 100 W; must adapt to smaller bricks (budget follows the contract) | User | 2026-11-16 |
| PD output | None | User | 2026-11-16 |
| Minimum source | PD >= 9 V; 5 V-only sources unsupported (ports off, LED) | User | 2026-11-16 |
| Host-powered mode | No brick (or 5 V-only): U8 TPS259470 eFuse feeds HOST_VBUS onto 5V_BUS while the buck is not regulating (BUCK_PG on OVLO), 1.78 A, reverse blocking; D41 SS34 feeds VIN for the 3V3 buck | User: data without a brick ("worthy change", "ok, go") | 2026-11-18 |
| Form factor | Square board, ports on 3 sides (4/3/3), HOST + PWR IN on the back | User | 2026-11-16 |
| Manufacturing | JLCPCB economic assembly, 5 boards fabricated and assembled, ENIG | User | 2026-11-16 |
| Stackup | 4 layers, JLC04161H-7628, 1 oz outer / 0.5 oz inner | User | 2026-11-16 |
| 5 V converter | One shared 5V_BUS rail (~17 A), not two 5-port rails -> LM5148-class controller + FETs; converter limit is again the whole-hub limit | User | 2026-11-16 |
| PD sink | TI TPS25730 | User: one per board, cost OK | 2026-11-16 |
| Port switch | Silergy SY6863B3ABC x10 (3.47-4.08 A, reverse block, EN active-high) | User; cheaper than AP22815 | 2026-11-16 |
| Hub ICs | USB2517 (7-port) -> USB2514B (4-port) cascade | Only in-stock MTT pair with strap-only individual port power | 2026-11-16 (presented, not objected) |
| Regulator design tool | TI WEBENCH OK | User | 2026-11-16 |
| Board size / trims | 85 x 85 mm; per-port and host VBUS TVS kept but as onsemi ESD5Z6.0T1G SOD-523 (C82323) instead of SMF6.0A; port caps 0603; 1.0 mm test pads | User (option 1 + 80x80) | 2026-11-16 |
| Thermal vias in exposed pads | Paste windows cut clear of the holes (paste_clear.py on project copies of the U4, U5, U1, U30, Q30, D1 footprints, vias as footprint pads); no filled/capped vias | User: free, JLC-standard | 2026-11-16 |
| Overload behaviour | Accept brownout/reset; per-port limit only; converter limit ~17 A; hub logic on its own regulator from VIN | User | 2026-11-16 |

An agreed decision is frozen: changing it later (a substitute part, a new threshold) goes back to the user with the
reason and options first (R26).

## 10. Assumptions

Defaults accepted without explicit confirmation, and anything decided without asking; each was stated to the user
(date). Challenge any that are wrong.

- All 10 downstream ports are USB-C receptacles (2026-11-16)
- Indoor, 0-40 C, no vibration/moisture, no mains (2026-11-16)
- The 5 V converter is sized for the largest supported brick (~18 A from 100 W), so the brick contract, not the
  converter, is the limit the budget policy works against (2026-11-16)
- With a 5 V-only source the hub logic is still powered (its regulator runs from any VIN), so it enumerates as a
  hub with dark ports; only the 5 V port converter is held off (2026-11-16)
- Input eFuse dropped: with one 17 A rail the converter current limit is the whole-hub limit again; protection is
  TVS + TPS25730 OVP/RCB + converter limit + per-port switches (2026-11-16)
- Hub ICs (3V3/1V2) are fed from VIN by their own small regulator, not from 5V_BUS, so a
  port-side overload or brownout never resets the hub and drops every device's data connection (2026-11-16)
- Detailed-design defaults taken from the design notes (2026-11-16): TPS25730 operating current strap 1 A / max 5 A;
  3V3 = TPS54202; status LEDs from the rails (green "PD OK" on 5V_BUS, red "low power" when 3V3 is up and 5V_BUS
  is not); VIN bulk <= 22 uF (TPS25730 PPHV 100 uF limit); TPS25730 VIN_3V3 not connected; hub B on hub A port 7
  (removable: non-removable strap only covers ports 1-3); hub B battery charging off; hub B VBUS_DET driven from
  hub A PRTPWR7; one reset supervisor (TPS3809K33) for both hubs; no HOST activity LED; no 1V2 rail (internal);
  one green LED per port from its switched VBUS; port current limit 3.47-4.08 A (RSET 1.87 k)
- Backfeed on a downstream port is at most ~5.5 V (legacy A-to-C charger or self-powered device); no 9-20 V fault
  on a downstream port is designed for (2026-11-16)
- Tool project, 5 boards fabricated, 2-5 assembled by JLCPCB, ~$100-150 total, no deadline (2026-11-16)

## 11. Open questions

| Question | Who answers | Blocks |
|---|---|---|
| Hot downstream VBUS (plain switch, non-compliant but backfeed-proof) vs Type-C cold socket | User | Port circuit |
| Assembled quantity: 2 or 5 (~$165 vs ~$245)? Stock checks use 5 (conservative) | User, at order time | Order only |

## 12. Next steps

1. Create the KiCad project; set stackup and design rules to section 7; draw the outline and mounting holes.
2. Power design from section 4 (pcb-power-supply).
3. Stock and datasheet checks for each candidate in section 8 (pcb-part-selection).
4. Schematic capture and layout (kicad-pcb-workflow).
5. Design review before ordering (kicad-board-review).
