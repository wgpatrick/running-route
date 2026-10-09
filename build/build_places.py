"""Thin the SF address points into a small geocoding index, and place curated destinations on the DEM."""
import pyarrow.parquet as pq, shapely, numpy as np, json, re, math, collections, gzip
from build_graph_elev import elev
a=pq.read_table('data/addresses.parquet').to_pandas()
pts=shapely.from_wkb(a.geometry.values); a['lon']=shapely.get_x(pts); a['lat']=shapely.get_y(pts)
a['n']=pd_num=a.number.str.extract(r'^(\d+)')[0].astype(float)
a=a.dropna(subset=['n','street'])
idx=collections.defaultdict(dict)
for st,n,lon,lat in zip(a.street.str.upper(),a.n.astype(int),a.lon,a.lat):
    idx[st].setdefault(n,(lon,lat))
out={}
for st,d in idx.items():
    ns=sorted(d)
    keep=[]; last=None
    for n in ns:  # keep about one point per 10 house numbers per side
        if last is None or n-last>=10 or n==ns[-1]: keep.append(n); last=n
    # flattened [n, lon*1e5, lat*1e5,...]
    out[st]=[v for n in keep for v in (n,round(d[n][0]*1e5),round(d[n][1]*1e5))]
s=json.dumps(out,separators=(',',':'))
open('data/addr.json','w').write(s)
print('streets',len(out),'pts',sum(len(v)//3 for v in out.values()),'MB',len(s)/1e6,'gz',len(gzip.compress(s.encode()))/1e6)

# curated destinations: (name, lat, lon, kind, blurb)
P=[
("Bernal Heights Summit",37.7432,-122.4142,"hill","Grassy summit with 360° views, the radio tower, and dogs everywhere"),
("Holly Park",37.7365,-122.4193,"hill","Round hilltop park circled by a loop path"),
("Twin Peaks",37.7531,-122.4473,"hill","The classic SF summit and Christmas Tree Point lookout; big climb, huge view"),
("Mount Davidson",37.7383,-122.4537,"hill","SF's highest point, wooded trails up to the big cross"),
("Corona Heights",37.7652,-122.4382,"hill","Rocky red-chert outcrop above the Castro"),
("Tank Hill",37.7598,-122.4476,"hill","Tiny rocky knob with a big downtown view"),
("Buena Vista Park",37.7686,-122.4413,"hill","Oldest park in SF, steep forested paths"),
("Grand View Park",37.7563,-122.4719,"hill","Turtle Hill: sunset-side views of the ocean and GG Park"),
("16th Ave Tiled Steps",37.7563,-122.4733,"place","163 mosaic stairs up Golden Gate Heights"),
("Mount Sutro",37.7585,-122.4580,"hill","Eucalyptus cloud forest with dirt trails"),
("Billy Goat Hill",37.7414,-122.4335,"hill","Rope-swing hilltop over Glen Park"),
("Walter Haas Playground",37.7406,-122.4371,"hill","Diamond Heights perch above Glen Canyon"),
("Kite Hill",37.7585,-122.4361,"hill","Small open hill between Castro and Noe"),
("Dolores Park (top)",37.7596,-122.4269,"place","The south-west corner with the skyline view"),
("McKinley Square",37.7591,-122.4040,"hill","Potrero Hill park with a downtown view"),
("Starr King Open Space",37.7570,-122.3988,"hill","Quiet top of Potrero Hill"),
("Mount Olympus",37.7631,-122.4456,"hill","Hidden summit, geographic center of SF"),
("Alta Plaza",37.7912,-122.4375,"hill","Terraced Pacific Heights hilltop"),
("Lafayette Park",37.7915,-122.4278,"hill","Pacific Heights park with bay glimpses"),
("Coit Tower",37.8024,-122.4058,"hill","Telegraph Hill summit; steep stairs nearby"),
("Russian Hill Park",37.8015,-122.4196,"hill","Larkin St hilltop over Alcatraz"),
("Huntington Park",37.7924,-122.4122,"hill","Top of Nob Hill"),
("Lone Mountain",37.7783,-122.4513,"hill","USF hilltop campus"),
("Strawberry Hill",37.7688,-122.4752,"hill","Island summit in Stow Lake"),
("McLaren Park Summit",37.7187,-122.4205,"hill","Big rolling park with trails and reservoir"),
("Bayview Hill",37.7137,-122.3965,"hill","Wild, quiet hilltop in the southeast"),
("Sutro Heights",37.7787,-122.5127,"hill","Garden ruins above Ocean Beach"),
("Alamo Square",37.7764,-122.4346,"hill","Painted Ladies hilltop"),
("Ferry Building",37.7955,-122.3937,"place","Embarcadero waterfront"),
("Oracle Park",37.7786,-122.3893,"place","Ballpark on the bay"),
("Crissy Field",37.8040,-122.4560,"place","Flat bayfront path toward the Golden Gate"),
("Palace of Fine Arts",37.8029,-122.4484,"place","Lagoon and rotunda in the Marina"),
("Ocean Beach",37.7594,-122.5107,"place","Great Highway promenade"),
("Stow Lake",37.7700,-122.4730,"place","Golden Gate Park lake loop"),
("Panhandle",37.7726,-122.4440,"place","Flat tree-lined path into GG Park"),
("Lake Merced",37.7270,-122.4920,"place","4.5-mile flat loop around the lake"),
("Stern Grove",37.7357,-122.4780,"place","Eucalyptus valley amphitheater"),
("Glen Canyon Park",37.7404,-122.4415,"place","Creek canyon with trails and rock outcrops"),
("Precita Park",37.7470,-122.4128,"place","Flat park at the north foot of Bernal"),
("Heron's Head Park",37.7393,-122.3762,"place","Bayside marsh trail"),
("Mission Bay",37.7705,-122.3910,"place","Waterfront paths and parks"),
("Duboce Park",37.7690,-122.4335,"place","Neighborhood park in the Lower Haight"),
("Alcatraz View: Aquatic Park",37.8065,-122.4225,"place","Pier, beach and Muni pier loop"),
("Fort Funston",37.7143,-122.5025,"place","Clifftop dunes and hang gliders above the ocean"),
("Lands End",37.7804,-122.5050,"place","Coastal trail with Golden Gate views"),
("Golden Gate Bridge",37.8077,-122.4750,"place","South end of the bridge at the welcome center"),
("Baker Beach",37.7936,-122.4836,"place","Beach below the Presidio bluffs"),
("City Hall",37.7793,-122.4193,"place","Civic Center plaza"),
("Fort Mason",37.8065,-122.4312,"place","Great Meadow and waterfront piers"),
("Washington Square",37.8008,-122.4100,"place","North Beach's park"),
("Lake Merced Boathouse",37.7275,-122.4935,"place","North end of the Lake Merced loop"),
]
lat=np.array([p[1] for p in P]); lon=np.array([p[2] for p in P])
# refine hills to the local DEM max within ~150 m
res=[]
for (name,la,lo,kind,blurb) in P:
    if kind=='hill':
        g=np.linspace(-80,80,17)
        LA=la+g[:,None]/111320+0*g[None,:]; LO=lo+0*g[:,None]+g[None,:]/(111320*math.cos(math.radians(la)))
        E=elev(LO.ravel(),LA.ravel()); i=int(np.argmax(E)); la2,lo2=LA.ravel()[i],LO.ravel()[i]
        print(f"{name:28s} {float(elev(np.array([lo]),np.array([la]))[0]):6.0f}m -> {E[i]:6.0f}m  moved {math.hypot((la2-la)*111320,(lo2-lo)*88000):4.0f}m")
        la,lo=float(la2),float(lo2)
    res.append(dict(name=name,lat=round(la,5),lon=round(lo,5),kind=kind,blurb=blurb,el=round(float(elev(np.array([lo]),np.array([la]))[0]))))
json.dump(res,open('data/places.json','w'),indent=0)
