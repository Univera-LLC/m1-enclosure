import {execFileSync} from 'node:child_process';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const here=dirname(fileURLToPath(import.meta.url));
export const root=resolve(here,'../../../..');
const project=JSON.parse(await readFile(join(root,'project.json'),'utf8'));
export const manifest=JSON.parse(await readFile(join(root,project.published_manifest),'utf8'));
const files={...manifest.files,...manifest.companion_files};
const types={html:'text/html; charset=utf-8',md:'text/plain; charset=utf-8',txt:'text/plain; charset=utf-8',
  json:'application/json',svg:'image/svg+xml',jpg:'image/jpeg',webp:'image/webp',glb:'model/gltf-binary',zip:'application/zip'};

export async function startPreview(port=0, onlineArchives=false, buildCandidate=true, engineeringDir=null){
  // Serve verified paths only. No CAD tree, unrelated workspace files or .git directory are exposed.
  execFileSync(process.env.PYTHON || (process.platform==='win32'?'python':'python3'),
    [join(root,'tools/verify_release.py')],{stdio:'inherit'});
  const candidate=engineeringDir||join(root,'build/d26-viewer');
  if(buildCandidate)execFileSync(process.execPath,[join(here,'build.mjs')],{stdio:'inherit'});
  const server=createServer(async(req,res)=>{
    if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);res.end();return;}
    const url=new URL(req.url,'http://localhost');
    let route=url.pathname.slice(1);
    if(!route||route.endsWith('/'))route+='index.html';
    if(!Object.hasOwn(files,route)){
      if(onlineArchives && /^(?:(?:d1|d2(?:\.[1-4])?|h1)\/|downloads\/d2\.[1-5]\/|reference\/(?:d2\.[1-5]\/|mac-board-reference\.glb$))/.test(route)){
        res.writeHead(302,{'Location':new URL(route+url.search,manifest.target).href});res.end();return;
      }
      res.writeHead(404);res.end();return;
    }
    try{
      // Only overlay generated D2.6 files; the old viewer and accessory evidence stay immutable.
      const overlay=(buildCandidate||engineeringDir)&&Object.hasOwn(manifest.files,route)&&
        (route==='index.html'||/^downloads\/d2\.6\/.+\.(?:stl|step|sc|zip)$/.test(route)||route.startsWith('reference/d2.6/')||
         (engineeringDir&&route.startsWith('downloads/d2.6/'))||/^d2(?:6-|5-vs-d26-).+\.(jpg|svg)$/.test(route));
      const data=await readFile(overlay?join(candidate,route):join(root,files[route].source));
      res.writeHead(200,{'Content-Type':types[route.split('.').pop()]||'application/octet-stream','Content-Length':data.length});
      res.end(req.method==='HEAD'?undefined:data);
    }catch{res.writeHead(500);res.end();}
  });
  await new Promise((done,fail)=>{server.once('error',fail);server.listen(port,'127.0.0.1',done);});
  return {server,url:'http://127.0.0.1:'+server.address().port+'/'};
}

if(process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const args=process.argv.slice(2);
  const port=args.length===0?8000:Number(args[1]);
  if((args.length!==0&&(args.length!==2||args[0]!=='--port'))||!Number.isInteger(port)||port<1||port>65535)
    throw Error('Usage: node preview.mjs [--port 1..65535]');
  const {url}=await startPreview(port,true);console.log('D2.6 preview: '+url+' (Ctrl+C to stop)');
}
