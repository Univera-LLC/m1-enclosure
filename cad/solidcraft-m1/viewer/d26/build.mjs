import {build} from 'esbuild';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {basename,dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseArgs} from 'node:util';
import {views,viewKeys,portViews,revision} from './catalog.js';
const here=dirname(fileURLToPath(import.meta.url)), viewer=dirname(here), cad=dirname(viewer), root=resolve(cad,'../..');
const {values:args}=parseArgs({options:{draft:{type:'boolean'},packed:{type:'string'},'cad-dir':{type:'string'},output:{type:'string'}}});
if(Boolean(args.packed)!==Boolean(args['cad-dir']))throw Error('Provide both --packed PATH and --cad-dir PATH (relative to the project root).');
if(args.output&&!args.packed)throw Error('--output requires --packed and --cad-dir');
const draft=args.draft, frozen=join(cad,'prototype-d26'), prototype=args.packed?resolve(root,args['cad-dir']):frozen;
const packed=args.packed?resolve(root,args.packed):null, dst=args.output?resolve(root,args.output):join(root,draft?'build/d26-draft':packed?'build/d26-engineering-viewer':'build/d26-viewer');
await mkdir(dirname(dst),{recursive:true});await mkdir(dst,{recursive:!packed});
const study=join(cad,'prototype-d2','photo-study');
async function releaseInput(path,encoding){try{return await readFile(path,encoding);}catch(err){if(draft&&err.code==='ENOENT')return null;throw err;}}
async function assembly(){
  if(packed)return readFile(join(packed,'assembly.glb'));
  // The public checkout can rebuild the UI from the exact assembly in the published atlas.
  // The geometry hash check below also applies to a newly packed CAD build.
  const html=await readFile(join(prototype,'review/index.html'),'utf8');
  const bytes=html.match(/<script id="model-bytes" type="application\/octet-stream">([A-Za-z0-9+/=]+)<\/script>/);
  if(!bytes)throw Error('Missing embedded assembly in the published D2.6 atlas.');
  return gunzipSync(Buffer.from(bytes[1],'base64'));
}
const [glb,template,css,license,oldContent,bundled]=await Promise.all([
  assembly(),readFile(join(here,'page.html'),'utf8'),Promise.all([readFile(join(viewer,'d1/style.css'),'utf8'),readFile(join(here,'style.css'),'utf8')]).then(parts=>parts.join('\n')),
  readFile(join(viewer,'node_modules/three/LICENSE'),'utf8'),readFile(join(viewer,'content.json'),'utf8'),
  build({entryPoints:[join(here,'app.js')],bundle:true,write:false,format:'iife',target:['es2020'],minify:true,legalComments:'inline'})]);
