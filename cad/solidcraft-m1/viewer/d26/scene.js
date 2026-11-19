import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {views,portViews} from './catalog.js';
import ownerFinishes from '../../prototype-d2/photo-study/finishes.json';

const V=(...v)=>new T.Vector3(...v);
const finishes={shell:['#444f51',.12,.54],graphite:['#242d30',.13,.51],faceplate:['#2b2e31',.08,.62],carrier:['#465357',.12,.53],rubber:['#272e2d',.02,.82],
  ...ownerFinishes,
  metal:['#b6c0bf',.72,.29],screw:['#798283',.65,.32],jade:['#498c71',.07,.47],amber:['#b98040',.09,.48],
  pdfr4:['#295847',.13,.41],buckfr4:['#325b85',.15,.42],gauge:['#5cc8ac',.02,.41],tray:['#687879',.12,.58],
  antenna:['#8b7892',.18,.48],board:['#476e5c',.13,.43],alloy:['#aab4b3',.59,.39],port:['#2b3639',.12,.52],
  gold:['#b59965',.62,.35],choke:['#646c70',.20,.51],ceramic:['#bd9e72',.18,.53],body:['#343c3d',.08,.5],v1fr4:['#307864',.18,.40],chip:['#3a474b',.12,.48]};
const power=new Set(['saddle','trigger','buck','socket','floorDetail','lidDetail']);
const boardParts=new Set(['logic','sink','ports','loom','coax','studmarks']);
const serviceViews=new Set(['rear','overview','inside']);
const saddleParts=new Set(['saddle','trigger','buck','socket','fixings']);
function atStops(t,stops,path){
  if(t<=stops[0])return V(...path[0]);
  for(let i=1;i<stops.length;i++)if(t<=stops[i])
    return V(...path[i-1]).lerp(V(...path[i]),phase(t,stops[i-1],stops[i]));
  return V(...path[path.length-1]);
}

const circuit={v1:[0,0,0],j1:[-5,0,0],pdchip:[-5,0,0],converter:[-5,0,0],coil:[-5,0,0],passives:[-5,0,0]};
const groups=new Map(), entries=[];
const desk=new T.Matrix4().makeRotationX(Math.PI/2).scale(V(1000,1000,1000));
// Deterministic kinematics for direct scrubbing, keyboard steps and shared URLs.
// Motion starts and ends at rest at each mechanical stop; the case does not move.
function phase(t,lo,hi){const u=Math.max(0,Math.min(1,(t-lo)/(hi-lo)));return u*u*(3-2*u);}

