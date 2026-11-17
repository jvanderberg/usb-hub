#!/usr/bin/env python3
"""Set a net class's differential-pair width / gap in the .kicad_pro (through kicad_sexpr.Project).

  netclass_dp.py PROJECT.kicad_pro CLASS WIDTH GAP

board_setup.py (kicad-skills 0.2.1) takes only track / clearance / via / drill per class, so the USB pair geometry
is applied by this step right after it (tools/build.sh). Exits 1 if the class does not exist.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kskills  # noqa: E402,F401  (puts kicad-skills' scripts on sys.path, checks the pinned revision)
from kicad_sexpr import Project  # noqa: E402


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    pro, name, w, g = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
    p = Project.load(pro)
    if not any(c.get('name') == name for c in p.netclasses()):
        sys.exit('net class %s is not in %s' % (name, pro))
    p.netclass(name, diff_pair_width=w, diff_pair_gap=g)
    p.save()
    c = next(c for c in Project.load(pro).netclasses() if c.get('name') == name)
    assert (c['diff_pair_width'], c['diff_pair_gap']) == (w, g), c
    print('netclass_dp: %s diff pair %.3f / %.3f mm in %s' % (name, w, g, pro))


if __name__ == '__main__':
    main()
