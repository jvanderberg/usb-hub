#!/usr/bin/env bash
# Rebuild hw/ from the generators. Stops at the first failed stage (R28).
# Stages: JLC library import (skips parts already imported) -> schematic -> netlist -> board from the netlist ->
# stackup, rules and net classes. Parts not in tools/place.json are staged off the board outline by new_board.py.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
K="$(python3 -c 'import sys; sys.path.insert(0, "'"$ROOT"'/tools"); import kskills; print(kskills.SCRIPTS)' 2>/dev/null)"
HW="$ROOT/hw"
KICAD_CLI="${KICAD_CLI:-$(command -v kicad-cli || echo /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli)}"
trap 'python3 "$K/kicad_locks.py" status "$HW" --clean >/dev/null || true' EXIT
rm -f "$HW/net.xml"
"$ROOT/tools/import_parts.sh"
python3 "$ROOT/tools/gen_sch.py"
"$KICAD_CLI" sch export netlist --format kicadxml -o "$HW/net.xml" "$HW/usb-hub.kicad_sch"
test -s "$HW/net.xml"
python3 "$K/netspec.py" check "$ROOT/tools/nets.json" "$HW/net.xml"
python3 "$K/new_board.py" "$HW/net.xml" "$HW/usb-hub.kicad_pcb" --layers 4 --outline 70x70 --origin 100,100 \
    --corner-r 2 --refs fab --placement "$ROOT/tools/place.json"
# Net classes. USB: every D+/D- pair (hub downstream ports incl. the hub A -> hub B link, HOST upstream).
# Power: the input/bus rails and every switched port VBUS. HighCurrent: the LM5148 switch node and the
# inductor-to-shunt node (the 17 A path that is not already a Power rail). Clearance 0.2 mm: the LM5148 QFN pads
# (SW 14 / CBOOT 15, ISNS+ 20 / EN 19 / VOUT 21) sit 0.22 mm apart, so 0.3 mm could never pass DRC.
python3 "$K/board_setup.py" "$HW/usb-hub.kicad_pro" --stackup JLC04161H-7628 --finish ENIG \
    --class 'USB:track=0.2,clearance=0.15' --class 'Power:track=0.8,clearance=0.2' \
    --class 'HighCurrent:track=2.0,clearance=0.2' \
    --pattern 'USB=*_DN?_D[PM]' --pattern 'USB=*/USB_UP_D[PM]' \
    --assign 'Power=VIN,5V_BUS,/power_in/PD_VBUS' --pattern 'Power=/port*/VBUS' \
    --assign 'HighCurrent=/buck_5v/5V_SW,/buck_5v/5V_ISNS'
rm -f "$HW/net.xml"
echo "build ok"
