"""Build a compact walkable street graph of SF with elevation, for the in-browser router."""
import pyarrow.parquet as pq, numpy as np, shapely, math, json, collections, gzip, base64, struct
seg = pq.read_table('data/segments.parquet').to_pandas()
D = np.load('data/dem.npz'); dem = D['dem']; Z=int(D['z']); X0=int(D['x0']); Y0=int(D['y0'])
def elev(lon, lat):
    n=2**Z
    px=((lon+180)/360*n - X0)*256 - .5
    r=np.radians(lat); py=((1-np.log(np.tan(r)+1/np.cos(r))/np.pi)/2*n - Y0)*256 - .5
    x0=np.floor(px).astype(int); y0=np.floor(py).astype(int); fx=px-x0; fy=py-y0
    g=lambda y,x: dem[np.clip(y,0,dem.shape[0]-1), np.clip(x,0,dem.shape[1]-1)]
    return (g(y0,x0)*(1-fx)*(1-fy)+g(y0,x0+1)*fx*(1-fy)+g(y0+1,x0)*(1-fx)*fy+g(y0+1,x0+1)*fx*fy)
KEEP = {'footway','cycleway','living_street','path','pedestrian','primary','secondary','tertiary',
        'residential','unclassified','service','steps','track','trunk','bridleway'}
CLASSES = ['residential','tertiary','secondary','primary','trunk','service','footway','sidewalk','crosswalk','path','steps','cycleway','pedestrian','track','living_street','unclassified','bridleway']
M_LAT = 111320.0; M_LON = 111320.0*math.cos(math.radians(37.76))
def dist(a,b): return math.hypot((a[0]-b[0])*M_LON,(a[1]-b[1])*M_LAT)

conn_xy = {}; raw_edges = []
for r in seg.itertuples():
    c = r.__getattribute__('_2') if False else r[2]
    cls = r[2]; sub = r[3] if isinstance(r[3],str) else None
    if cls not in KEEP: continue
    if sub in ('link','driveway','parking_aisle','cycle_crossing') : continue
    flags=set()
    if r.road_flags is not None:
        for f in r.road_flags: flags.update(f['values'])
    if flags & {'is_indoor','is_under_construction','is_abandoned','is_link'}: continue
    denied=False
    if r.access_restrictions is not None:
        for a in r.access_restrictions:
            w=a['when'] or {}; modes=w.get('mode'); 
            if a['access_type']=='denied' and a['between'] is None:
                if modes is None and w.get('vehicle') is None and w.get('using') is None: denied=True
                elif modes is not None and 'foot' in list(modes): denied=True
    if denied: continue
    if cls=='footway' and sub in ('sidewalk','crosswalk'): cls=sub
    name = r.names['primary'] if r.names is not None and r.names.get('primary') else ''
    g = shapely.from_wkb(r.geometry); coords=list(g.coords)
    # cumulative length to split at connectors
    cum=[0.0]
    for i in range(1,len(coords)): cum.append(cum[-1]+dist(coords[i-1],coords[i]))
    L=cum[-1]
    if L<=0: continue
    cs=sorted([(float(c['at']),c['connector_id']) for c in r.connectors])
    bridge = bool(flags & {'is_bridge','is_tunnel'})
    def point_at(d):
        for i in range(1,len(coords)):
            if cum[i]>=d:
                t=(d-cum[i-1])/max(cum[i]-cum[i-1],1e-9)
                return (coords[i-1][0]+t*(coords[i][0]-coords[i-1][0]), coords[i-1][1]+t*(coords[i][1]-coords[i-1][1]))
        return coords[-1]
    for (a,ca),(b,cb) in zip(cs,cs[1:]):
        da,db=a*L,b*L
        if db-da<0.5: continue
        pts=[point_at(da)]+[coords[i] for i in range(len(coords)) if da<cum[i]<db]+[point_at(db)]
        conn_xy.setdefault(ca,pts[0]); conn_xy.setdefault(cb,pts[-1])
        raw_edges.append([ca,cb,cls,name,pts,bridge])
print('raw edges',len(raw_edges))
# largest connected component
adj=collections.defaultdict(list)
for i,e in enumerate(raw_edges): adj[e[0]].append(e[1]); adj[e[1]].append(e[0])
seen={}; best=None
for s in adj:
    if s in seen: continue
    comp=[s]; seen[s]=s; st=[s]
    while st:
        x=st.pop()
        for y in adj[x]:
            if y not in seen: seen[y]=s; st.append(y); comp.append(y)
    if best is None or len(comp)>len(best[1]): best=(s,comp)
root=best[0]
edges=[e for e in raw_edges if seen[e[0]]==root]
print('component edges',len(edges),'nodes',len(best[1]))
# contract degree-2 nodes where attributes match
deg=collections.Counter()
for e in edges: deg[e[0]]+=1; deg[e[1]]+=1
inc=collections.defaultdict(list)
for i,e in enumerate(edges): inc[e[0]].append(i); inc[e[1]].append(i)
alive=[True]*len(edges)
def oriented(e,start):
    return e[4] if e[0]==start else e[4][::-1]