const poster={};
for(const key of [...viewKeys,'board-back','panel-back','rear-lid','rear-feed','rear-clear','rear-open',...Object.keys(portViews).filter(k=>k!=='all').map(k=>'rear-'+k)]){
  const data=await releaseInput(join(here,'posters',key+'.webp'));
  poster[key]=data?'data:image/webp;base64,'+data.toString('base64'):'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2 1"%3E%3C/svg%3E'.replaceAll('"','%22');
}
const tabs=viewKeys.map((k,i)=>'<a href="?view='+k+'" data-view="'+k+'"'+(!i?' aria-current="page"':'')+'><svg aria-hidden="true"><use href="#i-'+views[k].icon+'"/></svg>'+views[k].tab+'</a>').join('');
const cadReport=JSON.parse(await readFile(join(prototype,'cad-validation.json'),'utf8'));
const verified=JSON.parse(await readFile(join(packed||here,'geometry-check.json'),'utf8'));
if(verified.revision!==revision||verified.rear_panel?.openings.length!==8||createHash('sha256').update(glb).digest('hex')!==verified.sha256){throw Error('Viewer needs the verified '+revision+' panel and the current packed assembly');}
const mount=verified.rear_panel.mount;
if(mount?.axis?.join(',')!=='0,0,1'||!(mount.travel_mm>30)||verified.rear_panel.print_face!=='exterior')throw Error('CAD must verify top entry, vertical release and the exterior print face');
if(!draft&&!verified.owner_topside)throw Error('No evidence for the photo-based board in the packed assembly');
const boxes=Object.values(cadReport.bodies).map(b=>b.bbox);
const mm=new Intl.NumberFormat('uk-UA',{maximumFractionDigits:2});
const dimensions=[0,1,2].map(i=>mm.format(Math.max(...boxes.map(b=>b.max[i]))-Math.min(...boxes.map(b=>b.min[i])))).join(' <i>×</i> ');
const release=JSON.parse(await readFile(join(here,'downloads.json'),'utf8'));
const stls=JSON.parse(await readFile(join(prototype,'print/stl-checks.json'),'utf8'));
if(release.revision!==revision||stls.revision!==revision)throw Error('Download catalog does not match '+revision);
if(!draft){
  const sliced=JSON.parse(await readFile(join(prototype,'print/slice-checks.json'),'utf8'));
  for(const data of [stls,sliced]){
    if(data.fit_report_sha256!==verified.reports_sha256['fit-validation.json']||data.cad_report_sha256!==verified.reports_sha256['cad-validation.json'])throw Error('STL or slice results predate the current CAD/fit report');
  }
  if(sliced.revision!==revision||Object.keys(sliced.parts).length!==8||!Object.entries(stls.parts).every(([name,part])=>sliced.parts[name]?.input_sha256===part.sha256&&Array.isArray(sliced.parts[name].warnings)&&!sliced.parts[name].warnings.length))throw Error('All eight production slices must be current and warning-free, including the reinforced lid');
}
const downloadDir='downloads/'+revision.toLowerCase(),size=new Intl.NumberFormat('uk-UA',{maximumFractionDigits:1});
const downloadHashes={};
async function fileLinks(group){
  const links=await Promise.all(Object.entries(release[group]).map(async ([file,label])=>{
    const bytes=await releaseInput(join(prototype,file)),name=basename(file),url=downloadDir+'/'+file;
    if(!bytes&&draft&&group==='kits')return '';
    if(!bytes)throw Error('Missing required '+group+' '+file);
    if(group==='stl'&&createHash('sha256').update(bytes).digest('hex')!==stls.parts[name]?.sha256)throw Error('Unverified STL: '+file);
    if(['step','native'].includes(group)&&!cadReport.readback[name])throw Error('No STEP readback for '+file);
    if(['step','native'].includes(group)&&createHash('sha256').update(bytes).digest('hex')!==cadReport.files_sha256[name])throw Error('STEP hash mismatch: '+file);
    downloadHashes[url]=createHash('sha256').update(bytes).digest('hex');
    const dest=join(dst,url);await mkdir(dirname(dest),{recursive:true});await writeFile(dest,bytes);
    const mb=bytes.length>=1e6,weight=size.format(mb?bytes.length/1e6:Math.round(bytes.length/1e3))+(mb?' МБ':' КБ');
    return '<a class="file-link" href="'+url+'" download="'+name+'"><span>'+label+'</span><small>'+name.split('.').pop().toUpperCase()+' · '+weight+'</small><svg aria-hidden="true"><use href="#i-download"/></svg></a>';
  }));
  return links.join('\n');
}
const [KITS,STEPS,STLS,NATIVE]=await Promise.all(['kits','step','stl','native'].map(fileLinks));
// Trace the actual coplanar bed-contact faces of the released, print-oriented STL.
// Shared triangle edges cancel, leaving its outer perimeter and the eight apertures.
function printFace(stl,record){
  if(record.rotation_xyz_deg.join(',')!=='-90,0,0'||record.bed_face?.side!=='exterior'||record.bed_face.openings_on_first_section!==8||record.sha256!==createHash('sha256').update(stl).digest('hex'))throw Error('Unverified exterior-down STL');
  const n=stl.readUInt32LE(80);if(stl.length!==84+n*50)throw Error('Expected a binary STL');
  const edges=new Map(),xy=new Map();let loX=Infinity,loY=Infinity,hiX=-Infinity,hiY=-Infinity;
  for(let t=0;t<n;t++){
    const at=84+t*50+12,pts=[0,1,2].map(i=>[0,1,2].map(d=>stl.readFloatLE(at+i*12+d*4)));
    if(pts.some(p=>Math.abs(p[2])>.0002))continue;
    const ids=pts.map(([x,y])=>{const a=+x.toFixed(3),b=+(-y).toFixed(3),k=a+','+b;xy.set(k,[a,b]);loX=Math.min(loX,a);hiX=Math.max(hiX,a);loY=Math.min(loY,b);hiY=Math.max(hiY,b);return k;});
    for(let i=0;i<3;i++){const a=ids[i],b=ids[(i+1)%3];if(a===b)continue;const k=[a,b].sort().join(':');if(!edges.delete(k))edges.set(k,[a,b]);}
  }
  const next=new Map(edges.values()),loops=[];
  if(next.size!==edges.size)throw Error('Ambiguous STL face boundary');
  while(next.size){const start=next.keys().next().value;let k=start,path='M';do{
    if(!next.has(k))throw Error('Open STL face boundary');
    path+=xy.get(k).join(' ')+' ';const prior=k;k=next.get(k);next.delete(prior);
  }while(k!==start);loops.push(path+'Z');}
  if(loops.length!==9)throw Error('Expected one contact perimeter and eight port openings; found '+loops.length);
  return '<svg class="print-footprint" role="img" aria-label="Відбиток зовнішньої площини на столі, вісім окремих отворів" data-stl-sha="'+record.sha256+'" viewBox="'+[loX-2,loY-2,hiX-loX+4,hiY-loY+4].join(' ')+'"><path fill="#42594d" fill-rule="evenodd" d="'+loops.join(' ')+'"/></svg>';
}
const panelFile='02-flat-rear-panel.stl',printDrawing=printFace(await readFile(join(prototype,'print',panelFile)),stls.parts[panelFile]);
const [outline,boardModel]=await Promise.all([releaseInput(join(study,'antenna_shapes.svg'),'utf8'),releaseInput(join(prototype,'board-study/mac-board-reference.glb'))]);
function antennaStudy(svg){
  if(!svg)return '<p>Рисунок антен ще не додано до цієї чернетки.</p>';
  const root=svg.trim().match(/^<svg\b([^>]*)>([\s\S]*)<\/svg>$/);
  if(!root||/<(?:script|image|foreignObject|a)\b|\b(?:href|on\w+)\s*=/i.test(svg))throw Error('Expected self-contained vector antenna outlines');
  const body=root[2].replace(/<(title|desc)\b[^>]*>[\s\S]*?<\/\1>/g,'').trim();
  const panels=[['a','А. Компактний вузол: чорні накладки та вушко з отвором'],['b','Б. Видовжений вузол: зворотний бік, кінцевий відгин та вихід кабелю']];
  const cards=panels.map(([id,label])=>{
    const crop=root[1].match(new RegExp('data-panel-'+id+'="([\\d .-]+)"'))?.[1];
    if(!crop||crop.trim().split(/\s+/).length!==4)throw Error('Missing SVG crop for antenna '+id);
    return '<svg data-antenna="'+id+'" viewBox="'+crop+'" role="img" aria-label="'+label+'"><use href="#owner-antenna-outlines"/></svg>';
  });
  return '<svg class="antenna-defs" aria-hidden="true" focusable="false"><defs><g id="owner-antenna-outlines" font-family="system-ui, Segoe UI, Arial, sans-serif">'+body+'</g></defs></svg><div class="antenna-panels">'+cards.join('')+'</div>';
}
let boardLink='<span class="draft-file">Файл плати ще не додано до цієї чернетки.</span>';
if(boardModel){
  if(boardModel.length<20||boardModel.toString('ascii',0,4)!=='glTF'||boardModel.readUInt32LE(4)!==2||boardModel.readUInt32LE(8)!==boardModel.length)throw Error('Invalid portable Mac board GLB');
  const name='mac-board-reference.glb',url='reference/'+revision.toLowerCase()+'/'+name;
  const expected=verified.owner_topside?.download;
  if((!draft||expected)&&(expected?.file!==name||expected.bytes!==boardModel.length||expected.sha256!==createHash('sha256').update(boardModel).digest('hex')))throw Error('Portable board differs from its verified export');
  downloadHashes[url]=createHash('sha256').update(boardModel).digest('hex');
  await mkdir(dirname(join(dst,url)),{recursive:true});await writeFile(join(dst,url),boardModel);
  boardLink='<a class="file-link" id="board-model-download" href="'+url+'" download="'+name+'"><span>3D-модель плати Mac (.glb)</span><small>GLB · '+size.format(boardModel.length/1e6)+' МБ</small><svg aria-hidden="true"><use href="#i-download"/></svg></a>';
}
const service=verified.service,fit=verified.port_fit;
if(!service?.board_install_xyz_mm||fit?.ports?.length!==8)throw Error('No current board/port assembly reports');
for(const [name,sha] of Object.entries(verified.reports_sha256)){
  if(createHash('sha256').update(await readFile(join(prototype,name))).digest('hex')!==sha)throw Error('Packing uses an outdated CAD report: '+name);
}
const lengths=new Intl.NumberFormat('uk-UA',{minimumFractionDigits:2,maximumFractionDigits:2}),L=n=>lengths.format(n);
const mac=service.board_install_xyz_mm,pd=[...service.pd_remove_xyz_mm].reverse();
const pathFacts=(points)=>points.map(p=>'('+p.map(n=>mm.format(n)).join('; ')+')').join(' → ');
const offsets='<p><b>Панель.</b> Опустіть згори в пази порожнього шасі. На останніх '+mm.format(service.panel_remove_xyz_mm[1][2])+' мм опускання клини зміщують її на '+mm.format(Math.abs(service.panel_remove_xyz_mm[1][1]))+' мм до задніх упорів. За відкритої кришки під час заведення плат притримуйте обидва верхні кути біля цих упорів.</p><p><b>Плата Mac.</b> Після встановлення панелі опустіть плату перед опорами, підведіть торці гнізд до вузьких отворів і посадіть монтажні кільця. Зсуви від кінцевої посадки (X; Y; Z), мм: '+pathFacts(mac)+'.</p><p><b>PD і Mini‑560.</b> Обидва модулі спочатку ставлять у тримач. Установлення вузла з уже закріпленою платою Mac, мм: '+pathFacts(pd)+'. Для зняття пройдіть точки у зворотному порядку. Це положення CAD; реальні деталі ще не приміряли.</p>';
const ports={A1:'USB‑A 1',A2:'USB‑A 2',HDMI:'HDMI',TB1:'TB / USB‑C 1',TB2:'TB / USB‑C 2',audio:'Аудіо',RJ:'Ethernet',PD:'PD IN'};
const rows=fit.ports.map(o=>{
  if(!Object.hasOwn(ports,o.id)||!(o.skin_mm>0&&o.axial_clearance_mm>0)||Math.abs(o.skin_mm+o.axial_clearance_mm-o.recess_mm)>.008||!o.probes?.masked_bezel?.with_panel_removed||!o.probes?.open_to_back)throw Error('Missing recessed mask geometry: '+o.id);
  const opening=o.id==='audio'?'Ø '+L(o.opening_xz_mm[0]):o.opening_xz_mm.map(L).join(' × ');
  return '<tr data-port="'+o.id+'" data-recess="'+o.recess_mm+'" data-gap="'+o.axial_clearance_mm+'" data-skin="'+o.skin_mm+'"><th scope="row">'+ports[o.id]+'</th><td>'+opening+'</td><td>'+L(o.skin_mm)+'</td><td>'+L(o.axial_clearance_mm)+'</td><td>'+L(o.recess_mm)+'</td></tr>';
});
const portTable='<table class="fit-table"><caption>Від зовнішньої площини до кромки гнізда · номінальний CAD, мм</caption><thead><tr><th scope="col">Гніздо</th><th scope="col">Вікно: Ш × В</th><th scope="col">Тонка стінка</th><th scope="col">Повітря до кромки</th><th scope="col">Заглиблення</th></tr></thead><tbody>'+rows.join('')+'</tbody></table><p class="fit-caption">Заглиблення — сума товщини пластику й повітря перед торцем гнізда. Розміри вікон подано по найбільших ширині й висоті; заокруглення та скоси видно на кресленні й у 3D. Для аудіо остання колонка показує відступ до прямокутної рамки; до виступного круглого буртика — 0,32 мм. Осі — SOURCE, рамки й буртик — оцінки за фото (DOCUMENTED).</p>';
const sectionFile=await releaseInput(join(prototype,'connector-section.svg'))||Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 80"><text x="20" y="44">Розріз ще готується. Чернетка для рендеру.</text></svg>');
function vectorBox(data){
  const svg=data.toString('utf8'),bounds=svg.match(/\bviewBox=["']([\d., E+e-]+)["']/)?.[1]?.split(/[ ,]+/).map(Number);
  if(bounds?.length!==4||!bounds.every(Number.isFinite)||bounds[2]<=0||bounds[3]<=0||/<(?:script|image|foreignObject)\b|(?:\bhref|xlink:href)\s*=\s*["'](?!#)|\bon[a-z]+\s*=|url\(\s*["']?(?!#)[a-z]/i.test(svg))throw Error('Expected a self-contained vector drawing');return bounds;
}
const box=vectorBox(sectionFile);
const comparison=await readFile(join(prototype,'d25-vs-d26-usb-audio-comparison.svg'));const compBox=vectorBox(comparison);
await writeFile(join(dst,'d26-connector-section.svg'),sectionFile);
await writeFile(join(dst,'d25-vs-d26-usb-audio-comparison.svg'),comparison);
const sectionData='data:image/svg+xml;base64,'+sectionFile.toString('base64');
const wall=verified.rear_panel.wall_sections;
if(!Object.keys(ports).every(id=>wall[id]?.thickness_mm>0&&Array.isArray(wall[id].probe_xz_mm)))throw Error('Missing local solid thickness checks');
const nearMac=Object.values(wall).map(v=>v.thickness_mm);
const interval=arr=>Math.min(...arr)===Math.max(...arr)?L(arr[0]):L(Math.min(...arr))+'–'+L(Math.max(...arr));
const web=Object.entries(fit.webs_face_mm).sort((a,b)=>a[1]-b[1])[0];if(!web||Math.abs(web[1]-fit.minimum_web_mm)>.001)throw Error('Missing print web');
const webNote=web[0].split('/').map(k=>ports[k]).join(' та ')+': '+mm.format(fit.minimum_web_mm)+' мм у CAD.';
const field=verified.rear_panel.field.thickness_mm;
if(!(field>Math.max(...nearMac)))throw Error('Unverified solid main field');
const wallNote='Основна стінка панелі має '+L(field)+' мм. На дні кишень перед обідками — '+interval(nearMac)+' мм пластику. Далі є невеликий повітряний зазор; усі торці залишаються позаду зовнішньої площини.';
const buttons=Object.entries(portViews).map(([k,v])=>'<button type="button" data-port="'+k+'" aria-pressed="'+(k==='all')+'">'+v.label+'</button>').join('');
const familyFrames=Object.entries(portViews).filter(([k])=>k!=='all').map(([k,v])=>'<figure><a href="?view=rear&amp;port='+k+'#stage"><img loading="lazy" src="'+poster['rear-'+k]+'" alt="'+v.label+': вхід за фасонним отвором у зібраній панелі. Збільшити в 3D."></a><figcaption>'+v.label+'</figcaption></figure>').join('');
const tbPair=fit.ports.filter(p=>p.id==='TB1'||p.id==='TB2'),tb=tbPair[0];
if(tbPair.length!==2||tbPair.some(p=>p.masked_x_margin_mm?.length!==2||Math.min(...p.masked_x_margin_mm)<=1||L(p.opening_xz_mm[0])!==L(tb.opening_xz_mm[0])))throw Error('Missing two masked Thunderbolt bezels');
const tbNote='У кожного Thunderbolt ширина оболонки '+L(tb.outer_bezel_xz_span_mm[0])+' мм, а овального вікна у пластику — '+L(tb.opening_xz_mm[0])+' мм. З кожного боку панель перекриває приблизно '+L(tb.masked_x_margin_mm[0])+' мм оболонки.';
const inlet=fit.ports.find(p=>p.id==='PD'),shift=inlet.axis_xz_mm[1]-inlet.opening_center_xz_mm[1],thirds=new Intl.NumberFormat('uk-UA',{maximumFractionDigits:3});
if(!draft&&!(shift>.08&&shift<.12&&inlet.aperture_below_lip_mm>0&&inlet.aperture_below_lip_mm<.08))throw Error('Expected the final lowered aperture of the independent PD inlet');
const pdNote=shift>.01?'Центр його вікна у моделі на '+L(shift)+' мм нижче осі гнізда. На невеликій ділянці нижньої дуги отвір виходить за край металу приблизно на '+thirds.format(inlet.aperture_below_lip_mm)+' мм.':'Окремий вертикальний вхід належить тригеру CMTPD.';
const steps=[
  ['rear-open','Заведіть панель','У порожньому шасі сумістіть її краї з двома вертикальними пазами.'],
  ['rear-clear','Опустіть на полицю','Панель уже на місці; плата й вузол PD ще поза корпусом.'],
  ['rear-feed','Підведіть плату','Опустіть плату перед опорами. Подайте гнізда до отворів і посадіть монтажні кільця.'],
  ['rear','Закріпіть і закрийте','Закріпіть плату, встановіть тримач із PD та Mini‑560, поверніть кришку.'],
].map(([image,title,body])=>'<li><div class="step-frame"><img src="'+poster[image]+'" alt="'+title+' — кадр моделі '+revision+'"></div><h3>'+title+'</h3><p>'+body+'</p></li>').join('');
const slots={REV:revision,PANEL_BACK:poster['panel-back'],MIN_WEB_NOTE:webNote,WALL_NOTE:wallNote,PORT_DATA:JSON.stringify(fit),PORT_BUTTONS:buttons,FACADE_FRAMES:familyFrames,FACADE_POSTER:poster.rear,SECTION_WIDTH:box[2],SECTION_HEIGHT:box[3],PORT_SECTION:sectionData,PORT_TABLE:portTable,ASSEMBLY_STEPS:steps,ASSEMBLY_OFFSETS:offsets,SERVICE_DATA:JSON.stringify(service),DIMENSIONS:dimensions,KITS,STEPS,STLS,NATIVE,DOWNLOAD_DIR:downloadDir,PANEL_TRAVEL:mount.travel_mm,PRINT_FACE:printDrawing,BOARD_DOWNLOAD:boardLink,ANTENNA_STUDY:antennaStudy(outline),LEGACY_MODES:JSON.stringify(Object.keys(JSON.parse(oldContent).modes)),CSS:css,TABS:tabs,POSTER:poster.overview,MODEL:gzipSync(glb,{level:9}).toString('base64'),POSTERS:JSON.stringify(poster),BUNDLE:bundled.outputFiles[0].text.replace(/<\/script/gi,'<\\/script')};
slots.TB_NOTE=tbNote;
slots.PD_NOTE=pdNote;
slots.TB_COMPARISON='data:image/svg+xml;base64,'+comparison.toString('base64');slots.COMP_WIDTH=compBox[2];slots.COMP_HEIGHT=compBox[3];
let html=template.replace(/__([A-Z_]+)__/g,(_,k)=>{if(!Object.hasOwn(slots,k))throw Error('Unknown template slot: '+k);return slots[k];});
if(packed)html=html.replace('<body>','<body><aside style="padding:.75rem;background:#fff1c2;color:#352a09;text-align:center">Інженерна збірка: 3D і файли з поточного CAD. Статичні ілюстрації та фото-орієнтири — з опублікованої D2.6. Фізична примірка не підтверджена.</aside>');
html=html.replace('</head>',()=>'<!-- Three.js MIT licence\n'+license+'\n-->\n</head>');
// Use the same bytes offline that GitHub Pages publishes from the Git blob.
html=html.replace(/\r\n/g,'\n');
if(/(?:[A-Za-z]:[\\/]Users[\\/]|file:\/\/\/)/i.test(html))throw Error('Local path in public bundle');
const out=join(dst,'index.html');await writeFile(out,html);
if(!draft){
  for(const name of ['d26-preview.jpg','d26-rear-assembly.jpg'])await writeFile(join(dst,name),await readFile(join(frozen,'review',name)));
  if(packed){
    // Copy the report/assembly notes linked by the page from the selected CAD run.
    for(const name of ['FIT-FIRST.md','CREDITS.txt','ports-fit.json','reference-crosscheck.json','fascia-contract.json','cad-validation.json','fit-validation.json','power-fit.json','board-install-fit.json','print/stl-checks.json','print/slice-checks.json'])
      await writeFile(join(dst,downloadDir,name),await readFile(join(prototype,name)));
    await writeFile(join(dst,'engineering-check.json'),JSON.stringify({revision,source_reports:verified.reports_sha256,
      model_sha256:verified.sha256,ports:verified.port_fit.ports,download_sha256:downloadHashes},null,2)+'\n');
  }
}
console.log((draft?'Draft':'Review')+' '+out+' · '+Buffer.byteLength(html)+' bytes · '+createHash('sha256').update(html).digest('hex'));
