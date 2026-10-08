import numpy as np
D = np.load('data/dem.npz'); dem = D['dem']; Z=int(D['z']); X0=int(D['x0']); Y0=int(D['y0'])
def elev(lon, lat):
    n=2**Z
    px=((lon+180)/360*n - X0)*256 - .5
    r=np.radians(lat); py=((1-np.log(np.tan(r)+1/np.cos(r))/np.pi)/2*n - Y0)*256 - .5
    x0=np.floor(px).astype(int); y0=np.floor(py).astype(int); fx=px-x0; fy=py-y0
    g=lambda y,x: dem[np.clip(y,0,dem.shape[0]-1), np.clip(x,0,dem.shape[1]-1)]
    return (g(y0,x0)*(1-fx)*(1-fy)+g(y0,x0+1)*fx*(1-fy)+g(y0+1,x0)*(1-fx)*fy+g(y0+1,x0+1)*fx*fy)
