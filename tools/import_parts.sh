#!/usr/bin/env bash
# Import every JLC-assembled part's symbol, footprint and 3D model into hw/JLCImport (JLC's own footprints).
# One LCSC number per value/package. Re-running skips parts already in the library (no --overwrite).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PARTS=(
  # ICs
  C7470701   # LM5148RGYR 5 V controller
  C22438973  # TPS25730DREFR PD sink
  C191884    # TPS54202DDCR 3V3 buck
  C1521556   # USB2517-JZX hub A
  C16251     # USB2514B-AEZC-TR hub B
  C61364     # TPS3809K33DBVR reset supervisor
  C2687365   # SY6863B3ABC port switch
  C138714    # TPD4E05U06DQAR ESD array
  C3662799   # TPS259470ARPWR host-VBUS eFuse (host-powered mode, 2026-11-18)
  # discretes, power
  C553150    # CSD17505Q5A high-side FET
  C202231    # CSD17573Q5B low-side FET
  C6753479   # XAL1010-152MED 1.5 uH
  C2904234   # 2.5 mOhm 2512 shunt
  C167223    # FXL0630-100-M 10 uH
  C42400188  # ESTVS2200DRVR VBUS TVS
  C8678      # SS34 Schottky
  C477994    # PESD24VS1UL CC ESD
  C123790    # SMF6.0A VBUS TVS
  C15127     # AO3401A P-FET
  C12624     # KT-0603G green LED
  C2286      # KT-0603R red LED
  C70590     # X322524MOB4SI 24 MHz crystal
  # connectors
  C165948    # HRO TYPE-C-31-M-12
  C3020560   # GCT USB4105-GF-A
  # capacitors
  C138687    # 10u 50V X7R 1210
  C525654    # 47u 10V X5R 1210
  C2836438   # 22u 50V electrolytic
  C29823     # 4.7u 50V X7R 1206
  C15850     # 10u 25V X5R 0805
  C45783     # 22u 25V X5R 0805
  C19702     # 10u 10V X5R 0603
  C59461     # 22u 10V X5R 0603
  C82323     # ESD5Z6.0T1G VBUS TVS SOD-523
  C15849     # 1u 50V X5R 0603
  C23630     # 2.2u 16V X5R 0603
  C52923     # 1u 25V X5R 0402
  C1525      # 100n 16V X7R 0402
  C307331    # 100n 50V X7R 0402
  C15195     # 10n 50V X7R 0402
  C47118429  # 5.1n 50V X7R 0402
  C1664      # 330p 50V C0G 0603
  C576704    # 110p 50V C0G 0402
  C1567      # 47p 50V C0G 0402
  C1549      # 18p 50V C0G 0402
  C1548      # 15p 50V C0G 0402
  # resistors 0402 1 %
  C17168     # 0R
  C11702     # 1k
  C25867     # 1.5k
  C25879     # 2.2k (5V_BUS bleed: SS34 reverse leakage, host-powered mode)
  C270633    # 1.87k
  C25890     # 3.3k
  C25905     # 5.1k
  C2933105   # 5.23k
  C25744     # 10k
  C25752     # 12k
  C62740     # 15.4k
  C25768     # 22k
  C26978     # 41.2k
  C25792     # 47k
  C53398     # 53.6k
  C11626     # 54.9k (R34, FB top: 5.19 V, review 2026-11-17 D3)
  C25741     # 100k
  C25764     # 200k
  C26083     # 1M
)
lib="$ROOT/hw/JLCImport.kicad_sym"
for c in "${PARTS[@]}"; do
  if [ -f "$lib" ] && grep -q "\"$c\"" "$lib"; then continue; fi
  jlcimport-cli import "$c" -p "$ROOT/hw" --lib-name JLCImport --kicad-version 10
done
echo "import ok"
