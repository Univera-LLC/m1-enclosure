import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {enclosureModel, macModel, referenceModel} from './models.js';
import {rulerGroup} from './rulers.js';

const directions={iso:[.28,.86,1.25],top:[0,1,.0001],front:[0,0,1],rear:[0,0,-1]};
const vec=(...p)=>new T.Vector3(...p);
export async function startOrbit({host,overlay,enclosure,mac,moved,unavailable}) {
  const packed=JSON.parse(document.getElementById('glbs').textContent);
  const [cad,oem]=await Promise.all([enclosureModel(enclosure.size,packed.enclosure),macModel(mac.size,packed.mac)]);
  const renderer=new T.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.7));
  renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFShadowMap;
  host.append(renderer.domElement);
  const world=new T.Scene(),camera=new T.OrthographicCamera(-100,100,100,-100,.1,2200);
  const controls=new OrbitControls(camera,renderer.domElement);
  controls.enablePan=false;controls.minZoom=.45;controls.maxZoom=4;controls.rotateSpeed=.75;
  const studio=new RoomEnvironment(),pmrem=new T.PMREMGenerator(renderer);
  world.environment=pmrem.fromScene(studio,.04).texture;world.environmentIntensity=.76;
  studio.dispose();pmrem.dispose();
  world.add(new T.HemisphereLight(0xf7fff9,0xa2a9a5,.72));
  const key=new T.DirectionalLight(0xfff5e8,2.05),rim=new T.DirectionalLight(0xe6f0ff,.78);
  key.position.set(-240,380,180);rim.position.set(160,170,-260);key.castShadow=true;
  Object.assign(key.shadow.camera,{left:-350,right:350,top:290,bottom:-290,far:1100});
  key.shadow.mapSize.set(1024,1024);key.shadow.normalBias=.25;key.shadow.bias=-.00014;
  world.add(key,rim);
  const desk=new T.Mesh(new T.PlaneGeometry(1500,1500).rotateX(-Math.PI/2),new T.ShadowMaterial({opacity:.20,depthWrite:false}));
  desk.position.y=-.24;desk.receiveShadow=true;world.add(desk);
  const grid=new T.GridHelper(800,40,0x9baca2,0x9baca2);
  grid.position.set(0,-.19,-110);grid.material.transparent=true;grid.material.opacity=.17;
  grid.material.depthWrite=false;world.add(grid);
  const models=new T.Group();
  world.add(models);
  const bounds=new T.Box3(),references=new Map();
  let rows=[],selected,frame=0,showRuler=true;

  function drawRulers(width,height) {
    if(!showRuler)return;
    overlay.setAttribute('viewBox','0 0 '+width+' '+height);
    const dir=camera.position.clone().sub(controls.target).normalize();
    const at=(x,y,z)=>{
      const p=vec(x,y,z).project(camera);
      return [(p.x+1)*width*.5,(1-p.y)*height*.5];
    };
    const plan=Math.abs(dir.y)>=.34, side=Math.abs(dir.x)>Math.abs(dir.z);
    overlay.innerHTML=rows.map(([{id,size:[w,d,h]},group])=>{
      const x=group.position.x,z=group.position.z;
      const near=z+(dir.z>=0?d/2:-d/2),far=2*z-near;
      const edge=x+(dir.x>=0?w/2:-w/2);
      const widthEdge=[[x-w/2,near],[x+w/2,near]],depthEdge=[[edge,near],[edge,far]];
      const floor=([a,b])=>at(a,0,b);
      const widthPoints=widthEdge.map(floor);
      if(widthPoints[0][0]>widthPoints[1][0])widthPoints.reverse();
      const widthRuler=['width',w,...widthPoints],depthRuler=['depth',d,...depthEdge.map(floor)];
      const flatEdge=side?depthEdge:widthEdge;
      const [u,v]=floor(flatEdge[0])[0]>floor(flatEdge[1])[0]?flatEdge[0]:flatEdge[1];
      const heightRuler=['height',h,at(u,0,v),at(u,h,v)];
      const segments=plan?[widthRuler,depthRuler]:[side?depthRuler:widthRuler,heightRuler];
      if(plan&&Math.min(w,d)<20&&Math.abs(dir.y)<.9)segments.push(heightRuler);
      return rulerGroup(id,at(x,h/2,z),segments);
    }).join('');
  }
  function render() {
    if(!frame)frame=requestAnimationFrame(()=>{
      frame=0;
      const width=host.clientWidth,height=host.clientHeight;
      if(width&&height){renderer.render(world,camera);drawRulers(width,height);}
    });
  }
  function projection() {
    const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;
    const center=controls.target,span=[0,0],inverse=camera.quaternion.clone().invert();
    for(const x of [bounds.min.x,bounds.max.x])for(const y of [bounds.min.y,bounds.max.y])for(const z of [bounds.min.z,bounds.max.z]){
      const v=vec(x,y,z).sub(center).applyQuaternion(inverse);
      span[0]=Math.max(span[0],Math.abs(v.x));span[1]=Math.max(span[1],Math.abs(v.y));
    }
    const a=w/h,half=Math.max(span[0]/a,span[1])*(w<520?1.2:1.16);
    Object.assign(camera,{left:-half*a,right:half*a,top:half,bottom:-half});
    camera.updateProjectionMatrix();renderer.setSize(w,h,false);render();
  }
  function fit(direction) {
    bounds.getCenter(controls.target);
    camera.position.copy(controls.target).addScaledVector(direction.normalize(),1100);
    camera.zoom=1;controls.update();projection();
  }
  function setReference(item) {
    selected=item;
    if(item&&!references.has(item.id))references.set(item.id,referenceModel(item,render));
    rows=[[enclosure,cad],[mac,oem],...(item?[[item,references.get(item.id)]]:[])];
    const gap=42,total=rows.reduce((sum,[info])=>sum+info.size[0],gap*(rows.length-1));
    let left=-total/2;models.clear();
    for(const [{size:[w,d]},group] of rows){
      group.position.set(left+w/2,0,-d/2);models.add(group);left+=w+gap;
    }
    bounds.setFromObject(models);
    const dir=camera.position.clone().sub(controls.target);
    fit(dir.lengthSq()?dir:vec(...directions.iso));
  }
  function zoom(factor) {
    camera.zoom=T.MathUtils.clamp(camera.zoom*factor,controls.minZoom,controls.maxZoom);
    camera.updateProjectionMatrix();controls.update();render();
  }
  controls.addEventListener('change',render);
  controls.addEventListener('start',moved);
  renderer.domElement.addEventListener('webglcontextlost',unavailable);
  new ResizeObserver(projection).observe(host);
  setReference(null);fit(vec(...directions.iso));
  return {
    setReference(item){if(item!==selected)setReference(item);},
    setRuler(visible){
      if(visible===showRuler)return;
      showRuler=visible;
      if(!visible)overlay.replaceChildren();
      render();
    },
    preset(angle){fit(vec(...directions[angle]));},
    show(){projection();},
    zoom,
    turn(dx,dy){
      moved();
      const spherical=new T.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
      spherical.theta+=dx;spherical.phi+=dy;spherical.makeSafe();
      camera.position.copy(vec().setFromSpherical(spherical)).add(controls.target);controls.update();render();
    },
    inspect:()=>({camera:camera.position.toArray(),zoom:camera.zoom,ruler:showRuler,
      objects:rows.map(([{id},group])=>{
        const b=new T.Box3().setFromObject(group,true),s=b.getSize(vec());
        return {id,size:[s.x,s.z,s.y],ground:b.min.y,front:b.max.z,left:b.min.x,right:b.max.x};
      })}),
  };
}
