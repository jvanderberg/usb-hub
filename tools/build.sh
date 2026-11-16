#!/usr/bin/env bash
# Rebuild hw/ from the generators. Stops at the first failed stage (R28).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
K="$(python3 -c 'import sys; sys.path.insert(0, "'"$ROOT"'/tools"); import kskills; print(kskills.SCRIPTS)' 2>/dev/null)"
HW="$ROOT/hw"
trap 'python3 "$K/kicad_locks.py" status "$HW" --clean >/dev/null || true' EXIT
rm -f "$HW/net.xml"
python3 "$ROOT/tools/gen_sch.py"
kicad-cli sch export netlist --format kicadxml -o "$HW/net.xml" "$HW/usb-hub.kicad_sch"
test -s "$HW/net.xml"
python3 "$K/new_board.py" "$HW/net.xml" "$HW/usb-hub.kicad_pcb" --layers 4 --outline 70x70 --origin 100,100 \
    --corner-r 2 --refs fab --placement "$ROOT/tools/place.json"
python3 "$K/board_setup.py" "$HW/usb-hub.kicad_pro" --stackup JLC04161H-7628 --finish ENIG \
    --class 'USB:track=0.2,clearance=0.15' --class 'Power:track=0.8,clearance=0.2' --class 'HighCurrent:track=2.0,clearance=0.3'
rm -f "$HW/net.xml"
echo "build ok"
