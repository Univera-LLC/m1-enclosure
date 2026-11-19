import {chromium} from 'playwright';
import {existsSync} from 'node:fs';
import {mkdir,mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {viewKeys,portViews} from './catalog.js';
import {manifest,root,startPreview} from './preview.mjs';
const here=dirname(fileURLToPath(import.meta.url));
const arg=process.argv[2],posters=arg==='--posters',published=arg==='--published',engineering=arg==='--engineering';
const base=posters||published||engineering?undefined:arg;
if((engineering&&!process.argv[3])||(base&&!/^https?:\/\//.test(base)))throw Error('Usage: node browser.mjs [http(s)://host/path/ | --published | --posters | --engineering PATH]');
const engineeringDir=engineering?resolve(root,process.argv[3]):null;
const candidate=engineering?JSON.parse(await readFile(join(engineeringDir,'engineering-check.json'),'utf8')):null;
if(candidate)assert.equal(candidate.revision,'D2.6');
const out=await mkdtemp(engineering?join(engineeringDir,'browser-check-'):join(tmpdir(),base&&!posters?'d26-url-smoke-':'d26-local-smoke-'));
assert.equal(manifest.revision,'D2.6','This viewer checks the D2.6 release.');
const geom=candidate?{sha256:candidate.model_sha256,port_fit:{ports:candidate.ports}}:JSON.parse(await readFile(join(here,'geometry-check.json'),'utf8'));
assert.deepEqual(geom.port_fit.ports.map(p=>p.id).sort(),['A1','A2','HDMI','PD','RJ','TB1','TB2','audio']);
if(candidate)assert.equal(Object.keys(candidate.download_sha256).length,14);
const hash=b=>createHash('sha256').update(b).digest('hex');
let url=posters?pathToFileURL(join(root,'build/d26-draft/index.html')).href:base;
let server,browser;
const exact='?view=rear&spread=96&cam=0.8822%2C0.2619%2C0.3914%2C-7.5%2C56.76%2C23%2C1';
const edge='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
try{
  if(!url){
    ({server,url}=await startPreview(0,false,!published&&!engineering,engineeringDir));
  }
  browser=await chromium.launch({...(existsSync(edge)?{executablePath:edge}:{}),args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-gpu-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:960},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(!base&&!posters)await page.route(/^https?:\/\//,r=>{
    if(new URL(r.request().url()).origin===new URL(url).origin)return r.continue();
    errors.push('Unexpected external request: '+r.request().url());return r.abort();
  });
  await page.goto(url+(posters?'':exact),{waitUntil:'domcontentloaded'});
  const ready=()=>page.waitForFunction(()=>document.documentElement.dataset.render==='3d');
  const state=()=>page.evaluate(()=>window.m1Atlas.inspect());
  const painted=()=>page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  await ready();await painted();
  const model_sha256=hash(gunzipSync(Buffer.from(await page.locator('#model-bytes').textContent(),'base64')));
  assert.equal(model_sha256,geom.sha256);assert.equal((await state()).revision,'D2.6');
  async function capture(key){
    await painted();
    const style=await page.addStyleTag({content:'#pins,#leaders,.stage-head,.stage-foot,#poster{visibility:hidden!important}#stage:focus{outline:none!important;box-shadow:none!important}'});
    try{
      const png=await page.locator('#stage').screenshot({animations:'disabled'});
      const encoded=await page.evaluate(async(data)=>{
        const bm=await createImageBitmap(await (await fetch('data:image/png;base64,'+data)).blob());
        const c=document.createElement('canvas');c.width=bm.width;c.height=bm.height;c.getContext('2d').drawImage(bm,0,0);bm.close();
        return c.toDataURL('image/webp',.87).split(',')[1];
      },png.toString('base64'));
      const frame=Buffer.from(encoded,'base64');assert(frame.length>2000,key);
      await writeFile(join(root,'build/d26-posters',key+'.webp'),frame);
    }finally{await style.evaluate(e=>e.remove());}
  }
  if(posters){
    await mkdir(join(root,'build/d26-posters'),{recursive:true});
    for(const view of viewKeys){
      await page.locator('#tabs [data-view="'+view+'"]').click();assert.equal((await state()).view,view);
      await capture(view);
      if(view==='board'){await page.locator('#side-back').click();await capture('board-back');await page.locator('#side-top').click();}
      if(view==='rear'){
        for(const kind of Object.keys(portViews).filter(k=>k!=='all')){
          await page.locator('#port-tools [data-port="'+kind+'"]').click();await capture('rear-'+kind);
        }
        await page.locator('#port-tools [data-port="all"]').click();
        for(const [value,id] of [[36,'rear-lid'],[71,'rear-feed'],[74,'rear-clear'],[100,'rear-open']]){
          await page.locator('#spread').fill(String(value));await capture(id);
        }
        await page.goto(url+'?view=rear&part=panel&solo=1&side=back');
        await ready();assert.deepEqual((await state()).visible,['panel']);await capture('panel-back');
      }
    }
  }else{
    const entry=await state(),pose=entry.pose.split(',').map(Number),want=[.8822,.2619,.3914,-7.5,56.76,23,1];
    assert.equal(entry.view,'rear');assert.equal(entry.spread,96);assert(pose.length===7&&pose.every((v,i)=>Math.abs(v-want[i])<.001));assert(entry.positions.panel[2]>20);
    await page.locator('#stage').screenshot({path:join(out,'rear-96.png')});
    await page.locator('#service-tools [data-state="0"]').click();await painted();
    const probes=geom.port_fit.ports.flatMap(p=>['masked_bezel','open_to_back'].map(role=>({id:p.id,role,...p.probes[role]})));
    const hits=await page.evaluate(rows=>rows.map(p=>window.m1Atlas.frontProbe(...p.xz_mm).hit),probes);
    for(const [i,p] of probes.entries()){
      const h=hits[i];assert.equal([h.layer,h.group,h.finish,h.source].join('__'),p.first_mesh,p.id+' '+p.role);assert(Math.abs(h.y_mm-p.y_mm)<.018,p.id);
    }
    const hrefs=await page.locator('#downloads a[download]').evaluateAll(a=>a.map(n=>n.getAttribute('href')));
    assert(hrefs.filter(f=>f.endsWith('.stl')).length===8&&hrefs.filter(f=>f.endsWith('.step')).length===2&&hrefs.filter(f=>f.endsWith('.zip')).length===2&&hrefs.some(f=>f.endsWith('.sc')));
    assert.equal(new Set(hrefs).size,14);
    for(const href of hrefs){
      const response=await page.request.get(new URL(href,url).href);
      try{assert.equal(response.status(),200,href);assert.equal(hash(await response.body()),candidate?candidate.download_sha256[href]:manifest.files[href]?.sha256,href);}
      finally{await response.dispose();}
    }
    await page.locator('#to-panel-back').click();await ready();assert.deepEqual((await state()).visible,['panel']);assert.equal((await state()).side,'back');
    await page.locator('#stage').screenshot({path:join(out,'panel-back.png')});
    const previous=new URL('d2.5/?view=rear',url).href;await page.goto(previous);await ready();assert.equal((await state()).revision,'D2.5');
    const archivedFiles=await page.locator('#downloads a[download]').evaluateAll(links=>links.map(a=>a.getAttribute('href')));
    const archivedPrefix=new URL('downloads/d2.5/',manifest.target).href;
    assert.equal(new Set(archivedFiles.filter(h=>h.startsWith('../downloads/d2.5/')||h.startsWith(archivedPrefix))).size,12);
    assert.deepEqual(errors,[]);
    await writeFile(join(out,'browser.json'),JSON.stringify({scope:engineering?'engineering':base?'url':published?'published':'candidate',url:url+exact,published_baseline:manifest.pages_commit,model_sha256,view:entry.view,spread:entry.spread,pose:entry.pose,mesh_probes:probes.length,archive:'D2.5',downloads:hrefs,errors},null,2)+'\n');
  }
  assert.deepEqual(errors,[]);console.log(posters?'Rendered 19 D2.6 fallback views.':'Verified camera, exploded panel, 16 mesh probes, inside view, 14 downloaded files and D2.5 archive. Receipt: '+join(out,'browser.json'));
}finally{await browser?.close();if(server)server.close();}

