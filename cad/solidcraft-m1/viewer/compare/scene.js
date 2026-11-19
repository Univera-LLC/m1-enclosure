import {coverArt} from './art.js';
import {startOrbit} from './orbit.js';
import {rulerGroup} from './rulers.js';

(() => {
  const $ = id => document.getElementById(id);
  const { enclosure, mac, objects } = JSON.parse($('compare-data').textContent);
  const plots = Array.from(document.querySelectorAll('.compare-item'));
  const angleButtons = Array.from($('compare-angles').querySelectorAll('button'));
  const objectButtons = Array.from($('compare-choices').querySelectorAll('button'));
  const modeButtons = Array.from($('compare-modes').querySelectorAll('button'));
  let mode='orbit', angle='iso', orbitAngle='iso', selected=null, ruler=true, orbit;

  // The viewBox and units stay the same for every object; only the projection changes.
  const isoX = Math.SQRT1_2, isoY = 1 / Math.sqrt(6), isoZ = Math.sqrt(2 / 3);
  const views = {
    iso: { project: (x,y,z) => [(x-y)*isoX, (x+y)*isoY-z*isoZ], axes: 'Ширина × глибина × висота', dims: [0,1,2], lift: 8 },
    top: { project: (x,y) => [x,y], axes: 'Ширина × глибина', dims: [0,1], lift: -7 },
    front: { project: (x,y,z) => [x,-z], axes: 'Ширина × висота', dims: [0,2], lift: 52 },
    side: { project: (x,y,z) => [-y,-z], axes: 'Глибина × висота', dims: [1,2], lift: 52 },
  };
  const number = new Intl.NumberFormat('uk-UA', { maximumFractionDigits: 2, useGrouping: false });
  const fmt = n => number.format(n);
  const round = n => Number(n.toFixed(3));
  const points = items => items.map(p => p.map(round).join(',')).join(' ');
  const rect = (x,y,w,h,r,fill) => '<rect x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" rx="'+r+'" fill="'+fill+'"/>';
  const poly = (p,fill,edge='none') => '<polygon points="'+points(p)+'" fill="'+fill+'" stroke="'+edge+'" stroke-width="0.75"/>';

  const dark = ['#354744','#2a3a37','#25332f','#25332f'];
  const silver = ['#d4deda','#acb9b5','#94a39f','#879994'];
  const slate = ['#536c66','#435d55','#354b46','#344d44'];
  const bronze = ['#d0a175','#b38559','#966d49','#866140'];
  const whiteMetal = ['#e5ebe5','#c3cec6','#a8b8af','#83988b'];
  const red = ['#bd483d','#a03530','#832d2b','#822e2b'];
  const pages = ['#f0e5ce','#e1d1af','#d0ba92','#ac9d7b'];
  const covers = {
    berserk: ['#612f35','#50262b','#3f2529','#432126'],
    thrones: ['#2b4857','#233b4b','#1e3440','#1e3440'],
  };

  // Clockwise, including the tangent points so the outline retains the nominal bounds.
  function outline(w,d,r) {
    r=Math.min(r,w/2,d/2);
    const x=w/2-r,y=d/2-r;
    return [[x,y],[-x,y],[-x,-y],[x,-y]].flatMap(([cx,cy],i)=>
      Array.from({length:13},(_,j)=>{
        const a=(i+j/12)*Math.PI/2;
        return [cx+r*Math.cos(a),cy+r*Math.sin(a)];
      }));
  }
  function prism(project,w,d,r,low,high,colors,x=0,y=0) {
    const base=outline(w,d,r).map(([u,v])=>[u+x,v+y]);
    const top=base.map(([u,v])=>project(u,v,high));
    if(angle==='top')return poly(top,colors[0],colors[3]);
    const bottom=base.map(([u,v])=>project(u,v,low));
    let markup='';
    for(let i=0;i<base.length;i++){
      const j=(i+1)%base.length;
      if(top[j][0]>=top[i][0]-1e-7)continue;
      const dx=base[j][0]-base[i][0],dy=base[j][1]-base[i][1];
      const fill=dy>-dx?colors[2]:colors[1];
      // Fill the shared edge too so anti-aliasing doesn't make seams between facets.
      markup+='<path fill="'+fill+'" stroke="'+fill+'" stroke-width=".3" d="M'+points([bottom[i],bottom[j],top[j],top[i]])+'Z"/>';
    }
    return markup+(angle==='iso'?poly(top,colors[0],colors[3]):'');
  }
  function plane(project,a,b,c,markup) {
    const [x,y]=project(...a),[ux,uy]=project(...b),[vx,vy]=project(...c);
    const matrix=[ux-x,uy-y,vx-x,vy-y,x,y].map(round).join(' ');
    return '<g transform="matrix('+matrix+')">'+markup+'</g>';
  }

  function solid(item,project) {
    const [w,d,h]=item.size;
    const block=(...args)=>prism(project,...args);
    const top=(z,markup)=>angle==='iso'||angle==='top'?plane(project,[0,0,z],[1,0,z],[0,1,z],markup):'';
    const front=(y,z,markup)=>angle==='iso'||angle==='front'?plane(project,[0,y,z],[1,y,z],[0,y,z-1],markup):'';
    const art=(markup)=>top(h,'<g transform="scale('+w/100+' '+d/140+')">'+markup+'</g>');
    switch(item.id){
      case 'enclosure': {
        const feet=[-1,1].flatMap(x=>[-1,1].map(y=>block(12,12,6,0,4,dark,x*(w/2-18),y*(d/2-15)))).join('');
        const body=block(w,d,4,4,h-3,slate)+block(w,d,4,h-3,h,['#687f78','#507169','#47655c','#435d55']);
        const vents=Array.from({length:10},(_,i)=>[-1,1].map(y=>rect(i*6-29,y*12-10,2.8,20,1.2,'#2a453d')).join('')).join('');
        const screws=[-1,1].flatMap(x=>[-1,1].map(y=>'<circle cx="'+x*(w/2-8)+'" cy="'+y*(d/2-8)+'" r="1.9" fill="#9db1a8"/>')).join('');
        return feet+body+top(h,vents+screws)+front(d/2,24,'<circle r="4.6" fill="#304a42"/>');
      }
      case 'mac':
        return block(w-17,d-17,19,0,3,dark)+block(w,d,21,3,h,silver)+
          front(d/2,9,'<circle cx="73" r="1" fill="#fbfff8"/>');
      case 'aa':
        return block(w,d,w/2,0,h-2,dark)+block(w,d,w/2,h-12,h-2,bronze)+block(5.5,5.5,2.75,h-2,h,whiteMetal)+
          front(d/2,20,'<text fill="#f4ede0" font-family="system-ui" font-size="6" font-weight="700" text-anchor="middle">AA</text>');
      case 'cola':
        return block(w-4,d-4,(w-4)/2,0,3,whiteMetal)+block(w,d,w/2,3,h-4,red)+
          block(w-4,d-4,(w-4)/2,h-4,h,whiteMetal)+
          top(h,'<ellipse rx="25" ry="25" fill="none" stroke="#a6b8ac"/>'+rect(-5,-10,10,18,4,'#8fa49a')+rect(-2,-7,4,6,2,'#d7e1db'))+
          front(d/2,58,'<text fill="#fff3e4" font-family="system-ui" font-size="12" font-weight="700" text-anchor="middle">330</text>');
      case 'nuc':
        return block(w,d,6,0,h,dark)+top(h,'<text x="-40" y="-38" fill="#b6c4bd" font-family="system-ui" font-size="9" font-weight="650">NUC</text>')+
          front(d/2,h/2,rect(-40,-3,12,6,1,'#869991')+rect(-22,-3,12,6,1,'#869991')+'<circle cx="38" r="3" fill="#94ad9f"/>');
      case 'pixel':
        return block(w,d,10,0,h,['#bccdc4','#8fa99f','#7c9a8f','#69867b'])+art(coverArt.pixel);
      case 'portrait':
        return block(w,d,.35,0,h,['#fcfcf5','#b6c2a7','#a7b99e','#8c9b83'])+
          art('<image x="-50" y="-70" width="100" height="140" preserveAspectRatio="none" href="'+item.photo+'"/>');
      default: { // Paperbacks lying flat, with separately drawn covers.
        const cover=covers[item.id];
        return block(w,d,2,0,1,cover)+block(w-2,d-2,1.5,1,h-1,pages)+block(w,d,2,h-1,h,cover)+art(coverArt[item.id]);
      }
    }
  }

  function plotRulers(item,scale) {
    const {project,lift}=views[angle], [w,d,h]=item.size;
    const at=(x,y,z)=>{const [u,v]=project(x,y,z);return [u,v+lift];};
    const plan=angle==='iso'||angle==='top';
    const width=['width',w,at(-w/2,d/2,0),at(w/2,d/2,0)];
    const depth=['depth',d,at(w/2,d/2,0),at(w/2,-d/2,0)];
    const edge=angle==='side'?[w/2,-d/2]:[w/2,d/2];
    const height=['height',h,at(...edge,0),at(...edge,h)];
    const segments=plan?[width,depth]:angle==='side'?[depth,height]:[width,height];
    return rulerGroup(item.id,at(0,0,h/2),segments,scale);
  }
  function plotFrame(items) {
    const {project,lift}=views[angle];
    let half=150, top=-122, bottom=127;
    for(const {size:[w,d,h]} of items){
      for(const x of [-w/2,w/2])for(const y of [-d/2,d/2])for(const z of [0,h]){
        const [u,v]=project(x,y,z);
        half=Math.max(half,Math.ceil(Math.abs(u)+41));
        top=Math.min(top,Math.floor(v+lift-19));
        bottom=Math.max(bottom,Math.ceil(v+lift+36));
      }
    }
    return [-half,top,2*half,bottom-top];
  }
  function renderPlot(figure,item,index,box) {
    const {project,lift}=views[angle];
    const svg=figure.querySelector('svg');
    svg.setAttribute('viewBox',box.join(' '));
    const scale=Math.max(.1,svg.clientWidth/box[2]);
    const grid='compare-grid-'+index;
    const envelope='<g class="drawing" data-profile transform="translate(0 '+lift+')">'+solid(item,project)+'</g>';
    const [left,top,w,h]=box;
    const ground=angle==='front'||angle==='side'?'<path d="M'+(left+12)+' '+lift+'h'+(w-24)+'" stroke="#a5b7a9" stroke-width="1"/>':'';
    svg.innerHTML='<defs><pattern id="'+grid+'" width="10" height="10" patternUnits="userSpaceOnUse"><circle r=".65" cx="5" cy="5" fill="#7c9985" opacity=".36" stroke="none"/></pattern></defs>'+
      '<rect x="'+left+'" y="'+top+'" width="'+w+'" height="'+h+'" fill="url(#'+grid+')" stroke="none"/>'+ground+envelope+
      (ruler?plotRulers(item,scale):'');
    figure.querySelector('.compare-size').textContent=sizeText(item,angle);
  }
  function sizeText(item,view) {
    const value=item.round?('Ø'+fmt(item.size[0])+(view==='top'?'':' × '+fmt(item.size[2]))):
      views[view].dims.map(i=>fmt(item.size[i])).join(' × ');
    return (item.approx?'≈ ':'')+value+' мм';
  }
  function renderAngles() {
    for(const button of angleButtons){
      const name=button.dataset.angle;
      button.hidden=mode==='orbit'?name==='side':name==='rear';
      button.setAttribute('aria-pressed',name===(mode==='orbit'?orbitAngle:angle));
    }
  }
  function renderPlots() {
    const items=[enclosure,mac,...(selected?[selected]:[])],box=plotFrame(items);
    items.forEach((item,index)=>renderPlot(plots[index],item,index,box));
    if(!selected)plots[2].querySelector('svg').replaceChildren();
  }
  function render() {
    const in3d=mode==='orbit';
    $('compare-orbit').hidden=!in3d;
    $('compare-plots').hidden=in3d;
    $('compare-ruler').setAttribute('aria-pressed',ruler);
    document.querySelectorAll('.compare-ruler-note').forEach(note=>note.hidden=!ruler);
    modeButtons.forEach(button=>button.setAttribute('aria-pressed',button.dataset.mode===mode));
    objectButtons.forEach(button=>button.setAttribute('aria-pressed',button.dataset.item===(selected?.id||'none')));
    $('compare-object-note').textContent=selected?.caption||'Оберіть предмет, щоб поставити його поруч.';
    renderAngles();
    if(in3d){
      $('compare-orbit-reference').hidden=!selected;
      if(selected){
        $('compare-orbit-name').textContent=selected.name;
        $('compare-orbit-size').textContent=sizeText(selected,'iso');
      }
      orbit?.setReference(selected);
      orbit?.setRuler(ruler);
    }else{
      $('compare-axes').textContent=views[angle].axes;
      plots[2].hidden=!selected;
      $('compare-plots').classList.toggle('cases-only',!selected);
      if(selected)$('compare-object-name').textContent=selected.name;
      renderPlots();
    }
  }

  function chooseAngle(view) {
    if(mode==='orbit'){
      orbitAngle=view;orbit?.preset(view);renderAngles();
    }else{angle=view;render();}
  }
  modeButtons.forEach(button=>button.onclick=()=>{
    mode=button.dataset.mode;render();
    if(mode==='orbit')orbit?.show();
  });
  angleButtons.forEach(button=>button.onclick=()=>chooseAngle(button.dataset.angle));
  objectButtons.forEach(button=>button.onclick=()=>{
    selected=objects.find(item=>item.id===button.dataset.item)||null;
    render();
  });
  $('compare-ruler').onclick=()=>{ruler=!ruler;render();};
  $('compare-bench-source').onclick=()=>{$('compare-sources').open=true;};
  $('compare-out').onclick=()=>orbit?.zoom(1/1.19);
  $('compare-in').onclick=()=>orbit?.zoom(1.19);
  $('compare-reset').onclick=()=>chooseAngle('iso');
  const stage=$('compare-stage');
  stage.addEventListener('keydown',event=>{
    if(!orbit||event.target!==stage||event.ctrlKey||event.altKey||event.metaKey)return;
    const arrows={ArrowLeft:[-.16,0],ArrowRight:[.16,0],ArrowUp:[0,-.16],ArrowDown:[0,.16]};
    if(Object.hasOwn(arrows,event.key))orbit.turn(...arrows[event.key]);
    else if(event.key==='+'||event.key==='=')orbit.zoom(1.19);
    else if(event.key==='-'||event.key==='−')orbit.zoom(1/1.19);
    else if(event.key==='0')chooseAngle('iso');
    else return;
    event.preventDefault();
  });
  $('compare-orbit-case').textContent=sizeText(enclosure,'iso');
  $('compare-orbit-mac').textContent=sizeText(mac,'iso');
  render();
  $('compare-workbench').hidden=false;
  let plotWidth=0;
  new ResizeObserver(([entry])=>{
    const width=entry.contentRect.width;
    if(width&&mode==='diagram'&&width!==plotWidth){plotWidth=width;renderPlots();}
  }).observe($('compare-plots'));
  function unavailable() {
    orbit=undefined;
    stage.dataset.render='unavailable';
    modeButtons[0].disabled=true;
    $('compare-orbit-unavailable').hidden=false;
    mode='diagram';render();
  }
  startOrbit({host:$('compare-surface'),overlay:$('compare-orbit-rulers'),enclosure,mac,unavailable,moved:()=>{
    orbitAngle=null;renderAngles();
  }}).then(controller=>{
    orbit=controller;window.m1Comparison={inspect:controller.inspect};
    if(orbitAngle)orbit.preset(orbitAngle);
    $('compare-loading').hidden=true;
    $('compare-orbit-tools').hidden=false;
    render();stage.dataset.render='3d';
  }).catch(unavailable);
})();
