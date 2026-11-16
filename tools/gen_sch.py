"""Generate the usb-hub schematic. Stage 0: project skeleton (mounting holes only).
Run: python3 tools/gen_sch.py   (from anywhere)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kskills  # noqa: F401  (pins kicad-skills; must come first)
from schgen import Sch, kicad_symbol_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, 'hw')

s = Sch('usb-hub', paper='A3', title='10-port USB-C bench hub', rev='0')
s.lib('Mechanical', os.path.join(kicad_symbol_dir(), 'Mechanical.kicad_sym'))
# 4x M3 into heat-set inserts in the printed case (requirements s5). NPTH, not in BOM / position file.
for i in range(4):
    s.add('Mechanical:MountingHole', 'H%d' % (i + 1), 'M3', 30.48 + 15.24 * i, 25.4,
          footprint='MountingHole:MountingHole_3.2mm_M3', in_bom=False)
assert not s.collisions()
s.write(os.path.join(HW, 'usb-hub.kicad_sch'))
