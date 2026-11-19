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
if((engineering&&!process.argv[3])||(base&&!/^https?:\/\//.test(base)))throw Error('Usage: node browser.mjs [http(s)://host/path/ | --published | --posters [SITE OUT] | --engineering PATH]');
const engineeringDir=engineering?resolve(root,process.argv[3]):null;
const posterSite=posters&&process.argv[3]?resolve(root,process.argv[3]):null;
const candidateDir=engineeringDir||posterSite;
const candidate=candidateDir?JSON.parse(await readFile(join(candidateDir,'engineering-check.json'),'utf8')):null;
const revision=candidate?.revision||manifest.revision;
assert(['D2.6','D2.7'].includes(revision));
if(engineering)assert.equal(revision,manifest.revision,'The engineering preview must use the active release.');
const slug=revision.toLowerCase().replace('.','');
const posterOutput=resolve(root,process.argv[4]||join('build',slug+'-posters'));
const out=await mkdtemp(engineering?join(engineeringDir,'browser-check-'):join(tmpdir(),slug+(base?'-url-smoke-':'-local-smoke-')));
const geom=candidate?{sha256:candidate.model_sha256,port_fit:{ports:candidate.ports}}:JSON.parse(await readFile(join(here,'..',slug,'geometry-check.json'),'utf8'));
assert.deepEqual(geom.port_fit.ports.map(p=>p.id).sort(),['A1','A2','HDMI','PD','RJ','TB1','TB2','audio']);
if(candidate)assert.equal(Object.keys(candidate.download_sha256).length,14);
const hash=b=>createHash('sha256').update(b).digest('hex');
let url=posters?pathToFileURL(join(posterSite||join(root,'build',slug+'-draft'),'index.html')).href:base;
let server,browser;
const exact='?view=rear&spread=96&cam=0.8822%2C0.2619%2C0.3914%2C-7.5%2C56.76%2C23%2C1';
const edge='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

async function checkComparison(page, url) {
  await page.locator('#tabs .compare-tab').click();
  assert.equal(page.url(),new URL('compare/index.html',url).href);
  const stage=page.locator('#compare-stage[data-render="3d"]');
  await stage.waitFor();
  const inspect=()=>page.evaluate(()=>window.m1Comparison.inspect());
  const close=(a,b)=>Math.abs(a-b)<.02;
  const assets=join(here,'..','compare','assets');
  const embedded=JSON.parse(await page.locator('#glbs').textContent());
  assert.equal(hash(gunzipSync(Buffer.from(embedded.mac,'base64'))),
    hash(await readFile(join(assets,'mac-mini-datsketch.glb'))),'the credited Mac mini mesh is embedded');
  const benchmarks=JSON.parse(await page.locator('#compare-data').textContent()).objects;
  const photo=benchmarks.find(o=>o.id==='portrait').photo;
  assert.equal(hash(Buffer.from(photo.split(',')[1],'base64')),
    hash(await readFile(join(assets,'zelensky-a4.jpg'))),'the portrait photograph is embedded');
  assert.equal(await page.locator('.compare-credits a').count(),4);
  const orbitRulers=page.locator('#compare-orbit-rulers');
  const diagramRulers=page.locator('#compare-plots');
  const rulers=(scope,id)=>scope.locator('[data-rulers-for="'+id+'"] [data-ruler]')
    .evaluateAll(nodes=>Object.fromEntries(nodes.map(n=>[n.dataset.ruler,Number(n.dataset.lengthMm)])));
  const entry=await inspect();
  assert.deepEqual(entry.objects.map(o=>o.id),['enclosure','mac']);
  assert(entry.objects.every((o,i)=>o.size.every((n,j)=>close(n,[[170,119.91,46],[197,197,36]][i][j]))));
  assert(entry.objects.every(o=>close(o.ground,0)&&close(o.front,0)));
  assert(entry.objects[0].right<entry.objects[1].left,'both cases stand side by side');
  await orbitRulers.locator('[data-ruler="width"]').first().waitFor();
  assert.deepEqual(await rulers(orbitRulers,'enclosure'),{width:170,depth:119.91});
  assert.deepEqual(await rulers(orbitRulers,'mac'),{width:197,depth:197});
  assert(await orbitRulers.locator('[data-centimeters="10"]').count()>0);
  assert(await orbitRulers.locator('[data-interval-mm="1"] .ticks-0').count()>0);
  await page.screenshot({path:join(out,'comparison.png'),fullPage:true});

  const surface=stage.locator('canvas'),box=await surface.boundingBox();
  await page.mouse.move(box.x+box.width*.48,box.y+box.height*.43);
  await page.mouse.down();
  await page.mouse.move(box.x+box.width*.58,box.y+box.height*.60,{steps:7});
  await page.mouse.up();
  assert.notDeepEqual((await inspect()).camera,entry.camera,'drag orbits the shared camera');
  await page.locator('#compare-in').click();
  assert((await inspect()).zoom>entry.zoom);
  await stage.press('0');
  assert((await inspect()).camera.every((n,i)=>close(n,entry.camera[i])));
  await page.locator('[data-angle="rear"]').click();
  assert((await inspect()).camera[2]<0);
  await orbitRulers.locator('[data-rulers-for="enclosure"] [data-ruler="height"]').waitFor();
  assert.deepEqual(await rulers(orbitRulers,'enclosure'),{width:170,height:46});
  await stage.screenshot({path:join(out,'comparison-rear.png')});
  const ruler=page.locator('#compare-ruler');
  await ruler.click();assert.equal((await inspect()).ruler,false);
  assert.equal(await orbitRulers.locator('[data-ruler]').count(),0);
  await ruler.click();assert.equal((await inspect()).ruler,true);

  const objects=['aa','portrait','pixel','berserk','thrones','cola','nuc'];
  assert.equal(await page.locator('#compare-choices button').count(),objects.length+1);
  for(const id of objects){
    const choice=page.locator('[data-item="'+id+'"]');
    await choice.click();
    assert.equal(await choice.getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('#compare-orbit-name').textContent(),await choice.textContent());
    const rendered=(await inspect()).objects;
    assert.deepEqual(rendered.map(o=>o.id),['enclosure','mac',id]);
    const size=benchmarks.find(o=>o.id===id).size;
    assert(rendered.at(-1).size.every((n,i)=>close(n,size[i])),id+' matches its stated envelope');
  }
  await page.locator('[data-item="none"]').click();
  assert.equal((await inspect()).objects.length,2);
  await page.locator('[data-item="portrait"]').click();
  const portrait=(await inspect()).objects.at(-1);
  assert(portrait.size.every((n,i)=>close(n,[210,297,.3][i])),'the paper envelope is A4');
  await page.locator('[data-angle="top"]').click();
  await orbitRulers.locator('[data-rulers-for="portrait"] [data-ruler="depth"]').waitFor();
  assert.deepEqual(await rulers(orbitRulers,'portrait'),{width:210,depth:297});
  await page.locator('[data-mode="diagram"]').click();
  assert.equal(await page.locator('#compare-object-name').textContent(),'Портрет Зеленського · A4');
  const angles=page.locator('#compare-angles button:visible');
  assert.deepEqual(await angles.evaluateAll(buttons=>buttons.map(b=>b.dataset.angle)),['iso','top','front','side']);

  const plots=page.locator('[data-profile]');
  for(const [angle,expected] of Object.entries({
    top:[[170,119.91],[197,197]],front:[[170,46],[197,36]],side:[[119.91,46],[197,36]],
  })){
    await page.locator('[data-angle="'+angle+'"]').press('Enter');
    const boxes=await plots.evaluateAll(nodes=>nodes.map(node=>{const b=node.getBBox();return [b.width,b.height];}));
    assert(expected.every((dims,i)=>dims.every((n,j)=>Math.abs(n-boxes[i][j])<.02)),angle+' profile bounds');
  }
  await ruler.click();assert.equal(await diagramRulers.locator('[data-ruler]').count(),0);
  await ruler.click();assert.deepEqual(await rulers(diagramRulers,'mac'),{depth:197,height:36});

  const viewport=page.viewportSize();
  await page.setViewportSize({width:390,height:844});
  await page.locator('[data-angle="top"]').click();
  assert.deepEqual(await rulers(diagramRulers,'portrait'),{width:210,depth:297});
  const scales=await plots.evaluateAll(ns=>ns.map(n=>n.getScreenCTM().a));
  assert(Math.max(...scales)-Math.min(...scales)<.001,'panels use the same scale at mobile width');
  await page.locator('[data-mode="orbit"]').click();
  await page.locator('[data-angle="top"]').click();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth===document.documentElement.clientWidth),'comparison fits the viewport');
  await page.screenshot({path:join(out,'comparison-mobile.png'),fullPage:true});
  await page.setViewportSize(viewport);
  await page.locator('.compare-nav a[href="../index.html#stage"]').click();
  assert.equal(page.url(),new URL('index.html#stage',url).href);
  return {orbit:true,angles:4,objects:objects.length,reference_assets:['DatSketch GLB','President.gov.ua portrait'],
    portrait_mm:[210,297],ruler_minor_tick_mm:1,mobile_width:390};
}

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
  assert.equal(model_sha256,geom.sha256);assert.equal((await state()).revision,revision);
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
      await writeFile(join(posterOutput,key+'.webp'),frame);
    }finally{await style.evaluate(e=>e.remove());}
  }
  if(posters){
    await mkdir(posterOutput,{recursive:true});
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
    const archives=['D2.5'];
    let comparison;
    if(revision==='D2.7'){
      for(const [view,part] of [['base','chassis'],['power','saddle']]){
        await page.locator('#tabs [data-view="'+view+'"]').click();await painted();
        assert.equal((await state()).view,view);assert((await state()).visible.includes(part));
        await page.locator('#stage').screenshot({path:join(out,view+'.png')});
      }
      const image=await page.request.get(new URL('d27-mounts.webp',url).href);
      try{assert.equal(image.status(),200);assert.equal(hash(await image.body()),manifest.files['d27-mounts.webp'].sha256);}
      finally{await image.dispose();}
      if(!engineering)comparison=await checkComparison(page,url);
      await page.goto(url+'?rev=d2.6&view=rear');await ready();
      assert.equal((await state()).revision,'D2.6');assert(new URL(page.url()).pathname.endsWith('/d2.6/'));
      const old=JSON.parse(await readFile(join(root,'release/d2.6-manifest.json'),'utf8'));
      const oldLinks=await page.locator('#downloads a[download]').evaluateAll(links=>links.map(a=>a.getAttribute('href')));
      assert.equal(new Set(oldLinks).size,14);
      assert(oldLinks.every(h=>h.startsWith('../')&&old.files[h.slice(3)]));
      const href='downloads/d2.6/d2.6-first-fit.zip';
      const response=await page.request.get(new URL('../'+href,page.url()).href);
      try{assert.equal(response.status(),200);assert.equal(hash(await response.body()),old.files[href].sha256);}
      finally{await response.dispose();}
      archives.push('D2.6');
    }
    const previous=new URL('d2.5/?view=rear',url).href;await page.goto(previous);await ready();assert.equal((await state()).revision,'D2.5');
    const archivedFiles=await page.locator('#downloads a[download]').evaluateAll(links=>links.map(a=>a.getAttribute('href')));
    const archivedPrefix=new URL('downloads/d2.5/','https://dvaderfun.github.io/mac-mini-m1-case-prototype/').href;
    assert.equal(new Set(archivedFiles.filter(h=>h.startsWith('../downloads/d2.5/')||h.startsWith(archivedPrefix))).size,12);
    assert.deepEqual(errors,[]);
    await writeFile(join(out,'browser.json'),JSON.stringify({scope:engineering?'engineering':base?'url':published?'published':'candidate',revision,url:url+exact,model_sha256,view:entry.view,spread:entry.spread,pose:entry.pose,mesh_probes:probes.length,comparison,archives,downloads:hrefs,errors},null,2)+'\n');
  }
  const comparisonNote=revision==='D2.7'&&!engineering?', size comparison':'';
  assert.deepEqual(errors,[]);console.log(posters?'Rendered 19 '+revision+' fallback views: '+posterOutput:'Verified '+revision+' camera, exploded panel, 16 mesh probes, 14 downloads'+comparisonNote+' and archives. Receipt: '+join(out,'browser.json'));
}finally{await browser?.close();if(server)server.close();}

