#!/usr/bin/env bash
# Rebuild hw/ from the generators. Stops at the first failed stage (R28).
# Stages: JLC library import (skips parts already imported) -> schematic -> netlist -> board from the netlist ->
# stackup, rules and net classes -> routing (tools/route_plan.py). Parts not in tools/place.json are staged off the board outline by new_board.py.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
K="$(python3 -c 'import sys; sys.path.insert(0, "'"$ROOT"'/tools"); import kskills; print(kskills.SCRIPTS)' 2>/dev/null)"
HW="$ROOT/hw"
KICAD_CLI="${KICAD_CLI:-$(command -v kicad-cli || echo /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli)}"
trap 'python3 "$K/kicad_locks.py" status "$HW" --clean >/dev/null || true' EXIT
rm -f "$HW/net.xml"
"$ROOT/tools/import_parts.sh"
# project footprints: thermal vias in the exposed pads, paste windows clear of the drills (paste_clear.py)
rm -f "$HW"/usb-hub.pretty/*_ThermalVias.kicad_mod
python3 "$ROOT/tools/thermal_fp.py"
for f in TPS25730DREFR ESTVS2200DRVR LM5148RGYR CSD17505Q5A USB2517-JZX USB2514B-AEZC-TR; do
    test -s "$HW/usb-hub.pretty/${f}_ThermalVias.kicad_mod"
done
python3 "$ROOT/tools/gen_sch.py"
"$KICAD_CLI" sch export netlist --format kicadxml -o "$HW/net.xml" "$HW/usb-hub.kicad_sch"
test -s "$HW/net.xml"
python3 "$K/netspec.py" check "$ROOT/tools/nets.json" "$HW/net.xml"
python3 "$K/new_board.py" "$HW/net.xml" "$HW/usb-hub.kicad_pcb" --layers 4 --outline 85x85 --origin 100,100 \
    --corner-r 2 --refs fab --placement "$ROOT/tools/place.json"
# Net classes. USB: every D+/D- pair (hub downstream ports incl. the hub A -> hub B link, HOST upstream).
# Power: the input/bus rails and every switched port VBUS. HighCurrent: the LM5148 switch node and the
# inductor-to-shunt node (the 17 A path that is not already a Power rail). Clearance 0.2 mm: the LM5148 QFN pads
# (SW 14 / CBOOT 15, ISNS+ 20 / EN 19 / VOUT 21) sit 0.22 mm apart, so 0.3 mm could never pass DRC.
# USB pair: track 0.26 / gap 0.15 mm, ~90 ohm edge-coupled microstrip on L1 over L2 (JLC04161H-7628, h 0.2104 mm,
# Er 4.4, 15 um mask: layout-plan.md s3). An estimate: TO CONFIRM WITH JLC's IMPEDANCE CALCULATOR before ordering.
# board_setup.py has no diff-pair keys, so tools/netclass_dp.py sets the pair width / gap right after it.
python3 "$K/board_setup.py" "$HW/usb-hub.kicad_pro" --stackup JLC04161H-7628 --finish ENIG \
    --class 'USB:track=0.26,clearance=0.15' --class 'Power:track=0.8,clearance=0.2' \
    --class 'HighCurrent:track=2.0,clearance=0.2' \
    --pattern 'USB=*_DN?_D[PM]' --pattern 'USB=*/USB_UP_D[PM]' \
    --assign 'Power=VIN,5V_BUS,/power_in/PD_VBUS' --pattern 'Power=/port*/VBUS' \
    --assign 'HighCurrent=/buck_5v/5V_SW,/buck_5v/5V_ISNS'
python3 "$ROOT/tools/netclass_dp.py" "$HW/usb-hub.kicad_pro" USB 0.26 0.15
rm -f "$HW/net.xml"

# Routing (router.py, no autorouter): dump the unrouted board, then apply tools/route_plan.py onto it. The routed
# board in HEAD (if it has copper) gives the tracks/vias/zones their ids back, so an unchanged plan rebuilds the same
# bytes. The stage fails on a missing "wrote" line or any VIOLATION / REJECTED line (new-design.md s6, R28).
. "$K/kicad_env.sh"
REVIEW="$(cd "$K/../../kicad-board-review/scripts" && pwd)"
B="$ROOT/build"
mkdir -p "$B"
rm -rf "$B/pack0" "$B/router.log" "$B/previous.kicad_pcb"
"$KICAD_PYTHON" "$REVIEW/boarddump.py" "$HW/usb-hub.kicad_pcb" "$B/pack0" > "$B/boarddump.log" 2>&1 \
    || { cat "$B/boarddump.log"; exit 1; }
test -s "$B/pack0/board.json"
PREV=()
if git -C "$ROOT" show HEAD:hw/usb-hub.kicad_pcb > "$B/previous.kicad_pcb" 2>/dev/null \
        && grep -qE '^[[:space:]]*\((segment|via|zone)[[:space:]]' "$B/previous.kicad_pcb"; then
    PREV=(--previous "$B/previous.kicad_pcb")
fi
rc=0
"$PY" "$K/router.py" apply "$HW/usb-hub.kicad_pcb" "$B/pack0/board.json" "$ROOT/tools/route_plan.py" \
    ${PREV[@]+"${PREV[@]}"} > "$B/router.log" 2>&1 || rc=$?
tail -3 "$B/router.log"
grep -q '^wrote ' "$B/router.log" || { cat "$B/router.log"; echo "router did not write the board (exit $rc)"; exit 1; }
if grep -E '^ +(VIOLATION|REJECTED)' "$B/router.log"; then echo "router rejected items: fix tools/route_plan.py"; exit 1; fi
[ "$rc" -eq 0 ] || { echo "router exited $rc"; exit 1; }
echo "build ok"
