"""True common-datum sections for D2.6:
1) connector-section.svg: TB1 section (production panel STL, registered Mac, schematic cable).
2) d25-vs-d26-usb-audio-comparison.svg: side-by-side XZ pocket overlay + YZ X=41.30 section
   comparing real exported D2.5 (2.00 mm / 0.20 mm skin) vs D2.6 (2.60 mm / 0.80 mm skin)
   against the photographed USB-A/Audio T-block.
"""
from hashlib import sha256
from pathlib import Path
import json
import numpy as np
import trimesh as tm
from check_geometry import s,parts,bounds,md,qa,owner,BOARD_LABEL

def stl_to_desk(stl_path, panel_solid):
    bed=qa.k.qa.solid(tm.load_mesh(stl_path,process=False))
    on_bed_native=panel_solid.rotate([-90,0,0])
    return bed.translate(bounds(on_bed_native)[0].tolist()).rotate([90,0,0])

def make_tb1_section(panel, mac, desk_stl, load):
    fit=load('ports-fit.json');row=fit['ports']['TB1'];x,z=row['axis_xz_mm']
    face,lip,back=row['face_y_mm'],row['socket_lip_y_mm'],row['mask_back_y_mm']
    skin,air=row['mask_skin_thickness_mm'],row['nominal_axial_gap_mask_to_bezel_mm']
    stl=s.OUT/'print/02-flat-rear-panel.stl'
    to_yz=[[0,1,0,0],[0,0,1,0],[1,0,0,0]]
    clip=md.CrossSection.square([11.5,8.5]).translate([face-6.55,z-4.25])
    def cut(m):return m.transform(to_yz).slice(x)^clip
    plastic=cut(desk_stl);native=cut(panel);board=cut(mac)
    diff=(plastic-native).area()+(native-plastic).area()
    assert diff<.001 and board.area()>1.
    qx,qz=row['masked_bezel_probe_xz_mm'];assert abs(qx-x)<.0001
    p=desk_stl.ray_cast([x,60,qz],[x,53,qz]);b=mac.ray_cast([x,60,qz],[x,53,qz])
    assert np.allclose([h.position[1] for h in p],[face,back],atol=.0001) and abs(b[0].position[1]-lip)<.0001
    fx,cz,k=320,299,43.
    X=lambda y:fx+(y-face)*k;Y=lambda zz:cz-(zz-z)*k
    def path(cs):
        return ' '.join('M'+' L'.join(f'{X(y):.2f},{Y(zz):.2f}' for y,zz in pts)+' Z' for pts in cs.to_polygons())
    def text(x,y,value,cls='',anchor='start'):
        return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{value}</text>'
    def mm(n):return f'{n:.2f}'.replace('.',',')
    def rect_mm(x1,y1,x2,y2):
        return f'<rect x="{X(x1):.2f}" y="{Y(y2):.2f}" width="{(x2-x1)*k:.2f}" height="{(y2-y1)*k:.2f}" fill="#9fbeb3" stroke="#506e63" stroke-width="1"/>'
    L=1.20;stop=lip+L;tip=lip-1.16
    shaft=rect_mm(tip,z+1.215-.16,stop,z+1.215)+rect_mm(tip,z-1.215,stop,z-1.215+.16)
    barrel=f'<path d="M{X(stop):.2f} {Y(z+3.5):.2f} h79 q16 0 16 17 v267 q0 17 -16 17 h-79 Z" fill="#c7ddcf" stroke="#6d8b7c" stroke-width="1.5"/>'
    barrel+=f'<path d="M{X(stop)+95:.2f} {cz} h110" fill="none" stroke="#a5bfb1" stroke-width="30"/>'
    field=mm(row['field_thickness_mm'])
    lip2=150;k2=180;back2=lip2+air*k2;face2=back2+skin*k2
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="930" height="610" viewBox="0 0 930 610" role="img" aria-labelledby="d26secTitle d26secDesc">
<title id="d26secTitle">D2.6: справжній розріз через капсулу Thunderbolt (потовщена стінка 0,90 мм)</title>
<desc id="d26secDesc">Пластик перекриває широкий чорний обідок стінкою 0,90 мм (сумарний відступ 1,01 мм — як у заводській кришці Apple ~1,0 мм), а задній спільний паз TB поглиблено до Y=55,56 мм.</desc>
<defs><style>text{{font-family:'Segoe UI',Arial,sans-serif;fill:#20392e}}.ey{{font-size:12px;font-weight:650;letter-spacing:1.3px}}.head{{font-size:29px;font-weight:650}}.sub{{font-size:15px}}.lab{{font-size:16px;font-weight:650}}.tiny{{font-size:13px}}</style>
<pattern id="d26hatch" width="7" height="7" patternUnits="userSpaceOnUse"><rect width="7" height="7" fill="#e6c28b"/><path d="M-1 1 1-1 M0 7 7 0 M6 8 8 6" stroke="#bd965f" stroke-width="1"/></pattern>
<clipPath id="d26clip"><rect x="33" y="130" width="477" height="324" rx="5"/></clipPath></defs>
<rect width="930" height="610" rx="12" fill="#f9f9f3"/>
{text(27,30,'D2.6   /   ПОТОВЩЕНА ЗАДНЯ ПАНЕЛЬ (+0,60 ММ)   /   РОЗРІЗ ЧЕРЕЗ THUNDERBOLT 1','ey')}
{text(27,69,'Міцна стінка 0,90 мм перед TB — рівень заводської Apple','head')}
{text(27,95,'Розріз друкованої панелі 02 (поле 2,60 мм) і оновленої моделі плати. Кабель заходить праворуч.','sub')}
<path d="M27 111H903" stroke="#acbcb1"/><rect x="27" y="123" width="489" height="338" rx="8" fill="#edf1e8"/>
<g clip-path="url(#d26clip)">
<path d="{path(board)}" fill="#475c52" stroke="#34473c" stroke-width="1" fill-rule="evenodd"/>
<path d="{path(plastic)}" fill="url(#d26hatch)" stroke="#9a784a" stroke-width="1" fill-rule="evenodd"/>
{shaft}{barrel}
<path d="M{fx},120 V461" stroke="#197b56" stroke-width="1.5" stroke-dasharray="5 4"/>
<path d="M52,{cz} H493" stroke="#64796d" stroke-width=".8" stroke-dasharray="4 5" opacity=".75"/>
<path d="M{X(lip)-16:.2f} {Y(qz):.2f} H{X(face)+8:.2f}" stroke="#a1412d" stroke-width="1.6" stroke-dasharray="3 2"/>
</g>
{text(43,145,'УСЕРЕДИНІ','ey')}{text(499,145,'ЗОВНІ','ey','end')}
{text(541,150,'Пластик — штрихування','lab')}
{text(541,174,'Капсула 9,10 × 3,30 мм; стінка перед TB — '+mm(skin)+' мм.','tiny')}
{text(541,194,'Спільний паз TB поглиблено до Y = 55,56 мм','tiny')}
{text(541,214,'(стінка 1,80 мм; суцільне поле — '+field+' мм).','tiny')}
{text(541,253,'Гніздо й екран — темно-зеленим','lab')}
{text(541,277,'Широка рамка TB заходить у глибоку кишеню,','tiny')}
{text(541,297,'а задній екран (Y = 55,11) має +0,45 мм запасу.','tiny')}
{text(541,317,'Номінальне повітря перед TB: '+mm(air)+' мм.','tiny')}
{text(541,355,'Кабель — світло-зеленим, приклад','lab')}
{text(541,379,'За шийки '+mm(L)+' мм широке плече лишається','tiny')}
{text(541,399,'на '+mm(stop-face)+' мм перед лицем. Заводський Apple має','tiny')}
{text(541,419,'~1,0 мм стінку — стандартні TB-кабелі стають штатно.','tiny')}
<path d="M27 476H903" stroke="#acbcb1"/>
{text(27,500,'ЗБІЛЬШЕНО ВЗДОВЖ ОСІ   /   ЧЕРВОНИЙ ШТРИХ НА РОЗРІЗІ','ey')}
<rect x="51" y="520" width="{lip2-51:.2f}" height="20" fill="#475c52"/>
<rect x="{lip2}" y="520" width="{back2-lip2:.2f}" height="20" fill="#f9f9f3" stroke="#96a89b"/>
<rect x="{back2:.2f}" y="520" width="{face2-back2:.2f}" height="20" fill="url(#d26hatch)" stroke="#9a784a"/>
<path d="M{face2:.2f} 511v39" stroke="#197b56" stroke-width="1.6" stroke-dasharray="4 3"/>
{text(51,560,'Рамка','tiny')}{text(142,560,'Повітря','tiny')}{text(218,560,'Пластик 0,90 мм','tiny')}
{text(368,530,'Торець TB → лице: '+mm(air)+' + '+mm(skin)+' = '+mm(face-lip)+' мм','lab')}
{text(368,552,'Номінали CAD (9 шарів по 0,10 мм); перевіряється приміркою.','tiny')}
{text(27,588,'Базис: X = −19,05 мм, фасад Y = 57,36 мм. Фізичний друк D2.6 ще не виконано й не прийнято.','tiny')}
</svg>'''
    (s.OUT/'connector-section.svg').write_text(svg+'\n',encoding='utf8')
    digest=lambda path:sha256(path.read_bytes()).hexdigest()
    report={'revision':'D2.6','plane':'desk X through TB1; Y increases toward cable, Z up',
            'cut_x_mm':x,'axis_z_mm':z,'rim_witness_xz_mm':[qx,qz],'socket_lip_y_mm':lip,
            'panel_mask_back_y_mm':back,'panel_outer_face_y_mm':face,
            'mask_thickness_mm':skin,'air_between_mask_and_bezel_mm':air,
            'symmetric_difference_of_released_STL_and_native_facet_cross_sections_mm2':round(diff,7),
            'files_sha256':{str(p.relative_to(s.OUT)).replace(chr(92),'/'):digest(p) for p in [
                s.OUT/'cad-validation.json',s.OUT/'ports-fit.json',s.OUT/'geometry/panel.glb',stl,
                s.OUT/'board-study/registered-board.stl',s.OUT/'connector-section.svg']}}
    (s.OUT/'connector-section.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('TB1 cut at X',x,'diff mm2',diff)

def make_usb_audio_comparison(panel26, mac, desk_stl26):
    d25_dir=s.CAD/'prototype-d25'
    stl25=d25_dir/'print/02-flat-rear-panel.stl'
    # Align D2.5 STL using D2.5's own CAD bounds (FACE=56.76), NOT D2.6's thickened FACE=57.36!
    d25_val=json.loads((d25_dir/'cad-validation.json').read_text(encoding='utf8'))
    d25_name,=d25_val['groups']['panel']
    d25_bb=d25_val['bodies'][d25_name]['bbox']
    # In rotate([-90,0,0]), (x,y,z)->(x,z,-y), so bed min = [xmin, zmin, -ymax].
    bed25_min=[d25_bb['min'][0], d25_bb['min'][2], -d25_bb['max'][1]]
    bed25=qa.k.qa.solid(tm.load_mesh(stl25,process=False))
    desk_stl25=bed25.translate(bed25_min).rotate([90,0,0])
    assert abs(float(bounds(desk_stl25)[1,1])-56.76)<.005,bounds(desk_stl25)
    assert abs(float(bounds(desk_stl26)[1,1])-s.FACE)<.005,bounds(desk_stl26)
    # Measure exact 3D interference volume of photographed board vs D2.5 and D2.6 panels
    v25=round(float((desk_stl25^mac).volume()),3)
    v26=round(float((desk_stl26^mac).volume()),5)
    assert v25>150. and v26<.0005,(v25,v26)

    # 1) Left graphic: XZ interior pocket slices at Y=55.80 (inside the deep pockets)
    clip_xz=md.CrossSection.square([44.,32.]).translate([41.3-22., -41.5])
    def slice_xz(solid, y):
        cs=solid.rotate([90,0,0]).slice(y)
        return cs^clip_xz
    slab=md.CrossSection.square([42.,29.]).translate([41.3-21.,-39.5])
    void25=slab-slice_xz(desk_stl25, 55.80)
    void26=slab-slice_xz(desk_stl26, 55.80)
    board_bezels=slice_xz(mac, 56.25)   # USB-A bezels + rectangular audio block
    board_tbridge=slice_xz(mac, 56.05)  # includes silver T-bridge
    board_collar=slice_xz(mac, 56.85)   # protruding Ø5.00 audio collar
    hole25=slab-slice_xz(desk_stl25, 56.70)
    hole26=slab-slice_xz(desk_stl26, s.FACE-.06)

    lx0,ly0,lk=44.,510.,11.2
    def LX(x):return lx0+(x-20.)*lk
    def LY(z):return ly0-(z-11.)*lk
    def path_xz(cs):
        out=[]
        for pts in cs.to_polygons():
            out.append('M'+' L'.join(f'{LX(px):.2f},{LY(-pz):.2f}' for px,pz in pts)+' Z')
        return ' '.join(out)

    # 2) Right graphics: YZ vertical cross-section at X = 41.30 mm (audio + T-bridge centerline!)
    to_yz=[[0,1,0,0],[0,0,1,0],[1,0,0,0]]
    clip_yz=md.CrossSection.square([8.5,31.]).translate([51.5,12.0])
    def cut_yz(m):return m.transform(to_yz).slice(41.30)^clip_yz
    b_yz=cut_yz(mac)
    p25_yz=cut_yz(desk_stl25)
    p26_yz=cut_yz(desk_stl26)
    hit25_yz=p25_yz^b_yz
    hit26_yz=p26_yz^b_yz
    assert hit25_yz.area()>5. and hit26_yz.area()<.001,(hit25_yz.area(),hit26_yz.area())

    def yz_group(plastic_cs, hit_cs, face_y, card_x, title, badge, badge_col, notes):
        scale = 15.0
        gx = card_x + 20.0
        gy = 602.0
        YX = lambda y: gx + (y - 53.0) * scale
        YY = lambda z: gy - (z - 15.5) * scale
        def pyz(cs):
            return ' '.join('M' + ' L'.join(f'{YX(y):.2f},{YY(z):.2f}' for y, z in pts) + ' Z' for pts in cs.to_polygons())
        face_x = YX(face_y)
        line_start = YX(max(face_y, 57.04)) + 4.0
        callouts = []
        for z_mm, label, col in notes:
            yy = YY(z_mm)
            callouts.append(f'<line x1="{line_start:.1f}" y1="{yy:.1f}" x2="{card_x + 112:.1f}" y2="{yy:.1f}" stroke="{col}" stroke-width="1" stroke-dasharray="2 2"/>')
            callouts.append(f'<text x="{card_x + 116:.1f}" y="{yy + 4:.1f}" class="micro" fill="{col}" font-weight="600">{label}</text>')
        face_txt = f'Фасад Y={face_y:.2f}'.replace('.', ',')
        return f'''<g>
<rect x="{card_x}" y="120" width="250" height="532" rx="8" fill="#edf1e8" stroke="#c3cfc7"/>
<text x="{card_x + 14}" y="146" class="lab">{title}</text>
<rect x="{card_x + 14}" y="156" width="196" height="22" rx="4" fill="{badge_col}"/>
<text x="{card_x + 112}" y="171" class="badge" text-anchor="middle">{badge}</text>
<path d="{pyz(b_yz)}" fill="#475c52" stroke="#2d3e35" stroke-width="1" fill-rule="evenodd"/>
<path d="{pyz(plastic_cs)}" fill="url(#cmpHatch)" stroke="#8d6b3b" stroke-width="1" fill-rule="evenodd" opacity="0.90"/>
<path d="{pyz(hit_cs)}" fill="#d93829" stroke="#8a1911" stroke-width="1.2" fill-rule="evenodd" opacity="0.88"/>
<line x1="{face_x:.2f}" y1="190" x2="{face_x:.2f}" y2="612" stroke="#197b56" stroke-width="1.3" stroke-dasharray="4 3"/>
<text x="{face_x:.1f}" y="628" class="micro" text-anchor="middle">{face_txt}</text>
{''.join(callouts)}
</g>'''

    notes25 = [
        (34.8, 'Блок аудіо (упор)', '#b42318'),
        (32.1, 'Буртик Ø5 > Ø4,45', '#b42318'),
        (27.7, 'Т-місток (упор)', '#b42318'),
        (22.0, 'Хребет (стінка 0,20)', '#b42318'),
    ]
    notes26 = [
        (38.8, 'Монтажна стінка 2,10', '#1b7a46'),
        (34.8, 'Стінка пазу 0,80 мм', '#1b7a46'),
        (32.1, 'Ø5,90 (утопл. −0,32)', '#1b7a46'),
        (27.7, 'Т-місток вільний', '#1b7a46'),
        (22.0, 'Стінка 0,80 (4× товщ.)', '#1b7a46'),
    ]

    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="680" viewBox="0 0 1120 680" role="img">
<title>D2.5 vs D2.6: усунення колізій USB-A/аудіо та потовщення стінки пазу до 0,80 мм</title>
<defs>
<style>
text{{font-family:'Segoe UI',Arial,sans-serif;fill:#20392e}}
.ey{{font-size:12px;font-weight:700;letter-spacing:1.2px;fill:#436153}}
.head{{font-size:25px;font-weight:700}}
.sub{{font-size:13.5px;fill:#3b5448}}
.lab{{font-size:15px;font-weight:700}}
.tiny{{font-size:12px}}
.micro{{font-size:10.5px}}
.badge{{font-size:11.5px;font-weight:700;fill:#ffffff}}
</style>
<pattern id="cmpHatch" width="6" height="6" patternUnits="userSpaceOnUse">
  <rect width="6" height="6" fill="#e6c28b"/>
  <path d="M-1 1 1-1 M0 6 6 0 M5 7 7 5" stroke="#bd965f" stroke-width="1"/>
</pattern>
</defs>
<rect width="1120" height="680" rx="12" fill="#f9f9f3"/>
<text x="28" y="30" class="ey">MAC MINI M1   /   ПОРІВНЯННЯ РЕАЛЬНИХ STL: D2.5 → D2.6 (+0,60 ММ)   /   ЗОНА USB-A + АУДІО</text>
<text x="28" y="62" class="head">Усунення вигину на ~2 мм + потовщення стінки пазу з 0,20 до 0,80 мм</text>
<text x="28" y="86" class="sub">Перерізи STL проти моделі плати за фото (19.11.2026). Перетин: D2.5 = {v25:.1f} мм³ → D2.6 = {v26:.3f} мм³; поле 2,00 → 2,60 мм.</text>
<line x1="28" y1="102" x2="1092" y2="102" stroke="#acbcb1"/>

<rect x="28" y="120" width="528" height="532" rx="8" fill="#edf1e8" stroke="#c3cfc7"/>
<text x="44" y="146" class="lab">Внутрішня кишеня (вид зсередини, зріз Y = 55,80 мм)</text>
<text x="44" y="165" class="tiny">Зелений — Т-кишеня D2.6; червоний пунктир — D2.5; темне — модель портів</text>
<g>
  <path d="{path_xz(void26)}" fill="#cfe8d5" stroke="#1b7a46" stroke-width="2" fill-rule="evenodd"/>
  <path d="{path_xz(board_tbridge)}" fill="#8fa399" stroke="#475c52" stroke-width="1" fill-rule="evenodd"/>
  <path d="{path_xz(board_bezels)}" fill="#35483f" stroke="#1e2b24" stroke-width="1.2" fill-rule="evenodd"/>
  <path d="{path_xz(void25)}" fill="none" stroke="#d93829" stroke-width="2" stroke-dasharray="6 4" fill-rule="evenodd"/>
  <path d="{path_xz(hole26)}" fill="#ffffff" stroke="#1b7a46" stroke-width="1.6" fill-rule="evenodd" opacity="0.9"/>
  <path d="{path_xz(board_collar)}" fill="#1f2924" stroke="#000000" stroke-width="1" fill-rule="evenodd"/>
  <path d="{path_xz(hole25)}" fill="none" stroke="#d93829" stroke-width="1.4" stroke-dasharray="3 2" fill-rule="evenodd"/>
</g>
<text x="{LX(41.3):.1f}" y="{LY(37.4):.1f}" class="tiny" text-anchor="middle" font-weight="700" fill="#1b7a46">Верхня ніжка Т-кишені: 12,0 × 10,2 мм</text>
<text x="{LX(41.3):.1f}" y="{LY(15.6):.1f}" class="tiny" text-anchor="middle" font-weight="700" fill="#1b7a46">Нижня перекладина: 34,2 × 10,8 мм (A2 + Т-місток + A1)</text>
<text x="{LX(32.7):.1f}" y="{LY(22.0)+4:.1f}" class="tiny" text-anchor="middle" font-weight="700">USB-A2</text>
<text x="{LX(49.9):.1f}" y="{LY(22.0)+4:.1f}" class="tiny" text-anchor="middle" font-weight="700">USB-A1</text>
<text x="{LX(48.5):.1f}" y="{LY(34.2):.1f}" class="micro" fill="#b42318">D2.5: коло Ø7,70</text>
<text x="{LX(48.5):.1f}" y="{LY(32.7):.1f}" class="micro" fill="#b42318">різало прямокутний</text>
<text x="{LX(48.5):.1f}" y="{LY(31.2):.1f}" class="micro" fill="#b42318">блок 10,0 × 6,2 мм</text>
<text x="{LX(22.2):.1f}" y="{LY(34.2):.1f}" class="micro" fill="#1b7a46">Отвір аудіо: Ø5,90</text>
<text x="{LX(22.2):.1f}" y="{LY(32.7):.1f}" class="micro" fill="#1b7a46">(буртик Ø5,00 тепер</text>
<text x="{LX(22.2):.1f}" y="{LY(31.2):.1f}" class="micro" fill="#1b7a46">утоплений на 0,32 мм)</text>

<rect x="44" y="546" width="496" height="92" rx="6" fill="#f9f9f3" stroke="#ccd6cf"/>
<rect x="58" y="560" width="14" height="14" fill="#cfe8d5" stroke="#1b7a46" stroke-width="1.5"/>
<text x="80" y="572" class="tiny">D2.6 Т-кишеня (дно Y = 56,56; міцна лицева стінка 0,80 мм)</text>
<line x1="58" y1="590" x2="72" y2="590" stroke="#d93829" stroke-width="2.2" stroke-dasharray="5 3"/>
<text x="80" y="594" class="tiny">D2.5 старі кишені (стінка 0,20 мм + конфлікт USB-A / Т-місток / аудіо)</text>
<rect x="58" y="608" width="14" height="14" fill="#35483f"/>
<text x="80" y="620" class="tiny">Фотографовані порти (15,6×8,55 USB-A; 10,0×6,2 аудіо + буртик Ø5,00)</text>

{yz_group(p25_yz, hit25_yz, 56.76, 574, 'D2.5 · зріз X = 41,30', f'КОЛІЗІЯ {v25:.1f} мм³ · 0,20 мм', '#c93326', notes25)}
{yz_group(p26_yz, hit26_yz, s.FACE, 842, 'D2.6 · зріз X = 41,30', '0,000 мм³ · СТІНКА 0,80 мм', '#1b7a46', notes26)}
</svg>'''
    (s.OUT/'d25-vs-d26-usb-audio-comparison.svg').write_text(svg+'\n',encoding='utf8')
    print('Wrote d25-vs-d26-usb-audio-comparison.svg; board/panel overlap D2.5=',v25,'mm3 -> D2.6=',v26,'mm3')

def main():
    load=lambda f:json.loads((s.OUT/f).read_text(encoding='utf8'))
    panel=parts()[s.PANEL];mac=owner()[BOARD_LABEL]
    stl=s.OUT/'print/02-flat-rear-panel.stl';record=load('print/stl-checks.json')['parts'][stl.name]
    assert sha256(stl.read_bytes()).hexdigest()==record['sha256']
    desk_stl=stl_to_desk(stl,panel)
    make_tb1_section(panel,mac,desk_stl,load)
    make_usb_audio_comparison(panel,mac,desk_stl)

if __name__=='__main__': main()
