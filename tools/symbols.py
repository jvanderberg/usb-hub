"""Project symbols for usb-hub: every IC, connector and odd-numbered discrete redrawn with symgen from its JLCImport
symbol (pin numbers = JLC footprint pad numbers; types from the datasheet pin tables). Writes hw/usb-hub.kicad_sym.
Imported by gen_sch.py (import kskills first)."""
import os
import kskills  # noqa: F401  (pins kicad-skills; must come first)
from schgen import SymLib, kicad_symbol_dir
from symgen import ic, fet, save_library, PI, PO, IN, OUT, BI, PA, NC, OC

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, 'hw')
LIB = os.path.join(HW, 'usb-hub.kicad_sym')
JLC = SymLib('JLCImport', os.path.join(HW, 'JLCImport.kicad_sym'))
DEV = SymLib('Device', os.path.join(kicad_symbol_dir(), 'Device.kicad_sym'))

TI = 'https://www.ti.com/lit/ds/symlink/%s.pdf'


def lcsc_ds(c):
    return 'https://www.lcsc.com/datasheet/%s.pdf' % c


def jlc(name):
    return JLC.get(name)


def build():
    S = {}
    # ---- LM5148 (SNVSC01 Table 6-1 p3-4). NC 1,2,22-24: "connect to GND at the exposed pad" -> stacked on AGND/EP.
    S['LM5148'] = ic('LM5148', 10.16,
                     left=[('VIN', ['12'], PI), None, ('EN', ['19'], IN), None, ('RT', ['4'], IN), ('CNFG', ['3'], IN),
                           ('PFM/SYNC', ['18'], IN), None, ('FB', ['6'], IN), ('EXTCOMP', ['5'], OUT), None,
                           ('VCC', ['9'], PO), ('VDDA', ['8'], PO), ('VCCX', ['16'], PI), None, ('PG', ['17'], OC)],
                     right=[('HO', ['13'], OUT), ('CBOOT', ['15'], PA), ('SW', ['14'], PA), ('LO', ['11'], OUT), None,
                            ('ISNS+', ['20'], IN), ('VOUT', ['21'], IN)],
                     bottom=[('AGND/EP', ['7', '25', '1', '2', '22', '23', '24'], PI), ('PGND', ['10'], PI)],
                     desc='80 V synchronous buck controller, VQFN-24 (RGY)', datasheet=TI % 'lm5148',
                     inherit=jlc('LM5148RGYR'))
    # ---- TPS25730D (SLVSGP9 pin table p5-6). VBUS_IN 23-25 and VBUS 32-33 shorted together (p9 note 2).
    S['TPS25730D'] = ic('TPS25730D', 12.7,
                        left=[('VBUS', ['23', '24', '25', '32', '33'], PI), None, ('CC1', ['28'], BI),
                              ('CC2', ['29'], BI), None, ('ADCIN1', ['2'], IN), ('ADCIN2', ['3'], IN),
                              ('ADCIN3', ['5'], IN), ('ADCIN4', ['7'], IN), None, ('FAULT_IN', ['18'], IN),
                              ('RESERVED', ['26'], IN), ('RESERVED', ['27'], IN), ('RESERVED', ['36'], IN), None,
                              # VIN_3V3 deliberately unpowered (power-design-pd-3v3.md s2.4): typed passive so ERC
                              # does not demand a driver for a supply input that is meant to stay open
                              ('VIN_3V3', ['38'], PA)],
                        right=[('PPHV', ['20', '21', '22'], PO), None, ('LDO_3V3', ['1'], PO), ('LDO_1V5', ['4'], PO),
                               None, ('I2C_SDA', ['8'], BI), ('I2C_SCL', ['9'], IN), None, ('~{SINK_EN}', ['19'], OC),
                               ('CAP_MIS', ['6'], OC), ('PLUG_EVENT', ['37'], OC), ('PLUG_FLIP', ['13'], OC),
                               ('~{DBG_ACC}', ['10'], OC), None, ('DRAIN', ['15', '30', '40'], PA)],
                        bottom=[('GND', ['11', '12', '14', '16', '17', '31', '34', '35', '39'], PI)],
                        desc='USB PD sink controller, strap-configured, integrated 7 A power path, WQFN-38',
                        datasheet=TI % 'tps25730', inherit=jlc('TPS25730DREFR'))
    # ---- TPS54202 (SLVSD26C Table 4-1 p3)
    S['TPS54202'] = ic('TPS54202', 6.35,
                       left=[('VIN', ['3'], PI), None, ('EN', ['5'], IN)],
                       right=[('BOOT', ['6'], PA), ('SW', ['2'], PO), None, ('FB', ['4'], IN)],
                       bottom=[('GND', ['1'], PI)], desc='28 V 2 A synchronous buck, SOT-23-6',
                       datasheet=TI % 'tps54202', inherit=jlc('TPS54202DDCR'))
    # ---- TPS3809K33 (SLVS228 Table 6-1)
    S['TPS3809K33'] = ic('TPS3809K33', 7.62,
                         left=[('VDD', ['3'], PI)], right=[('~{RESET}', ['2'], OUT)], bottom=[('GND', ['1'], PI)],
                         desc='Supply supervisor 2.93 V, push-pull active-low reset, SOT-23',
                         datasheet=TI % 'tps3809', inherit=jlc('TPS3809K33DBVR'))
    # ---- SY6863B3ABC (Rev 0.9C pin table p2); control pins both on the left, next to the hub's labels
    S['SY6863B3ABC'] = ic('SY6863B3ABC', 7.62,
                          left=[('IN', ['6'], PI), None, ('EN', ['4'], IN), ('OCB', ['3'], OC)],
                          right=[('OUT', ['1'], PO), None, ('ISET', ['5'], PA)],
                          bottom=[('GND', ['2'], PI)],
                          desc='5.5 V 3 A current-limited power switch, reverse blocking, OUT 28 V, SOT-23-6',
                          datasheet=lcsc_ds('C2687365'), inherit=jlc('SY6863B3ABC'))
    # ---- TPD4E05U06DQA (Table 4-2): channels in the receptacle's row order, GND and NC on the far side
    S['TPD4E05U06'] = ic('TPD4E05U06', 6.35,
                         left=[('D2+', ['4'], PA), ('D2-', ['5'], PA), None, ('D1+', ['1'], PA), ('D1-', ['2'], PA)],
                         # NC pins 7/6/10/9 sit opposite D2+/D2-/D1+/D1- and carry the same net for TI's
                         # straight-through routing ("Used for optional straight-through routing", Table 4-2 p4)
                         right=[('NC', ['7'], PA), ('NC', ['6'], PA), None, ('NC', ['10'], PA),
                                ('NC', ['9'], PA)],
                         bottom=[('GND', ['3', '8'], PI)],
                         desc='4-channel 0.5 pF ESD array, USON-10', datasheet=TI % 'tpd4e05u06',
                         inherit=jlc('TPD4E05U06DQAR_C138714'))
    # ---- ESTVS2200DRVR (Rev 1.1 p2): GND 1-3 + pad, IO 4-6
    S['ESTVS2200'] = ic('ESTVS2200', 2.54, left=[('IO', ['4', '5', '6'], PA)],
                        right=[('GND', ['1', '2', '3', '7'], PA)], ref='D',
                        desc='22 V flat-clamp surge TVS, SON-6 (TVS2200 second source)',
                        datasheet=lcsc_ds('C42400188'), inherit=jlc('ESTVS2200DRVR'))
    # ---- hubs
    hub_a_right = [None, None]                          # two empty rows clear the vertical supply-pin names
    for n in range(1, 8):
        g = [('USBDN%d_DP' % n, [str({1: 2, 2: 4, 3: 7, 4: 9, 5: 12, 6: 54, 7: 56}[n])], BI),
             ('USBDN%d_DM' % n, [str({1: 1, 2: 3, 3: 6, 4: 8, 5: 11, 6: 53, 7: 55}[n])], BI)]
        pw = ('PRTPWR%d' % n, [str({1: 29, 2: 26, 3: 23, 4: 20, 5: 30, 6: 39, 7: 36}[n])], OUT)
        # OCS: input with an internal 35-90 uA pull-up to 3.3 V (2517 p12, Table 8-2 p49), driven only by the
        # switches' open-drain OCB: typed passive (the pull-up is the pin's own weak driver) so ERC sees a driver
        oc = ('OCS%d_N' % n, [str({1: 28, 2: 27, 3: 22, 4: 21, 5: 35, 6: 38, 7: 37}[n])], PA)
        g += [oc, pw] if n == 7 else [pw, oc]           # port 7: PRTPWR7 level with hub B's VBUS_DET
        hub_a_right += g + ([None] if n < 6 else [None, None, None] if n == 6 else [])
    S['USB2517'] = ic('USB2517', 17.78, top_pitch=5.08,
                      left=[None, None, ('USBUP_DP', ['59'], BI), ('USBUP_DM', ['58'], BI), None,
                            ('VBUS_DET', ['44'], IN), ('RESET_N', ['43'], IN), None,
                            ('XTAL1/CLKIN', ['61'], IN), ('XTAL2', ['60'], OUT), ('RBIAS', ['63'], PA), None,
                            ('CFG_SEL2', ['13'], IN), ('SCL/CFG_SEL0', ['41'], BI), ('HS_IND/CFG_SEL1', ['42'], BI),
                            ('SDA/NON_REM1', ['40'], BI), ('SUSP_IND/NON_REM0', ['45'], BI),
                            ('LED_B3/GANG_EN', ['34'], BI), ('LED_B1/BOOST0', ['50'], BI),
                            ('LED_B2/BOOST1', ['48'], BI), None,
                            ('LED_A1/PRT_SWP1', ['51'], BI), ('LED_A2/PRT_SWP2', ['49'], BI),
                            ('LED_A3/PRT_SWP3', ['47'], BI), ('LED_A4/PRT_SWP4', ['33'], BI),
                            ('LED_A5/PRT_SWP5', ['31'], BI), ('LED_A6/PRT_SWP6', ['17'], BI),
                            ('LED_A7/PRT_SWP7', ['15'], BI), None,
                            ('LED_B4', ['32'], OUT), ('LED_B5', ['18'], OUT), ('LED_B6', ['16'], OUT),
                            ('LED_B7', ['14'], OUT), None, ('TEST', ['19'], IN)],
                      right=hub_a_right,
                      top=[('VDDA33', ['5', '10', '52', '57'], PI), ('VDD33CR', ['24'], PI), ('VDD33', ['46'], PI),
                           ('VDD33PLL', ['64'], PI), ('VDD18', ['25'], PO), ('VDD18PLL', ['62'], PO)],
                      bottom=[('VSS', ['65'], PI)],
                      desc='USB 2.0 7-port multi-TT hub controller, QFN-64 9x9', datasheet=lcsc_ds('C1521556'),
                      inherit=jlc('USB2517-JZX'))
    hub_b_right = [None]
    for n in range(1, 5):
        hub_b_right += [('USBDP_DN%d' % n, [str({1: 2, 2: 4, 3: 7, 4: 9}[n])], BI),
                        ('USBDM_DN%d' % n, [str({1: 1, 2: 3, 3: 6, 4: 8}[n])], BI),
                        ('PRTPWR%d/BC_EN%d' % (n, n), [str({1: 12, 2: 16, 3: 18, 4: 20}[n])], OUT),
                        ('OCS%d_N' % n, [str({1: 13, 2: 17, 3: 19, 4: 21}[n])], PA)] + ([None] if n < 4 else [])  # IPU, as hub A
    S['USB2514B'] = ic('USB2514B', 20.32, top_pitch=5.08,
                       left=[None, ('USBDP_UP', ['31'], BI), ('USBDM_UP', ['30'], BI), None, ('VBUS_DET', ['27'], IN),
                             None, ('RESET_N', ['26'], IN), None, ('XTALIN/CLKIN', ['33'], IN),
                             ('XTALOUT', ['32'], OUT), ('RBIAS', ['35'], PA), None,
                             ('SCL/CFG_SEL0', ['24'], BI), ('HS_IND/CFG_SEL1', ['25'], BI),
                             ('SDA/NON_REM1', ['22'], BI), ('SUSP_IND/NON_REM0', ['28'], BI), None,
                             ('TEST', ['11'], IN), None, ('CRFILT', ['14'], PO), ('PLLFILT', ['34'], PO)],
                       right=hub_b_right,
                       top=[('VDDA33', ['5', '10', '29', '36'], PI), ('VDD33', ['15', '23'], PI)],
                       bottom=[('VSS', ['37'], PI)],
                       desc='USB 2.0 4-port multi-TT hub controller, QFN-36 6x6', datasheet=lcsc_ds('C16251'),
                       inherit=jlc('USB2514B-AEZC-TR'))
    # ---- USB-C receptacles (connector pins passive). DFP: downstream ports; UFP: HOST (row order suits its Rd)
    tc = jlc('TYPE-C-31-M-12')
    sbu = ('SBU', ['A8', 'B8'], NC)
    gnd = ('GND', ['A1B12', 'B1A12'], PA)
    shield = ('SHIELD', ['1', '2', '3', '4'], PA)
    vbus = ('VBUS', ['A4B9', 'B4A9'], PA)
    dp, dm = ('D+', ['A6', 'B6'], PA), ('D-', ['A7', 'B7'], PA)
    cc1, cc2 = ('CC1', ['A5'], PA), ('CC2', ['B5'], PA)
    S['TYPE-C-31-M-12'] = ic('TYPE-C-31-M-12', 5.08, ref='J',
                             right=[vbus, None, None, None, cc1, cc2, None, dp, dm, None, sbu, None, gnd, shield],
                             desc='USB-C 2.0 receptacle, 16 pin, through-hole shell legs (DFP drawing)',
                             datasheet=lcsc_ds('C165948'), inherit=tc)
    S['TYPE-C-31-M-12_UFP'] = ic('TYPE-C-31-M-12_UFP', 5.08, ref='J',
                                 right=[vbus, None, None, None, dm, dp, None, cc2, cc1, None, sbu, None, gnd, shield],
                                 desc='USB-C 2.0 receptacle, 16 pin, through-hole shell legs (UFP drawing)',
                                 datasheet=lcsc_ds('C165948'), inherit=tc)
    S['USB4105-GF-A'] = ic('USB4105-GF-A', 5.08, ref='J',
                           right=[('VBUS', ['A4', 'A9', 'B4', 'B9'], PA), None, ('CC1', ['A5'], PA),
                                  ('CC2', ['B5'], PA), None, ('D+/D-', ['A6', 'B6', 'A7', 'B7'], NC),
                                  ('SBU', ['A8', 'B8'], NC), None, ('GND', ['A1', 'A12', 'B1', 'B12'], PA),
                                  ('SHIELD', ['1', '2', '3', '4'], PA)],
                           desc='USB-C 2.0 receptacle, 5 A VBUS, through-hole stakes (PD input)',
                           datasheet=lcsc_ds('C3020560'), inherit=jlc('USB4105-GF-A'))
    # ---- FETs renumbered to the JLC footprints (pad 9 = drain tab)
    S['CSD17505Q5A'] = fet(DEV.get('Q_NMOS'), 'CSD17505Q5A', D=['5', '6', '7', '8', '9'], G=['4'], S=['1', '2', '3'],
                           desc='30 V N-MOSFET, SON 5x6 (high side)', inherit=jlc('CSD17505Q5A'))
    S['CSD17573Q5B'] = fet(DEV.get('Q_NMOS'), 'CSD17573Q5B', D=['5', '6', '7', '8', '9'], G=['4'], S=['1', '2', '3'],
                           desc='30 V N-MOSFET, SON 5x6 (low side)', inherit=jlc('CSD17573Q5B'))
    S['AO3401A'] = fet(DEV.get('Q_PMOS'), 'AO3401A', D=['3'], G=['1'], S=['2'], desc='-30 V P-MOSFET, SOT-23',
                       inherit=jlc('AO3401A'))
    # ---- red LED: its JLC footprint has pad 1 = anode (Device:LED is 1 = K), so it gets its own symbol
    S['KT-0603R'] = ic('KT-0603R', 2.54, left=[('A', ['1'], PA)], right=[('K', ['2'], PA)], ref='D',
                       desc='Red LED 0603 (pad 1 = anode)', datasheet=lcsc_ds('C2286'), inherit=jlc('KT-0603R'))
    for name in ('CSD17505Q5A', 'CSD17573Q5B'):           # TI's own datasheet over the imported link
        for q in S[name].nodes('property'):
            if str(q[1]) == 'Datasheet':
                q[2] = TI % name.lower()
    for q in S['AO3401A'].nodes('property'):
        if str(q[1]) == 'Datasheet':
            q[2] = lcsc_ds('C15127')
    return S


def write():
    S = build()
    save_library(S, LIB, 'usb-hub', project_dir=HW)
    return S


if __name__ == '__main__':
    write()
    print('wrote', LIB)
