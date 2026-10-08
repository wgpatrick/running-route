const fs=require('fs'), zlib=require('zlib');
const Lib=require('../app/router.js')();
const b64=fs.readFileSync(__dirname+'/data/blob.b64','utf8');
const buf=zlib.gunzipSync(Buffer.from(b64,'base64'));
let t=Date.now(); const g=Lib.decode(buf.buffer.slice(buf.byteOffset,buf.byteOffset+buf.length)); console.log('decode ms',Date.now()-t, g.nN, g.nE);
const home={lat:37.73870,lon:-122.41984,label:'339 Elsie St'};
for (const q of ['339 Elsie St','24th St & Mission St','Cortland and Mission','1 Ferry Building','Twin Peaks','2000 Fulton St','500 Valencia Street','Haight & Ashbury','37.76,-122.45','Dolores Park']) console.log(q,'=>',JSON.stringify(Lib.geocode(g,q,home)));
const mi=1609.344;
const P = (o)=>Object.assign({start:home,targetM:null,hill:'rolling'},o);
const fmt=(r)=>`${(r.length/mi).toFixed(2)}mi gain ${(r.gain*3.281).toFixed(0)}ft maxUp ${(r.maxUp*100).toFixed(1)}% ovl ${(r.overlap*100).toFixed(0)}% steps ${r.steps} score ${r.score.toFixed(2)} | ${r.passed.map(p=>p.name).join(', ')} | climbs ${r.climbs.map(c=>c.street+' '+(c.gain*3.28|0)+'ft').join('; ')}`;
const tw=g.places.find(p=>p.name==='Twin Peaks');
for (const [name,p] of [
 ['7mi rolling loop',P({targetM:7*mi})],
 ['5mi flat',P({targetM:5*mi,hill:'flat'})],
 ['6mi hilly',P({targetM:6*mi,hill:'hilly'})],
 ['7mi via Twin Peaks',P({targetM:7*mi,destinations:[tw]})],
 ['to twin peaks no target',P({destinations:[tw]})],
 ['10mi fast',P({targetM:10*mi,hill:'flat',fast:true})],
 ['4mi out-back',P({targetM:4*mi,shape:'out-and-back'})],
 ['p2p to Ferry 6mi',P({targetM:6*mi,end:{lat:37.7955,lon:-122.3937}})],
]) { t=Date.now(); const res=Lib.plan(g,p); console.log('\n##',name, res.ms+'ms', res.routes.length,'routes'); for(const r of res.routes) console.log('  ',fmt(r), '| est', (Lib.estimateSeconds(r,510)/60).toFixed(1),'min'); }
