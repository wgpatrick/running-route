"""Pack graph + addresses + places into one gzipped binary blob (base64) and render the terrain image."""
import json, base64, gzip, struct, numpy as np, math, io
from PIL import Image, ImageFilter
g=json.load(open('data/graph.json')); addr=json.load(open('data/addr.json')); places=json.load(open('data/places.json'))
DT={'nodeLon':'i4','nodeLat':'i4','nodeEl':'i2','eU':'i4','eV':'i4','eLen':'u4','eCls':'u1','eName':'u2','eUp':'u2','eDn':'u2','eOff':'u4','eN':'u2','geom':'i2'}
fields=[]; body=b''
for k,dt in DT.items():
    raw=base64.b64decode(g[k])
    while len(body)%4: body+=b'\0'
    fields.append({'k':k,'dt':dt,'off':len(body),'len':len(raw)}); body+=raw
header=json.dumps({'classes':g['classes'],'names':g['names'],'fields':fields,'addr':addr,'places':places},separators=(',',':')).encode()
pad=(4-(len(header)+4)%4)%4; header+=b' '*pad
blob=struct.pack('<I',len(header))+header+body
gz=gzip.compress(blob,9); b64=base64.b64encode(gz).decode()
open('data/blob.b64','w').write(b64); print('blob raw MB',len(blob)/1e6,'b64 MB',len(b64)/1e6)

# terrain image: R = hillshade, G = elevation (0..300m -> 0..255), B = water(255)/contour(140)
D=np.load('data/dem.npz'); dem=D['dem'].astype(np.float64); Z=int(D['z']); X0=int(D['x0']); Y0=int(D['y0'])
F=3
h,w=dem.shape; dem=dem[:h//F*F,:w//F*F].reshape(h//F,F,w//F,F).mean(axis=(1,3))
H,W=dem.shape
lat_c=37.76; px_m=40075016.686*math.cos(math.radians(lat_c))/(2**Z*256)*F
gy,gx=np.gradient(dem,px_m)
slope=np.arctan(np.hypot(gx,gy)*1.6); aspect=np.arctan2(-gx,gy)
az=math.radians(315); alt=math.radians(45)
hs=np.sin(alt)*np.cos(slope)+np.cos(alt)*np.sin(slope)*np.cos(az-aspect)
hs=np.clip(hs,0,1)
water=dem< 0.5
el=np.clip(dem,0,300)/300*255
sm=dem.copy()
for _ in range(2):
    p=np.pad(sm,1,mode='edge'); sm=sum(p[1+dy:1+dy+H,1+dx:1+dx+W] for dy in (-1,0,1) for dx in (-1,0,1))/9
band=np.floor(np.maximum(sm,0)/20)  # 20 m contours
edge=np.zeros_like(band,bool); edge[:-1,:]|=band[:-1,:]!=band[1:,:]; edge[:,:-1]|=band[:,:-1]!=band[:,1:]
b=np.where(water,255,np.where(edge&(sm>2),140,0))
img=np.dstack([hs*255,el,b]).astype(np.uint8)
buf=io.BytesIO(); Image.fromarray(img).save(buf,'PNG',optimize=True)
n=2**Z
def lon(x): return x/n*360-180
def lat(y): return math.degrees(math.atan(math.sinh(math.pi*(1-2*y/n))))
bounds=[[lat(Y0+H*F/256),lon(X0)],[lat(Y0),lon(X0+W*F/256)]]
json.dump({'png':base64.b64encode(buf.getvalue()).decode(),'bounds':bounds,'w':W,'h':H},open('data/terrain.json','w'))
print('terrain',W,H,'png MB',len(buf.getvalue())/1e6, bounds)
