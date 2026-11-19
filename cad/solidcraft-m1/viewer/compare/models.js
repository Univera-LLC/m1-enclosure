import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {toCreasedNormals} from 'three/addons/utils/BufferGeometryUtils.js';
import hardwareFinishes from '../../prototype-d2/photo-study/finishes.json';
import {coverArt} from './art.js';

const vec=(...p)=>new T.Vector3(...p);
const material=(color,metalness=0,roughness=.56)=>new T.MeshStandardMaterial({color,metalness,roughness});
const surfaceColors={shell:'#465253',faceplate:'#2b3234',graphite:'#262c2c',rubber:'#272c2b',screw:'#99a6a7'};

function put(group,geo,mat,x=0,y=0,z=0) {
  const mesh=new T.Mesh(geo,mat);
  mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);
  return mesh;
}

// The drawn radius is in plan view. A separate bevel keeps the height exact.
function slab(group,w,d,y,h,r,mat,bevel=0) {
  bevel=Math.min(bevel,h/4,r/2);
  const x=w/2-bevel, z=d/2-bevel;
  r=Math.min(r-bevel,x,z);
  const s=new T.Shape();
  s.moveTo(-x+r,-z);s.lineTo(x-r,-z);s.quadraticCurveTo(x,-z,x,-z+r);
  s.lineTo(x,z-r);s.quadraticCurveTo(x,z,x-r,z);
  s.lineTo(-x+r,z);s.quadraticCurveTo(-x,z,-x,z-r);
  s.lineTo(-x,-z+r);s.quadraticCurveTo(-x,-z,-x+r,-z);
  const geo=new T.ExtrudeGeometry(s,{depth:h-2*bevel,bevelEnabled:bevel>0,bevelSize:bevel,
    bevelThickness:bevel,bevelSegments:3,curveSegments:10}).rotateX(-Math.PI/2);
  return put(group,bevel?toCreasedNormals(geo,Math.PI/4):geo,mat,0,y+bevel);
}
const cylinder=(group,r1,r2,y,h,mat)=>
  put(group,new T.CylinderGeometry(r2,r1,h,48),mat,0,y+h/2);

function ink(group,geometry,map,x,y,z,rotX=0) {
  const m=new T.Mesh(geometry,new T.MeshBasicMaterial({map,transparent:true,depthWrite:false,toneMapped:false,
    polygonOffset:true,polygonOffsetFactor:-2}));
  m.position.set(x,y,z);m.rotation.x=rotX;group.add(m);return m;
}
function canvasTexture(width,height,paint) {
  const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
  paint(canvas.getContext('2d'));
  const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;return texture;
}
function faceInk(group,w,h,y,z,text) {
  const tex=canvasTexture(256,100,c=>{
    c.fillStyle='#fff5df';c.font='600 64px system-ui';c.textAlign='center';c.textBaseline='middle';
    c.fillText(text,128,50);
  });
  return ink(group,new T.PlaneGeometry(w,h),tex,0,y,z);
}
function topInk(group,item,request) {
  const art=coverArt[item.id];
  if(!item.photo&&!art)return;
  const [w,d,h]=item.size;
  const src=item.photo||'data:image/svg+xml,'+encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="560" viewBox="-50 -70 100 140">'+art+'</svg>');
  const map=new T.TextureLoader().load(src,request);
  map.colorSpace=T.SRGBColorSpace;map.anisotropy=4;
  if(item.photo){
    const paper=new T.MeshStandardMaterial({map,roughness:.87,polygonOffset:true,polygonOffsetFactor:-2});
    const surface=new T.Mesh(new T.PlaneGeometry(w,d).rotateX(-Math.PI/2),paper);
    surface.position.y=h;surface.receiveShadow=true;group.add(surface);
  }else{ink(group,new T.PlaneGeometry(w,d),map,0,h,0,-Math.PI/2);}
}