for n in list(inc):
    if deg[n]!=2: continue
    ids=[i for i in inc[n] if alive[i]]
    if len(ids)!=2 or ids[0]==ids[1]: continue
    a,b=edges[ids[0]],edges[ids[1]]
    if (a[2],a[3],a[5])!=(b[2],b[3],b[5]): continue
    ua = a[0] if a[1]==n else a[1]; vb = b[1] if b[0]==n else b[0]
    if ua==vb: continue
    pts = oriented(a,ua)+oriented(b,n)[1:]
    new=[ua,vb,a[2],a[3],pts,a[5]]
    alive[ids[0]]=alive[ids[1]]=False
    edges.append(new); alive.append(True); k=len(edges)-1
    for x in (ua,vb):
        inc[x]=[i for i in inc[x] if i not in ids]+[k]
    inc[n]=[]
edges=[e for i,e in enumerate(edges) if alive[i]]
nodes={}
for e in edges:
    for c in (e[0],e[1]): nodes.setdefault(c,len(nodes))
print('contracted edges',len(edges),'nodes',len(nodes))
node_ll=np.zeros((len(nodes),2))
for c,i in nodes.items(): node_ll[i]=conn_xy[c]
node_el=elev(node_ll[:,0],node_ll[:,1])
# per-edge densified geometry with elevation
names=['']; name_ix={'':0}
E_u=[];E_v=[];E_len=[];E_cls=[];E_name=[];E_off=[];E_n=[];E_up=[];E_dn=[]
G=[]  # flat list of int16 triples (dlon,dlat,delev)
tot_len=0
for e in edges:
    pts=e[4]
    dense=[pts[0]]
    for p,q in zip(pts,pts[1:]):
        d=dist(p,q); k=max(1,int(math.ceil(d/15)))
        for j in range(1,k+1): dense.append((p[0]+(q[0]-p[0])*j/k, p[1]+(q[1]-p[1])*j/k))
    arr=np.array(dense)
    el=elev(arr[:,0],arr[:,1]).astype(float)
    if e[5]:  # bridge/tunnel: straight line between ends
        el=np.linspace(el[0],el[-1],len(el))
    elif len(el)>4:  # light smoothing of DEM noise
        k=np.array([1,2,3,2,1],float); k/=k.sum()
        sm=np.convolve(np.pad(el,2,mode='edge'),k,mode='valid'); sm[0]=el[0]; sm[-1]=el[-1]; el=sm
    seglen=[dist(dense[i],dense[i+1]) for i in range(len(dense)-1)]
    L=sum(seglen); tot_len+=L
    de=np.diff(el); up=float(de[de>0].sum()); dn=float(-de[de<0].sum())
    u=nodes[e[0]]; v=nodes[e[1]]
    # enforce node elevation consistency at endpoints
    if e[3] not in name_ix: name_ix[e[3]]=len(names); names.append(e[3])
    E_u.append(u);E_v.append(v);E_len.append(round(L*10));E_cls.append(CLASSES.index(e[2]));E_name.append(name_ix[e[3]])
    E_up.append(round(up*10)); E_dn.append(round(dn*10))
    E_off.append(len(G)//3); E_n.append(len(dense))
    # interior + end vertices as deltas from previous (start = node u); elev in decimeters
    prev=(round(dense[0][0]*1e5),round(dense[0][1]*1e5),round(el[0]*10))
    for (x,y),z in zip(dense[1:],el[1:]):
        cur=(round(x*1e5),round(y*1e5),round(z*10))
        G.extend([cur[0]-prev[0],cur[1]-prev[1],cur[2]-prev[2]]); prev=cur
print('total km',round(tot_len/1000),'geom verts',len(G)//3, 'names',len(names))
G=np.array(G); assert np.abs(G).max()<32767, np.abs(G).max()
def b64(a,dt): return base64.b64encode(np.asarray(a,dtype=dt).tobytes()).decode()
nl=np.round(node_ll*1e5).astype(np.int32)
blob={
 'classes':CLASSES,'names':names,
 'nodeLon':b64(nl[:,0],'<i4'),'nodeLat':b64(nl[:,1],'<i4'),'nodeEl':b64(np.round(node_el*10),'<i2'),
 'eU':b64(E_u,'<i4'),'eV':b64(E_v,'<i4'),'eLen':b64(E_len,'<u4'),'eCls':b64(E_cls,'<u1'),'eName':b64(E_name,'<u2'),
 'eUp':b64(E_up,'<u2'),'eDn':b64(E_dn,'<u2'),'eOff':b64(E_off,'<u4'),'eN':b64(E_n,'<u2'),'geom':b64(G,'<i2'),
}
json.dump(blob,open('data/graph.json','w'))
raw=open('data/graph.json','rb').read()
print('graph json MB',len(raw)/1e6,'gz MB',len(gzip.compress(raw,9))/1e6)