export async function startScene({stage,surface,leaders,pins,eventPick,eventManual,eventFace,state}){
  const panelTravel=Number(stage.dataset.panelTravel),service=JSON.parse(document.getElementById('service-data').textContent);
  const boardOut=[...service.board_install_xyz_mm].reverse(),pdOut=service.pd_remove_xyz_mm;
  const facade=JSON.parse(document.getElementById('port-data').textContent);
  if(boardOut.length<3||boardOut[0].some(x=>x!==0))throw Error('Missing verified board installation stops');
  if(!(panelTravel>0))throw Error('Missing CAD panel travel');
  const renderer=new T.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.8)); renderer.setClearColor(0x000000,0);
  renderer.outputColorSpace=T.SRGBColorSpace; renderer.toneMapping=T.ACESFilmicToneMapping; renderer.toneMappingExposure=.96;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFShadowMap;
  surface.append(renderer.domElement);
  const world=new T.Scene(),camera=new T.OrthographicCamera(-100,100,100,-100,.1,1900);
  camera.up.set(0,0,1);camera.position.set(-100,-160,120);
  const pmrem=new T.PMREMGenerator(renderer),room=new RoomEnvironment(),env=pmrem.fromScene(room,.03);
  world.environment=env.texture;world.environmentIntensity=.54;room.dispose();pmrem.dispose();
  world.add(new T.HemisphereLight(0xe9f4ff,0x909c8c,1.06));
  const key=new T.DirectionalLight(0xfff4df,2.45),fill=new T.DirectionalLight(0xd5e9ff,1.1),rim=new T.DirectionalLight(0xffffff,.9);
  world.add(key,key.target,fill,rim); fill.position.set(95,90,90);rim.position.set(30,-110,100);
  key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.normalBias=.07;key.shadow.bias=-.0004;key.shadow.radius=3;
  const ground=new T.Mesh(new T.PlaneGeometry(1800,1800),new T.ShadowMaterial({opacity:.135,depthWrite:false}));
  ground.receiveShadow=true;world.add(ground);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=false;controls.enablePan=true;
  controls.minZoom=.35;controls.maxZoom=7; controls.zoomSpeed=.92; controls.rotateSpeed=.80;
  let w=1,h=1,half=100,manual=false,frame=0,framed=false,pinElements=[],travelArrow=null,overlayKey='',visible=[],bounds=new T.Box3(),lastState={};
  const ray=new T.Raycaster(),vec2=new T.Vector2(),vp=V();
  function request(){if(!frame)frame=requestAnimationFrame(()=>{
    frame=0;
    if(state.view==='board'&&manual){
      const side=camera.position.z>=controls.target.z?'top':'back';
      if(side!==state.side)eventFace(side);
    }
    renderer.render(world,camera);positionPins();
  });}
  function didMove(){manual=true;eventManual?.();}
  controls.addEventListener('change',request);controls.addEventListener('start',didMove);

  const raw=Uint8Array.from(atob(document.getElementById('model-bytes').textContent.trim()),c=>c.charCodeAt(0));
  const bytes=await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const {scene}=await new GLTFLoader().parseAsync(bytes,'');scene.updateMatrixWorld(true);
  const materials=new Map();
  scene.traverse(o=>{
    if(!o.isMesh)return;
    const [layer,id,finish]=o.name.split('__'); if(!finishes[finish])throw Error('Unknown finish: '+o.name);
    if(!groups.has(id)){const g=new T.Group();groups.set(id,g);world.add(g);}
    const faceOnly=layer==='photo'&&['logic','coax','studmarks'].includes(id);
    const k=id+':'+finish+(faceOnly?':face':''),[color,metalness,roughness]=finishes[finish];
    if(!materials.has(k))materials.set(k,new T.MeshStandardMaterial({color,metalness,roughness,side:faceOnly?T.FrontSide:T.DoubleSide,flatShading:['logic','sink','rf','ports'].includes(id),
      transparent:layer==='gauge',opacity:layer==='gauge'?.27:1,depthWrite:layer!=='gauge'}));
    const geo=o.geometry.clone().applyMatrix4(desk.clone().multiply(o.matrixWorld));geo.computeBoundingBox();
    const mesh=new T.Mesh(geo,materials.get(k));mesh.userData={id,layer,finish,source:o.name.split('__').slice(3).join('__'),base:geo.boundingBox.clone()};
    mesh.castShadow=mesh.receiveShadow=layer!=='gauge';groups.get(id).add(mesh); entries.push(mesh);
  });
  // A rear-facing depth buffer of the actual assembly supplies ambient
  // occlusion inside bores and narrow seams. It contains no port silhouettes
  // or painted overlays. The hemi-spherical horizon is sampled in millimetres;
  // separated/isolated/board views use their original studio materials.
  const frontPanel=entries.find(m=>m.userData.id==='panel').userData.base;
  const xmin=frontPanel.min.x-3,xmax=frontPanel.max.x+3,zmin=frontPanel.min.z-3,zmax=frontPanel.max.z+3;
  const fieldW=xmax-xmin,fieldH=zmax-zmin,depthTarget=new T.WebGLRenderTarget(2048,Math.max(128,Math.round(2048*fieldH/fieldW)),{minFilter:T.NearestFilter,magFilter:T.NearestFilter,depthBuffer:true});
  depthTarget.depthTexture=new T.DepthTexture(depthTarget.width,depthTarget.height,T.UnsignedIntType);
  const frontCamera=new T.OrthographicCamera(-fieldW/2,fieldW/2,fieldH/2,-fieldH/2,.1,80.1);
  frontCamera.up.set(0,0,1);frontCamera.position.set((xmax+xmin)/2,facade.face_y_mm+12,(zmax+zmin)/2);
  frontCamera.lookAt(frontCamera.position.clone().add(V(0,-1,0)));frontCamera.updateMatrixWorld();
  const depthScene=new T.Scene(),depthMat=new T.MeshBasicMaterial({side:T.DoubleSide,colorWrite:false});
  for(const m of entries){const {id,layer}=m.userData;
    if(id==='rf'||['gauge','v1','cutaway'].includes(layer))continue;
    const occluder=new T.Mesh(m.geometry,depthMat);depthScene.add(occluder);
  }
  renderer.setRenderTarget(depthTarget);renderer.clear();renderer.render(depthScene,frontCamera);renderer.setRenderTarget(null);depthScene.clear();depthMat.dispose();
  const frontAO={value:0},shaderHead=`
    uniform sampler2D atlasDepth;uniform vec4 atlasField;uniform vec2 atlasY;uniform float atlasRearAO;
    varying vec3 atlasDesk;
    float atlasHorizon(vec2 p,vec2 dir,float radial){
      vec2 q=(p+dir*radial-atlasField.xy)/atlasField.zw;
      if(any(lessThan(q,vec2(0.0)))||any(greaterThan(q,vec2(1.0))))return 0.0;
      float d=texture2D(atlasDepth,vec2(1.0-q.x,q.y)).x;if(d>=.99998)return 0.;
      float surfaceY=atlasY.y-80.0*d;
      return max(0.0,(surfaceY-atlasDesk.y-.045)/radial);
    }
    float atlasAmbient(vec3 normalView){
      if(atlasRearAO<.5||atlasDesk.y>=atlasY.x-.09||dot(normalView,(viewMatrix*vec4(0.,1.,0.,0.)).xyz)<.3)return 1.0;
      vec2 p=atlasDesk.xz;
      if(any(lessThan(p,atlasField.xy))||any(greaterThan(p,atlasField.xy+atlasField.zw)))return 1.0;
      float sum=0.0;
      for(int i=0;i<12;++i){
        float a=float(i)*.52359878;vec2 dir=vec2(cos(a),sin(a));
        float h=0.0;float r=.15;
        for(int j=0;j<11;++j){h=max(h,atlasHorizon(p,dir,r));r*=1.49;}
        sum+=1.0/(1.0+h*h);
      }
      return .014+.986*pow(sum/12.0,1.92);
    }`;
  for(const mat of materials.values()){
    mat.onBeforeCompile=shader=>{
      Object.assign(shader.uniforms,{atlasDepth:{value:depthTarget.depthTexture},atlasField:{value:new T.Vector4(xmin,zmin,fieldW,fieldH)},atlasY:{value:new T.Vector2(facade.face_y_mm,frontCamera.position.y-frontCamera.near)},atlasRearAO:frontAO});
      shader.vertexShader='varying vec3 atlasDesk;\n'+shader.vertexShader.replace('#include <project_vertex>','atlasDesk=(modelMatrix*vec4(transformed,1.0)).xyz;\n#include <project_vertex>');
      shader.fragmentShader=shaderHead+'\n'+shader.fragmentShader.replace('#include <opaque_fragment>','outgoingLight *= atlasAmbient(normal);\n#include <opaque_fragment>');
    };
  }
  // Surface ink from the existing studio illustrations, never a structural solid.
  const inks=[];
  function ink(id,text,at,xaxis,normal,width,height,color){
    const c=document.createElement('canvas');c.width=384;c.height=112;const g=c.getContext('2d');
    g.font='600 82px Arial';g.fillStyle=color;g.textAlign='center';g.textBaseline='middle';g.fillText(text,192,58);
    const map=new T.CanvasTexture(c);map.colorSpace=T.SRGBColorSpace;
    const mat=new T.MeshBasicMaterial({map,transparent:true,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2,toneMapped:false});
    const m=new T.Mesh(new T.PlaneGeometry(width,height),mat);
    m.setRotationFromMatrix(new T.Matrix4().makeBasis(V(...xaxis),V(0,0,1),V(...normal)));m.position.set(...at);
    groups.get(id).add(m);inks.push([id,m]);
  }
  const registered=(id,point)=>V(...point).add(V(...(service.power_datum_offsets_xyz_mm?.[id]||[0,0,0])));
  ink('buck','4R7',registered('buck',[-82.10,-6.20,26]).toArray(),[0,-1,0],[-1,0,0],8.3,4.1,'#333a3b');
  function included(m){
    const {layer,id}=m.userData,view=state.view;
    if(state.solo&&state.selected!==id)return false;
    if(serviceViews.has(view)&&!state.solo){
      const s=state.spread;
      if(s>=36&&['lid','lidscrews'].includes(id)||s>=44&&id==='pcbscrews'||s>=54&&saddleParts.has(id)||s>=74&&(boardParts.has(id)||id==='rf'))return false;
    }
    if(id==='rf')return view==='inside'&&state.rf;
    const boardInView=['inside','board'].includes(view)||serviceViews.has(view)&&state.spread>=36;
    if((layer==='photo'&&id!=='sink'||['loom','coax','studmarks'].includes(id))&&!boardInView)return false;
    if(view==='pcb')return layer==='v1';
    if(layer==='cutaway'&&(view!=='power'||!state.mounts||id==='lidDetail'&&state.spread>=40&&!state.solo))return false;
    if(layer==='v1'||layer==='gauge'&&!(view==='power'&&state.gauges))return false;
    if(layer==='portrait')throw Error('Obsolete illustrative port shells cannot be drawn in D2.6');
    if(view==='board')return boardParts.has(id)&&(state.side!=='back'||layer!=='photo'||id==='sink');
    if(view==='power')return power.has(id);
    if(view==='base')return id==='chassis';
    if(view==='inside')return id!=='lid'&&id!=='lidscrews';
    return true;
  }
  function offset(id){
    const t=state.spread/100;
    if(state.view==='board')return V(0,0,0);
    if(serviceViews.has(state.view)){
      const q=state.spread;
      // The lid is parked off camera. Only documented CAD waypoints move the two port-bearing assemblies.
      if(id==='lid'||id==='lidscrews')return V(0,-126*phase(q,18,36)||0,28*phase(q,6,18)+(id==='lidscrews'?8*phase(q,0,6):0));
      if(id==='pcbscrews')return V(0,0,14*phase(q,36,44));
      if(saddleParts.has(id)&&pdOut?.length>1)return atStops(q,pdOut.map((_,i)=>44+10*i/(pdOut.length-1)),pdOut);
      if(boardParts.has(id)||id==='rf')return atStops(q,service.board_remove_stops_pct,boardOut);
      if(id==='panel')return atStops(q,service.panel_remove_stops_pct,service.panel_remove_xyz_mm);
      return V();
    }
    if(state.view==='power'){
      if(!state.mounts)return V(0,0,id==='saddle'?0:20*t);
      if(id==='lidDetail')return V(0,0,28*phase(state.spread,0,40));
      if(id==='floorDetail')return V(0,0,0);
      if(saddleParts.has(id))return atStops(state.spread,service.pd_detail_stops_pct,pdOut);
      return V();
    }
    const layout=state.view==='pcb'?circuit:{};
    return V(...(layout[id]||[0,0,0])).multiplyScalar(t);
  }
  function baseDirection(){
    const view=views[state.view],dir=V(...(state.view==='board'&&state.side==='back'?view.backDirection:view.direction));
    if(state.view==='rear'){
      if(state.solo&&state.selected==='panel')return state.side==='back'?V(.22,-1,.53).normalize():V(0,1,0);
      if(state.solo&&state.selected==='lid')return V(.26,1,-.87).normalize();
      if(state.solo&&state.selected==='chassis')return V(.37,1,1.14).normalize();
      const reveal=phase(state.spread,6,36);dir.x+=.48*reveal;dir.z+=.99*reveal;
    }
    return dir.normalize();
  }
  function recalc(){
    bounds.makeEmpty();visible=[];
    frontAO.value=serviceViews.has(state.view)&&state.view!=='inside'&&state.spread===0&&!state.solo?1:0;
    key.castShadow=!(state.view==='rear'&&frontAO.value);
    const used=new Set();
    for(const [id,g] of groups)g.position.copy(offset(id));
    for(const m of entries){
      m.visible=included(m);if(!m.visible)continue;
      visible.push(m);const b=m.userData.base.clone().translate(m.parent.position);bounds.union(b);
      if(used.has(m.material))continue;used.add(m.material);
      const selected=state.selected===m.userData.id&&!state.solo;
      m.material.emissive.set(selected?'#287d55':'#000000');m.material.emissiveIntensity=selected?.33:0;
    }
    const shown=new Set(visible.map(m=>m.userData.id));for(const [id,m] of inks)m.visible=shown.has(id);
    world.updateMatrixWorld(true);
    if(bounds.isEmpty())throw Error('Empty view');
    const c=bounds.getCenter(V()),extent=Math.max(...bounds.getSize(V()).toArray(),18);
    ground.position.z=bounds.min.z-Math.max(.38,extent*.008);
    ground.visible=!state.solo&&!['rear','pcb','board'].includes(state.view);
    const insidePanel=state.view==='rear'&&state.solo&&state.selected==='panel'&&state.side==='back';
    const exterior=['overview','rear'].includes(state.view)&&!insidePanel;
    key.target.position.copy(c);key.position.copy(c).addScaledVector(exterior?V(-.78,1.0,1.6):V(-.78,-.66,1.8),extent*1.6);
    Object.assign(key.shadow.camera,{left:-extent*.77,right:extent*.77,top:extent*.77,bottom:-extent*.77,near:1,far:extent*7});key.shadow.camera.updateProjectionMatrix();
  }
  const clipped=(val,lo,hi)=>Math.min(Math.max(lo,val),hi);
  function fitted(dir){
    if(state.view==='rear'&&state.spread===0&&!state.solo&&dir.y>.9999){
      const mask=portViews[state.port]?.ids,rows=facade.ports.filter(o=>!mask||mask.includes(o.id));
      const boxes=rows.map(o=>o.bounds_xz_mm);
      const lo=[0,1].map(i=>Math.min(...boxes.map(b=>b[0][i]))),hi=[0,1].map(i=>Math.max(...boxes.map(b=>b[1][i])));
      const full=state.port==='all';
      if(full){
        const span=bounds.getSize(V()),center=bounds.getCenter(V());
        return {target:V(center.x,facade.face_y_mm,center.z),half:Math.max(span.x/2/(w/h)/.93,span.z/2/.77)};
      }
      const pad=Math.max(2.8,(hi[0]-lo[0])*.13),width=hi[0]-lo[0]+2*pad,height=hi[1]-lo[1]+9;
      return {target:V((lo[0]+hi[0])/2,facade.face_y_mm,(lo[1]+hi[1])/2),half:Math.max(width/(2*w/h)/.89,height/2/.78)};
    }
    const right=V().crossVectors(camera.up,dir).normalize(),up=V().crossVectors(dir,right).normalize();
    let x1=Infinity,x2=-Infinity,y1=Infinity,y2=-Infinity;
    for(const m of visible){
      const b=m.userData.base,off=m.parent.position;
      for(const x of [b.min.x,b.max.x])for(const y of [b.min.y,b.max.y])for(const z of [b.min.z,b.max.z]){
        vp.set(x,y,z).add(off);const xx=vp.dot(right),yy=vp.dot(up);
        x1=Math.min(x1,xx);x2=Math.max(x2,xx);y1=Math.min(y1,yy);y2=Math.max(y2,yy);
      }
    }
    const center=bounds.getCenter(V()),target=right.multiplyScalar((x1+x2)/2).addScaledVector(up,(y1+y2)/2).addScaledVector(dir,center.dot(dir));
    return {target,half:Math.max((y2-y1)/2/(state.view==='inside'?.79:.73),(x2-x1)/2/(w/h)/.83,2)};
  }
  function projection(){camera.left=-half*w/h;camera.right=half*w/h;camera.top=half;camera.bottom=-half;camera.updateProjectionMatrix();}
  function applyPose(dir,target,hh,zoom=1){
    half=hh;camera.zoom=clipped(zoom,.35,7);projection();controls.target.copy(target);
    camera.position.copy(target).addScaledVector(dir,520);camera.lookAt(target);controls.update();framed=true;request();
  }
  function fit(dir=baseDirection()){
    const f=fitted(dir);applyPose(dir,f.target,f.half);
  }
  function resize(){
    const rect=stage.getBoundingClientRect();if(!rect.width||!rect.height)return;
    const changed=Math.round(rect.width)!==w||Math.round(rect.height)!==h;
    const dir=changed&&visible.length&&manual&&framed?camera.position.clone().sub(controls.target).normalize():null;
    const previousFit=dir?fitted(dir).half:0;
    w=Math.round(rect.width);h=Math.round(rect.height);renderer.setSize(w,h,false);
    if(visible.length&&changed){
      if(dir){half*=fitted(dir).half/previousFit;projection();}else fit();
    }request();
  }
  function makePins(){
    const mode=state.view==='rear'&&state.spread===74?'seated':state.view==='rear'&&state.spread>74?'separated':state.view==='rear'&&state.spread>=54?'moving':state.view==='rear'&&state.spread>=16?'released':state.mounts?'sectionPins':'pins';
    const signature=[state.view,state.port,mode,state.selected,state.solo,state.labels].join(':');if(signature===overlayKey)return;overlayKey=signature;
    leaders.replaceChildren();pins.replaceChildren();pinElements=[];travelArrow=null;
    if(!state.labels||state.solo)return;
    const ns='http://www.w3.org/2000/svg';
    if(state.view==='rear'){
      travelArrow=document.createElementNS(ns,'path');travelArrow.dataset.travelAxis='0,0,1';travelArrow.setAttribute('fill','none');
      travelArrow.setAttribute('stroke','#156b50');travelArrow.setAttribute('stroke-width','2.4');travelArrow.setAttribute('stroke-linecap','round');travelArrow.setAttribute('stroke-linejoin','round');leaders.append(travelArrow);
    }
    const view=views[state.view];
    for(const spec of (view[mode]||view.pins)){
      if(state.view==='rear'&&mode==='pins'&&state.port!=='all'){
        const use=portViews[state.port].ids.some(id=>Math.abs(facade.ports.find(o=>o.id===id).axis_xz_mm[0]-spec.point[0])<1);
        if(!use)continue;
      }
      const b=document.createElement('button');b.type='button';b.className='pin';b.dataset.part=spec.part;
      const i=views[state.view].list.indexOf(spec.part);if(!['rear','base'].includes(state.view)&&i>=0){const n=document.createElement('b');n.textContent=String(i+1).padStart(2,'0');b.append(n);}
      b.append(spec.label);b.title='Вибрати: '+spec.label;b.setAttribute('aria-pressed',String(state.selected===spec.part));b.onclick=()=>eventPick(spec.part);
      const g=document.createElementNS(ns,'g'),ln=document.createElementNS(ns,'path'),dot=document.createElementNS(ns,'circle');
      ln.setAttribute('fill','none');ln.setAttribute('stroke','#557562');ln.setAttribute('opacity','.78');dot.setAttribute('r','2.6');dot.setAttribute('stroke','#e9f1e8');dot.setAttribute('stroke-width','1');dot.setAttribute('fill','#2d5944');
      g.append(ln,dot);let pair=null;if(spec.pair){const path=ln.cloneNode(),tip=dot.cloneNode();g.append(path,tip);pair={path,tip};}
      leaders.append(g);pins.append(b);pinElements.push({spec,b,g,ln,dot,pair});
    }
  }
  function positionPins(){
    const placed=[],dir=camera.position.clone().sub(controls.target).normalize(),exterior=state.view==='rear'||state.view==='overview',checkOcclusion=exterior||manual&&dir.dot(baseDirection())<.80;
    if(travelArrow){
      const start=V(-96,60,33),end=start.clone().add(offset('panel')),s=start.project(camera),e=end.project(camera);
      const x0=(1+s.x)*w/2,y0=(1-s.y)*h/2,x1=(1+e.x)*w/2,y1=(1-e.y)*h/2,len=Math.hypot(x1-x0,y1-y0);
      travelArrow.style.display=len>8?'':'none';
      if(len>8){const dx=(x1-x0)/len,dy=(y1-y0)/len;travelArrow.setAttribute('d',`M${x0} ${y0}L${x1} ${y1}m${-dx*6-dy*4} ${-dy*6+dx*4}L${x1} ${y1}l${-dx*6+dy*4} ${-dy*6-dx*4}`);}
    }
    function exposed(pt,id){
      if(!checkOcclusion)return true;
      ray.set(pt.clone().addScaledVector(dir,550),dir.clone().negate());
      const hit=ray.intersectObjects(visible,false).find(o=>o.object.userData.layer!=='gauge');
      return !hit||hit.distance>546||(hit.object.userData.id===id&&(!exterior||hit.distance>541));
    }
    for(const {spec,b,g,ln,dot,pair} of pinElements){
      if(!visible.some(m=>m.userData.id===spec.part)||state.view==='board'&&dir.z<.12){b.hidden=true;g.style.display='none';continue;}
      const pt=registered(spec.part,spec.point).add(offset(spec.part)),screen=pt.clone().project(camera);
      const x=(screen.x+1)*w/2,y=(1-screen.y)*h/2;
      let show=x>3&&x<w-3&&y>8&&y<h-8;
      if(show&&!exposed(pt,spec.part))show=false;
      b.hidden=!show;g.style.display=show?'':'none';if(!show)continue;
      const bw=b.offsetWidth,bh=b.offsetHeight,dx=spec.offset[0]*(w<450?.77:1),dy=spec.offset[1];
      const bx=clipped(x+dx+(dx>15?0:dx< -15?-bw:-bw/2),5,w-bw-5);
      let by=clipped(y+dy-bh/2,42,h-bh-41);
      for(const delta of [0,-26,26,-52,52,-78,78]){
        const cy=clipped(by+delta,40,h-bh-39);
        if(!placed.some(p=>bx<p.x+p.w+3&&bx+bw+3>p.x&&cy<p.y+p.h+2&&cy+bh+2>p.y)){by=cy;break;}
      }
      placed.push({x:bx,y:by,w:bw,h:bh});b.style.transform='translate('+bx.toFixed(1)+'px,'+by.toFixed(1)+'px)';
      const ex=clipped(x,bx+4,bx+bw-4),ey=clipped(y,by+2,by+bh-2);
      ln.setAttribute('d','M'+x.toFixed(1)+' '+y.toFixed(1)+' L'+ex.toFixed(1)+' '+ey.toFixed(1));dot.setAttribute('cx',x);dot.setAttribute('cy',y);
      if(pair){const p=registered(spec.part,spec.pair).add(offset(spec.part)),s=p.clone().project(camera),cx=(s.x+1)*w/2,cy=(1-s.y)*h/2;
        const showPeer=exposed(p,spec.part)&&cx>=3&&cx<w-3&&cy>=8&&cy<h-8;
        pair.path.style.display=pair.tip.style.display=showPeer?'':'none';
        pair.path.setAttribute('d',`M${cx.toFixed(1)} ${cy.toFixed(1)} L${ex.toFixed(1)} ${ey.toFixed(1)}`);pair.tip.setAttribute('cx',cx);pair.tip.setAttribute('cy',cy);}
    }
  }
  let pointer;
  renderer.domElement.addEventListener('pointerdown',e=>{if(e.isPrimary&&e.button===0)pointer=[e.pointerId,e.clientX,e.clientY];else pointer=null;});
  renderer.domElement.addEventListener('pointercancel',()=>pointer=null);
  renderer.domElement.addEventListener('pointerup',e=>{
    if(!pointer||pointer[0]!==e.pointerId||Math.hypot(e.clientX-pointer[1],e.clientY-pointer[2])>5){pointer=null;return;}pointer=null;
    const rect=renderer.domElement.getBoundingClientRect();vec2.set((e.clientX-rect.left)*2/w-1,1-(e.clientY-rect.top)*2/h);
    ray.setFromCamera(vec2,camera);const hit=ray.intersectObjects(visible,false).find(o=>o.object.userData.layer!=='gauge');
    if(hit)eventPick(hit.object.userData.id);
  });
  function update(force=false){
    const viewChanged=state.view!==lastState.view,soloChanged=state.solo!==lastState.solo||state.solo&&state.selected!==lastState.selected;
    recalc();if(force||viewChanged||soloChanged||!framed){manual=false;fit();}
    else if(lastState.spread!==state.spread){
      if(!manual)fit();else{const d=camera.position.clone().sub(controls.target).normalize();half=fitted(d).half;projection();}
    }
    makePins();lastState={...state};request();
  }
  function zoom(factor){didMove();camera.zoom=clipped(camera.zoom*factor,.35,7);camera.updateProjectionMatrix();controls.update();request();}
  function rotate(a,e){didMove();const d=camera.position.clone().sub(controls.target).normalize(),theta=Math.atan2(d.y,d.x)+a,phi=clipped(Math.asin(d.z)+e,-1.5,1.5);applyPose(V(Math.cos(theta)*Math.cos(phi),Math.sin(theta)*Math.cos(phi),Math.sin(phi)),controls.target.clone(),half,camera.zoom);}
  function pose(){
    if(!manual)return null;const d=camera.position.clone().sub(controls.target).normalize();
    return [...d.toArray(),...controls.target.toArray(),camera.zoom*fitted(d).half/half].map(x=>Number(x.toFixed(4))).join(',');
  }
  function restore(s){
    if(!s)return;const a=s.split(',').map(Number);if(a.length!==7||!a.every(Number.isFinite)||a.slice(3,6).some(n=>Math.abs(n)>1500))return;
    const d=V(...a.slice(0,3));if(d.length()<.5||d.length()>1.5||Math.abs(d.normalize().z)>.99999)return;
    manual=true;applyPose(d,V(...a.slice(3,6)),fitted(d).half,a[6]);
  }
  // Project exactly the same desk-mm probe through the current camera and report
  // the front-most actually included mesh. The browser proof compares the pixels
  // at this location with an isolated plate at the same physical probe.
  function frontProbe(x,z){
    const pt=V(x,facade.face_y_mm,z),q=pt.clone().project(camera);
    const r=new T.Raycaster(V(x,facade.face_y_mm+12,z),V(0,-1,0),0,80);
    const hit=r.intersectObjects(visible,false)[0];
    return {pixel:[(1+q.x)*w/2,(1-q.y)*h/2],viewport:[w,h],hit:hit?{group:hit.object.userData.id,layer:hit.object.userData.layer,source:hit.object.userData.source,finish:hit.object.userData.finish,y_mm:hit.point.y}:null};
  }
  resize();update(true);new ResizeObserver(resize).observe(stage);
  return {update,zoom,rotate,pose,restore,frontProbe,reset:()=>{manual=false;fit();},visible:()=>[...new Set(visible.map(m=>m.userData.id))],count:()=>visible.length,
    sources:id=>visible.filter(m=>m.userData.id===id).map(m=>m.userData.source).sort(),boardFinishes:()=>[...new Set(visible.filter(m=>boardParts.has(m.userData.id)).map(m=>m.userData.finish))].sort(),groundVisible:()=>ground.visible,
    positions:()=>Object.fromEntries([...new Set(visible.map(m=>m.userData.id))].map(id=>[id,groups.get(id).position.toArray()]))};
}
