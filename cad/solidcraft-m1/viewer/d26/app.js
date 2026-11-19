import {views,viewKeys,parts,revision,portViews} from './catalog.js';
import {startScene} from './scene.js';

const $=id=>document.getElementById(id), live='https://dvaderfun.github.io/mac-mini-m1-case-prototype/';
if(location.protocol==='file:')for(const a of document.querySelectorAll('footer a[data-archive]'))a.href=new URL(a.getAttribute('href'),live);
document.querySelector('.jump-rear').href='?view=rear#stage';
const posters=JSON.parse($('posters').textContent), state={};let api=null,pendingPose=null,failed=false;
const num=n=>String(n).padStart(2,'0'),icon=n=>'<svg aria-hidden="true"><use href="#i-'+n+'"/></svg>';
const base=(key)=>({view:key,selected:null,solo:false,labels:true,spread:key==='power'?28:0,gauges:false,mounts:false,rf:false,side:'top',port:'all'});
function readLocation(){
  const p=new URLSearchParams(location.search),key=Object.hasOwn(views,p.get('view'))?p.get('view'):'overview';
  Object.assign(state,base(key));
  if(!['board','base'].includes(key)&&p.has('spread')&&/^\d{1,3}$/.test(p.get('spread')))state.spread=Math.min(100,Number(p.get('spread')));
  state.labels=p.get('labels')!=='0';state.gauges=key==='power'&&p.get('gauges')==='1';
  state.mounts=key==='power'&&p.get('mounts')==='1';
  state.rf=!failed&&key==='inside'&&p.get('rf')==='1';if(state.rf)state.spread=0;state.side=key==='board'&&p.get('side')==='back'?'back':'top';
  state.port=key==='rear'&&state.spread===0&&Object.hasOwn(portViews,p.get('port'))?p.get('port'):'all';
  const part=p.get('part');
  if(Object.hasOwn(parts,part)&&validPart(key,part)){state.selected=part;state.solo=p.get('solo')==='1';}
  if(key==='rear'&&part==='panel'&&state.solo&&p.get('side')==='back')state.side='back';
  pendingPose=p.get('cam');
}
function validPart(key,id){
  if(id==='rf')return key==='inside'&&state.rf;
  if(key==='board')return (state.side==='back'?views.board.backList:views.board.list).includes(id);
  if(id==='studmarks')return key==='inside';
  if(['loom','coax'].includes(id))return ['inside','board'].includes(key);
  if(['base','pcb','power'].includes(key))return views[key].list.includes(id)||(key==='power'&&state.mounts&&views.power.mounts.includes(id));
  return !['floorDetail','lidDetail'].includes(id)&&!views.pcb.list.includes(id)&&(key!=='inside'||!['lid','lidscrews'].includes(id));
}
function address(share=false) {
  const url=new URL(share&&location.protocol==='file:'?live:location.href);url.search='';url.hash='';const p=url.searchParams;
  if(state.view!=='overview'||share)p.set('view',state.view);
  if(state.view==='rear'&&state.port!=='all')p.set('port',state.port);
  if(state.selected)p.set('part',state.selected);if(state.solo)p.set('solo','1');
  if(state.spread!==base(state.view).spread)p.set('spread',state.spread);
  if(!state.labels)p.set('labels','0');if(state.gauges)p.set('gauges','1');if(state.mounts)p.set('mounts','1');
  if(state.rf)p.set('rf','1');if((state.view==='board'||state.view==='rear'&&state.solo&&state.selected==='panel')&&state.side==='back')p.set('side','back');
  const pose=api?api.pose():pendingPose;if(pose)p.set('cam',pose);return url;
}
function write(method='replaceState'){
  if(location.protocol!=='file:')history[method](null,'',address());
}
function setPressed(el,v){el.setAttribute('aria-pressed',String(v));}
function render(){
  const v=views[state.view],i=viewKeys.indexOf(state.view)+1;
  for(const b of $('tabs').querySelectorAll('a')){if(b.dataset.view===state.view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}
  const board=state.view==='board',back=board&&state.side==='back',figure=back?'Зворот плати Mac · геометрія SOURCE':v.figure;
  $('guide-kicker').textContent=board?'Плата власника · геометрія SOURCE':state.view==='pcb'?'Окрема гілка C5R':'Огляд збірки '+revision;
  $('ordinal').textContent=num(i)+' / '+num(viewKeys.length);$('view-title').textContent=v.title;$('view-copy').textContent=back?v.backText:v.text;$('scene-note').textContent=v.note;
  $('figure-code').textContent=v.code;$('fig-index').textContent='РИС. '+num(i);$('fig-title').textContent=figure;$('fig-status').textContent=board?(back?'SOURCE':'SOURCE + фото'):state.view==='pcb'?'C5R · v1':'FDM '+revision;
  $('poster').src=posters[back?'board-back':state.view];$('poster').alt=figure+' — статичний вигляд цифрової моделі';
  $('spread').closest('.spread-tools').hidden=state.view==='base'||board;$('board-tools').hidden=!board;
  $('reference-antennas').hidden=state.view!=='inside';setPressed($('reference-antennas'),state.rf);
  setPressed($('side-top'),!back);setPressed($('side-back'),back);$('to-board-file').hidden=!board;$('to-antennas').hidden=!['inside','board'].includes(state.view);
  $('to-fit').hidden=$('to-print').hidden=!['rear','overview'].includes(state.view);$('service-tools').hidden=state.view!=='rear';
  $('to-panel-back').hidden=state.view!=='rear';
  $('port-tools').hidden=state.view!=='rear';
  for(const b of $('port-tools').querySelectorAll('button'))setPressed(b,state.port===b.dataset.port&&state.spread===0);
  $('spread-label').textContent=['rear','overview','inside'].includes(state.view)?'Розбирання':'Рознести деталі';$('spread').disabled=failed&&state.view!=='rear';
  $('spread').value=state.spread;$('amount').value=state.spread+'%';$('gauges').hidden=state.view!=='power';
  $('mounts').hidden=state.view!=='power';setPressed($('mounts'),state.mounts);
  setPressed($('labels'),state.labels);setPressed($('gauges'),state.gauges);setPressed($('solo'),state.solo);
  $('part-list').replaceChildren(...[...(back?v.backList:v.list),...(state.mounts?v.mounts:[]),...(state.rf?['rf']:[])].map((id,index)=>{
    const b=document.createElement('button');b.type='button';b.className='part-row';b.dataset.part=id;setPressed(b,state.selected===id);
    b.innerHTML='<span class="no">'+num(index+1)+'</span><span class="swatch" aria-hidden="true"></span><span>'+parts[id].name+'</span>'+icon('chevron');
    b.style.setProperty('--swatch',parts[id].color);b.onclick=()=>choose(id);return b;
  }));
  $('inspection').hidden=!state.selected;
  if(state.selected){const p=parts[state.selected];$('part-name').textContent=p.name;$('part-copy').textContent=p.description;$('part-evidence').textContent=p.source;}
  $('solo').querySelector('span').textContent=state.solo?'Повернути весь вид':'Лише ця деталь';
  $('gesture').textContent=failed?'Статичний вигляд':state.selected?parts[state.selected].name:'Тягніть, щоб обертати';
  spreadFeedback();
  document.title=v.tab+' · Mac mini M1 / '+(state.view==='pcb'?'PCB v1':'FDM '+revision);
}
function update(force=false,method='replaceState'){render();api?.update(force);write(method);}
function choose(id){
  if(!Object.hasOwn(parts,id)||!validPart(state.view,id))return;
  const row=document.activeElement?.closest('.part-row');state.selected=id;update();
  if(row)$('part-list').querySelector('[data-part="'+id+'"]')?.focus({preventScroll:true});
}
function reset(){Object.assign(state,base(state.view));pendingPose=null;update(true);}
$('tabs').addEventListener('click',e=>{
  const a=e.target.closest('a[data-view]');
  if(!a||e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();
  if(a.dataset.view===state.view)return;Object.assign(state,base(a.dataset.view));pendingPose=null;update(true,'pushState');
});
$('labels').onclick=()=>{state.labels=!state.labels;update();};
$('gauges').onclick=()=>{state.gauges=!state.gauges;update();};
$('mounts').onclick=()=>{state.mounts=!state.mounts;if(!state.mounts&&views.power.mounts.includes(state.selected)){state.selected=null;state.solo=false;}update(true);};
$('reference-antennas').onclick=()=>{state.rf=!state.rf;if(state.rf)state.spread=0;if(!state.rf&&state.selected==='rf'){state.selected=null;state.solo=false;}update(true);};
for(const side of ['top','back'])$('side-'+side).onclick=()=>{state.side=side;if(state.selected&&!validPart(state.view,state.selected)){state.selected=null;state.solo=false;}pendingPose=null;update(true);};
$('solo').onclick=()=>{if(state.selected){state.solo=!state.solo;update(true);}};
$('clear-part').onclick=()=>{const solo=state.solo;state.selected=null;state.solo=false;update(solo);};
function spreadFeedback(){
  const v=state.spread;
  if(!['rear','overview','inside'].includes(state.view)){$('spread').setAttribute('aria-valuetext',v+'%');return;}
  const phase=v===0?'Корпус складено':v<=6?'Звільніть гвинти кришки':v<36?'Зніміть кришку':v===36?'Кришку знято':v<=44?'Звільніть кріплення плати':v<54?'Вийміть вузол живлення':v<60?'Підніміть плату над опорами':v<65?'Відведіть гнізда від панелі':v<74?'Вийміть плату з радіатором':v===74?'Шасі без плат; панель у пазах':v<100?'Підніміть панель вертикально':'Панель вийнято з порожнього шасі';
  const step=v<30?[0,state.port==='all'?'rear':'rear-'+state.port,state.port==='all'?'Зібраний тил':portViews[state.port].label+' · зібране гніздо']:v<54?[36,'rear-lid','Кришку знято']:v<74?[71,'rear-feed','Плату піднято перед панеллю']:v<88?[74,'rear-clear','Шасі без плат; панель у пазах']:[100,'rear-open','Панель вийнято з порожнього шасі'];
  if(state.view==='rear'){
    if(state.solo&&state.selected==='panel'&&state.side==='back'){
      step[1]='panel-back';step[2]='Зворот панелі · кишені за отворами';
    }
    for(const b of $('service-tools').querySelectorAll('button'))setPressed(b,step[0]===Number(b.dataset.state));
    if($('poster').getAttribute('src')!==posters[step[1]])$('poster').src=posters[step[1]];
    $('poster').alt='Тил · '+step[2]+' — статичний вигляд цифрової моделі';
    $('fig-title').textContent=failed||step[1]==='panel-back'?step[2]:v>0?phase:state.port==='all'?views.rear.figure:portViews[state.port].label+' · гніздо спереду';
  }
  const description=failed?step[2]:phase;
  $('spread').setAttribute('aria-valuetext',description+', '+v+'%');
  if(!state.selected)$('gesture').textContent=(failed?'Кадр · ':'')+description;
}
function setSpread(v){
  if(state.rf&&v>0){state.rf=false;if(state.selected==='rf'){state.solo=false;state.selected=null;}render();}
  if(v>0&&state.port!=='all'){state.port='all';render();}
  state.spread=v;
  for(const b of $('port-tools').querySelectorAll('button'))setPressed(b,v===0&&state.port===b.dataset.port);
  $('spread').value=v;$('amount').value=v+'%';spreadFeedback();api?.update();
}
$('spread').oninput=e=>setSpread(Number(e.target.value));
for(const b of $('port-tools').querySelectorAll('button'))b.onclick=()=>{
  Object.assign(state,{port:b.dataset.port,spread:0,selected:null,solo:false});pendingPose=null;update(true);
};
for(const b of $('service-tools').querySelectorAll('button'))b.onclick=()=>{
  if(state.selected||state.solo||state.port!=='all'){Object.assign(state,{selected:null,solo:false,port:'all'});update(true);}
  setSpread(Number(b.dataset.state));write();
};
$('spread').onchange=()=>write();
$('zoom-in').onclick=()=>api?.zoom(1.25);$('zoom-out').onclick=()=>api?.zoom(.8);$('reset').onclick=reset;
// Expand the existing viewer so the same canvas, controls and camera survive the resize.
const review=$('review'),fullButton=$('fullscreen');
let viewportOnly=false,fullPending=false,returnScroll=[0,0],outside=[];
function syncFullscreen(){
  const open=document.fullscreenElement===review||viewportOnly;
  if(review.classList.contains('expanded')===open)return;
  review.classList.toggle('expanded',open);document.documentElement.classList.toggle('review-open',open);
  fullButton.setAttribute('aria-expanded',String(open));
  fullButton.querySelector('use').setAttribute('href',open?'#i-collapse':'#i-expand');
  fullButton.querySelector('span').textContent=open?'Згорнути':'На весь екран';
  fullButton.title=open?'Вийти з повного екрана (Esc)':'Розгорнути 3D-огляд на весь екран';
  if(open){
    review.setAttribute('role','dialog');review.setAttribute('aria-modal','true');review.setAttribute('aria-label','Повноекранний огляд моделі');
    outside=[...document.querySelectorAll('.skip,.mast,.intro,#assembly-guide,#port-fit,#panel-print,#antennas,#downloads,#about,footer')].filter(el=>!el.inert);
    outside.forEach(el=>el.inert=true);$('stage').focus({preventScroll:true});
  }else{
    review.removeAttribute('role');review.removeAttribute('aria-modal');review.removeAttribute('aria-label');
    outside.forEach(el=>el.inert=false);outside=[];
    fullButton.focus({preventScroll:true});window.scrollTo(...returnScroll);
  }
}
async function leaveFullscreen(){
  if(viewportOnly){viewportOnly=false;syncFullscreen();}
  else if(document.fullscreenElement===review){
    try{await document.exitFullscreen();}catch{/* The browser can leave first, e.g. on Escape. */}
    syncFullscreen();
  }
}
fullButton.onclick=async()=>{
  if(fullPending)return;
  fullPending=true;
  try{
    if(review.classList.contains('expanded')){await leaveFullscreen();return;}
    returnScroll=[window.scrollX,window.scrollY];
    if(review.requestFullscreen&&document.fullscreenEnabled){
      try{await review.requestFullscreen();}catch{viewportOnly=true;}
    }else viewportOnly=true;
    syncFullscreen();
  }finally{fullPending=false;}
};
document.addEventListener('fullscreenchange',syncFullscreen);
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&review.classList.contains('expanded')){e.preventDefault();void leaveFullscreen();}
});
$('stage').addEventListener('keydown',e=>{
  if(e.target!==$('stage')||!api)return;
  const fn={ArrowLeft:()=>api.rotate(-.16,0),ArrowRight:()=>api.rotate(.16,0),ArrowUp:()=>api.rotate(0,.12),ArrowDown:()=>api.rotate(0,-.12),
    '+':()=>api.zoom(1.2),'=':()=>api.zoom(1.2),'-':()=>api.zoom(1/1.2),'0':reset}[e.key];
  if(fn){e.preventDefault();fn();}
});
window.addEventListener('popstate',()=>{readLocation();render();api?.update(true);api?.restore(pendingPose);});
let noticeTimer;$('share').onclick=async()=>{
  const url=address(true).href;write();
  try{await navigator.clipboard.writeText(url);const el=$('notice');el.textContent='Посилання на цей вид скопійовано';el.hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>el.hidden=true,2600);}
  catch{$('share-url').value=url;$('share-dialog').showModal();$('share-url').select();}
};
function staticMode(){
  state.rf=false;if(state.selected==='rf'){state.selected=null;state.solo=false;}
  failed=true;api=null;$('stage').classList.remove('ready');$('surface').hidden=true;$('pins').replaceChildren();$('leaders').replaceChildren();
  $('loading').textContent='3D недоступне · показано зображення';
  for(const id of ['labels','spread','reset','zoom-in','zoom-out','solo','gauges','mounts','reference-antennas'])$(id).disabled=true;
  document.documentElement.dataset.render='static';render();
}
async function start(){
  readLocation();render();
  try{
    api=await startScene({stage:$('stage'),surface:$('surface'),leaders:$('leaders'),pins:$('pins'),eventPick:choose,state,
      eventFace(side){state.side=side;if(state.selected&&!validPart('board',state.selected)){state.selected=null;state.solo=false;}update();}});
    api.restore(pendingPose);
    await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
    if(failed)return;
    $('stage').classList.add('ready');$('loading').hidden=true;document.documentElement.dataset.render='3d';
    $('surface').querySelector('canvas').addEventListener('webglcontextlost',e=>{e.preventDefault();$('loading').hidden=false;staticMode();},{once:true});
  }catch(err){console.warn('Статичний перегляд:',err.message);staticMode();}
}
// Expose read-only scene facts for the deployment checks, including the actual GPU draw list.
Object.defineProperty(window,'m1Atlas',{value:{frontProbe:(x,z)=>Number.isFinite(x)&&Number.isFinite(z)?api?.frontProbe(x,z):null,inspect:()=>({revision,...state,visible:api?.visible()||[],meshes:api?.count()||0,positions:api?.positions()||{},sourceAntennas:api?.sources('rf')||[],radiator:api?.sources('sink')||[],boardFinishes:api?.boardFinishes()||[],ground:api?.groundVisible()??false,pose:api?.pose()||null})}});
start();
