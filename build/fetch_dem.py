import math, requests, io, numpy as np, os
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
W,S,E,N = -122.5155,37.7040,-122.3550,37.8120
Z=15
def tx(lon): return (lon+180)/360*2**Z
def ty(lat): r=math.radians(lat); return (1-math.log(math.tan(r)+1/math.cos(r))/math.pi)/2*2**Z
x0,x1=int(tx(W)),int(tx(E)); y0,y1=int(ty(N)),int(ty(S))
os.makedirs("data/tiles",exist_ok=True)
def get(xy):
    x,y=xy; p=f"data/tiles/{x}_{y}.png"
    if not os.path.exists(p):
        r=requests.get(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png",timeout=60); r.raise_for_status(); open(p,"wb").write(r.content)
    a=np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    return xy, a[...,0]*256+a[...,1]+a[...,2]/256-32768
jobs=[(x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)]
H=(y1-y0+1)*256; Wd=(x1-x0+1)*256
dem=np.zeros((H,Wd),np.float32)
with ThreadPoolExecutor(16) as ex:
    for (x,y),a in ex.map(get,jobs): dem[(y-y0)*256:(y-y0+1)*256,(x-x0)*256:(x-x0+1)*256]=a
np.savez_compressed("data/dem.npz",dem=dem,z=Z,x0=x0,y0=y0)
print(len(jobs),"tiles",dem.shape,dem.min(),dem.max())