async function readModel(packed) {
  const raw=Uint8Array.from(atob(packed),c=>c.charCodeAt(0));
  const buffer=await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const {scene}=await new GLTFLoader().parseAsync(buffer,'');
  return scene;
}

export async function macModel([w,d,h],packed) {
  const scene=await readModel(packed);
  // In the source GLB +Z faces the ports; the comparison uses +Z for the front.
  scene.rotation.y=Math.PI;
  const box=new T.Box3().setFromObject(scene,true),size=box.getSize(vec());
  scene.scale.set(w/size.x,h/size.y,d/size.z);
  box.setFromObject(scene,true);
  const center=box.getCenter(vec());
  scene.position.set(-center.x,-box.min.y,-center.z);
  scene.traverse(mesh=>{
    if(!mesh.isMesh)return;
    mesh.castShadow=mesh.receiveShadow=true;
    if(mesh.material.name==='Logo')mesh.material.roughness=.32;
  });
  const group=new T.Group();
  group.add(scene);
  return group;
}

export function referenceModel(item,request) {
  const group=new T.Group(),[w,d,h]=item.size;
  switch(item.id){
    case 'aa':
      cylinder(group,w/2,w/2,0,1.4,material('#9da8a6',.55,.37));
      cylinder(group,w/2,w/2,1.4,h-12.4,material('#242d2c',.22,.42));
      cylinder(group,w/2,w/2,h-11,8.4,material('#c59b68',.69,.31));
      cylinder(group,w/2,w/2,h-2.6,.6,material('#aa834f',.55,.32));
      cylinder(group,3,2.75,h-2,2,material('#d0ddd7',.74,.34));
      faceInk(group,9,3.6,21,d/2,'AA');break;
    case 'cola': {
      const metal=material('#c7cecc',.78,.33);
      const body=new T.MeshPhysicalMaterial({color:'#bf322c',metalness:.38,roughness:.32,clearcoat:.7});
      cylinder(group,30,w/2,0,4,metal);cylinder(group,w/2,w/2,4,h-12,body);
      cylinder(group,w/2,30,h-8,6,body);cylinder(group,29.3,29.3,h-2,1.1,metal);
      const rim=new T.TorusGeometry(29.25,.55,12,72).rotateX(-Math.PI/2);
      put(group,rim,metal,0,h-.55,0);
      const opening=new T.CircleGeometry(5,36);opening.scale(1,1.35,1);opening.rotateX(-Math.PI/2);
      put(group,opening,material('#515d5d',.31,.58),0,h-.88,14);
      const tab=new T.TorusGeometry(3.8,.75,10,30);tab.scale(.79,1.5,.50);tab.rotateX(-Math.PI/2);
      put(group,tab,metal,0,h-.46,1);
      faceInk(group,34,14,h*.56,d/2,'330');
      break;
    }
    case 'portrait':
      slab(group,w,d,0,h,.25,material('#fffaf1',0,.9));break;
    case 'pixel': {
      const metal=material('#9dafac',.78,.3),glass=material('#253536',.47,.2);
      slab(group,w-.4,d-.4,0,.9,9,glass,.21);
      slab(group,w,d,.82,h-2.4,9,metal,.64);
      slab(group,w-1,d-1,h-2.02,.69,8.7,material('#a5c0b7',.18,.41),.15);
      const island=slab(group,w*.8,15,h-1.35,1.1,6,metal,.22);island.position.z=-d*.34;
      const plate=slab(group,w*.75,12,h-.40,.2,5,glass,.04);plate.position.z=-d*.34;
      const lens=material('#25393e',.36,.15),rim=material('#71858a',.72,.29);
      for(const x of [-17,-5,7]){
        put(group,new T.CylinderGeometry(4.1,4.1,.2,32),rim,x,h-.16,-d*.34);
        put(group,new T.CylinderGeometry(3.5,3.5,.14,36),lens,x,h-.07,-d*.34);
      }
      put(group,new T.CylinderGeometry(1.7,1.7,.13,26),material('#e0d7b4'),20,h-.065,-d*.34);
      break;
    }
    case 'nuc': {
      slab(group,w,d,0,h,6,material('#3e4947',.12),.55);
      const portMat=new T.MeshBasicMaterial({color:'#889c94',polygonOffset:true,polygonOffsetFactor:-2});
      for(const x of [-33,-14]){
        const p=put(group,new T.PlaneGeometry(13,5),portMat,x,h*.5,d/2);p.castShadow=false;
      }
      break;
    }
    default: {
      const cover=material(item.id==='berserk'?'#612f35':'#2b4857',.08,.52);
      slab(group,w,d,0,1,1.3,cover);
      slab(group,w-1,d-1,1,h-2,.9,material('#dfd1af'));
      slab(group,w,d,h-1,1,1.3,cover);
      const paper=canvasTexture(384,160,c=>{
        c.fillStyle='#e9dfc9';c.fillRect(0,0,384,160);
        for(let n=0;n<80;n++){
          c.fillStyle=n%7===0?'#c7bda7':n%3===0?'#ddd1b9':'#e2d8c1';c.fillRect(0,n*2,384,1);
        }
      });
      ink(group,new T.PlaneGeometry(w-2,h-2.2),paper,0,h/2,(d-1)/2);
      break;
    }
  }
  if(item.id!=='pixel')topInk(group,item,request);
  return group;
}

