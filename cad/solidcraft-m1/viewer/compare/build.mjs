import {readFile} from 'node:fs/promises';
import {gzipSync,gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';

function pack(glb) {
  const compressed=gzipSync(glb,{level:9});
  compressed[9]=255;
  return compressed.toString('base64');
}

// Keep the shell and the hardware visible through it from the verified atlas GLB.
// The subset retains original coordinates, normals and triangle indices.
function enclosureGlb(atlas) {
  const packed=atlas.match(/<script id="model-bytes" type="application\/octet-stream">([A-Za-z0-9+/=]+)<\/script>/);
  if(!packed)throw Error('No assembly in the released atlas');
  const glb=gunzipSync(Buffer.from(packed[1],'base64'));
  const jsonBytes=glb.readUInt32LE(12);
  const assembly=JSON.parse(glb.subarray(20,20+jsonBytes));
  const bin=glb.subarray(28+jsonBytes);
  const parts=new Set(['chassis','lid','blank','panel','feet','lidscrews']);
  const chunks=[], accessors=[], bufferViews=[], nodes=[], meshes=[];
  let size=0;
  function copyAccessor(index) {
    const accessor=assembly.accessors[index], view=assembly.bufferViews[accessor.bufferView];
    if(view.buffer!==0||accessor.sparse)throw Error('Unsupported accessor in enclosure GLB');
    const start=view.byteOffset||0;
    chunks.push(bin.subarray(start,start+view.byteLength),Buffer.alloc((4-view.byteLength%4)%4));
    bufferViews.push({...view,byteOffset:size});
    size+=view.byteLength+(4-view.byteLength%4)%4;
    accessors.push({...accessor,bufferView:bufferViews.length-1});
    return accessors.length-1;
  }
  const copied=new Set();
  for(const node of assembly.nodes){
    const [layer,part]=node.name.split('__');
    const shell=layer==='d2'&&parts.has(part);
    if(!shell&&!(layer==='oem'&&part==='ports'||layer==='d2'&&part==='socket'||layer==='photo'&&part==='sink'))continue;
    if(shell)copied.add(part);
    nodes.push({...node,mesh:meshes.length});
    const mesh=assembly.meshes[node.mesh];
    meshes.push({...mesh,primitives:mesh.primitives.map(p=>({
      mode:p.mode,indices:copyAccessor(p.indices),
      attributes:Object.fromEntries(Object.entries(p.attributes).map(([kind,i])=>[kind,copyAccessor(i)])),
    }))});
  }
  if(copied.size!==parts.size)throw Error('Missing exterior parts in the released atlas');
  const scene={asset:assembly.asset,scene:0,scenes:[{nodes:nodes.map((_,i)=>i)}],
    nodes,meshes,accessors,bufferViews,buffers:[{byteLength:size}]};
  const json=Buffer.from(JSON.stringify(scene)), padded=Buffer.concat([json,Buffer.alloc((4-json.length%4)%4,32)]);
  const header=Buffer.alloc(20), binHeader=Buffer.alloc(8);
  header.write('glTF');header.writeUInt32LE(2,4);header.writeUInt32LE(28+padded.length+size,8);
  header.writeUInt32LE(padded.length,12);header.write('JSON',16);
  binHeader.writeUInt32LE(size);binHeader.writeUInt32LE(0x004e4942,4);
  return pack(Buffer.concat([header,padded,binHeader,...chunks]));
}

const [atlas,mac,bundle]=await Promise.all([
  readFile(process.argv[2],'utf8'),
  readFile(new URL('./assets/mac-mini-datsketch.glb',import.meta.url)),
  build({entryPoints:[fileURLToPath(new URL('./scene.js',import.meta.url))],bundle:true,write:false,
    format:'iife',target:['es2020'],minify:true,legalComments:'inline'}),
]);
process.stdout.write(JSON.stringify({
  models:{enclosure:enclosureGlb(atlas),mac:pack(mac)},
  script:bundle.outputFiles[0].text.replace(/<\/script/gi,'<\\/script'),
}));
