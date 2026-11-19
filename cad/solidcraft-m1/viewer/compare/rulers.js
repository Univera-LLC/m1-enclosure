const xy=p=>p.map(n=>Number(n.toFixed(2))).join(' ');
const point=(a,b,n)=>[a[0]+b[0]*n,a[1]+b[1]*n];
const move=(a,b)=>'M'+xy(a)+'L'+xy(b);

// Endpoints are the object's real envelope in millimetres, projected into the view.
export function edgeRuler({a,b,outside,length,axis,scale=1}) {
  const dx=b[0]-a[0],dy=b[1]-a[1],screen=Math.hypot(dx,dy);
  if(screen*scale<6)return '';
  const unit=[dx/length,dy/length];
  const normal=[-dy/screen,dx/screen];
  if(normal[0]*outside[0]+normal[1]*outside[1]<0)normal.forEach((n,i)=>{normal[i]=-n;});
  const start=point(a,normal,7/scale),end=point(b,normal,7/scale);
  const pxPerMm=screen*scale/length;
  const labelStep=[10,20,50,100].find(n=>n*pxPerMm>=27)||100;
  const paths=['','',''];
  let labels='';
  for(let n=0;n<=length+.001;n++){
    const major=n%10===0, middle=n%5===0, label=n%labelStep===0;
    const mark=point(start,unit,n);
    paths[major?2:middle?1:0]+=move(mark,point(mark,normal,(major?7:middle?4.5:2.6)/scale));
    if(label && screen*scale>=17){
      const p=point(mark,normal,14/scale);
      labels+='<text class="scale-label" data-centimeters="'+n/10+'" x="'+p[0]+'" y="'+p[1]+
        '" font-size="'+10.5/scale+'" style="stroke-width:'+2.8/scale+'">'+n/10+'</text>';
    }
  }
  return '<g class="edge-ruler" data-ruler="'+axis+'" data-length-mm="'+length+'" data-interval-mm="1">'+
    '<path class="ruler-leader" d="'+move(a,point(start,normal,2/scale))+move(b,point(end,normal,2/scale))+
      '" stroke-width="'+.75/scale+'"/>'+
    '<path class="ruler-line" d="'+move(start,end)+'" stroke-width="'+1.15/scale+'"/>'+
    paths.map((d,i)=>d?'<path class="ruler-ticks ticks-'+i+'" d="'+d+'" stroke-width="'+(.62+i*.2)/scale+'"/>':'').join('')+
    labels+'</g>';
}

export function rulerGroup(id,center,segments,scale=1) {
  return '<g data-rulers-for="'+id+'">'+segments.map(([axis,length,a,b])=>{
    const outside=[(a[0]+b[0])*.5-center[0],(a[1]+b[1])*.5-center[1]];
    return edgeRuler({a,b,outside,length,axis,scale});
  }).join('')+'</g>';
}