function printGrain() {
  const texture=canvasTexture(128,128,c=>{
    c.fillStyle='#808080';c.fillRect(0,0,128,128);
    for(let y=0;y<128;y+=16){
      c.fillStyle='#595959';c.fillRect(0,y,128,3);
      c.fillStyle='#a1a1a1';c.fillRect(0,y+4,128,2);
    }
  });
  texture.colorSpace=T.NoColorSpace;texture.wrapS=texture.wrapT=T.RepeatWrapping;
  return texture;
}

function grainUV(geometry) {
  const p=geometry.getAttribute('position'),n=geometry.getAttribute('normal'),uv=new Float32Array(p.count*2);
  for(let i=0;i<p.count;i++){
    const horizontal=Math.abs(n.getY(i))>.68;
    uv[2*i]=horizontal?p.getX(i)*120:p.getX(i)*80+p.getZ(i)*80;
    uv[2*i+1]=horizontal?p.getZ(i)*330:p.getY(i)*550;
  }
  geometry.setAttribute('uv',new T.BufferAttribute(uv,2));
}

export async function enclosureModel(expected,packed) {
  const scene=await readModel(packed);
  const finishes=new Map(),grain=printGrain();
  scene.traverse(mesh=>{
    if(!mesh.isMesh)return;
    const finish=mesh.name.split('__')[2];
    const printed=['shell','faceplate','graphite'].includes(finish);
    if(!finishes.has(finish)){
      const m=hardwareFinishes[finish]?material(...hardwareFinishes[finish]):
        material(surfaceColors[finish],finish==='screw'?.65:.05,printed?.65:.4);
      if(printed){m.bumpMap=grain;m.bumpScale=.038;}
      m.side=T.DoubleSide;finishes.set(finish,m);
    }
    if(printed)grainUV(mesh.geometry);
    mesh.material=finishes.get(finish);mesh.castShadow=mesh.receiveShadow=true;
  });
  scene.scale.setScalar(1000);scene.updateMatrixWorld(true);
  const box=new T.Box3().setFromObject(scene),size=box.getSize(vec()),center=box.getCenter(vec());
  if([size.x,size.z,size.y].some((n,i)=>Math.abs(n-expected[i])>.02))throw Error('CAD envelope and published dimensions disagree');
  scene.position.set(-center.x,-box.min.y,-center.z);
  const group=new T.Group();group.add(scene);return group;
}
