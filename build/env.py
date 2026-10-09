"""Surroundings for the street graph: parks and water (nice), industrial land (not), traffic signals,
drinking fountains and public toilets. Everything comes from the Overture base theme (OpenStreetMap-derived)."""
import pyarrow.parquet as pq, shapely, numpy as np, math
from shapely import STRtree

LAT0, LON0 = 37.76, -122.44
M_LAT = 111320.0; M_LON = 111320.0 * math.cos(math.radians(LAT0))
def to_m(geom):
    return shapely.transform(geom, lambda c: np.column_stack([(c[:, 0] - LON0) * M_LON, (c[:, 1] - LAT0) * M_LAT]))

GREEN_LU = {'park', 'dog_park', 'recreation_ground', 'golf_course', 'national_park', 'meadow', 'grass', 'protected_landscape_seascape', 'garden', 'pitch'}
GREEN_LAND = {'wood', 'forest', 'grass', 'grassland', 'scrub', 'shrubbery', 'heath', 'beach', 'sand', 'wetland'}
INDUSTRIAL = {'industrial', 'brownfield', 'railway'}
WATER = {'bay', 'ocean', 'strait', 'lake', 'reservoir', 'river'}

def _polys(table, classes, min_area=0, max_area=None):
    t = pq.read_table(f'data/{table}.parquet').to_pandas()
    t = t[t['class'].isin(classes)]
    geoms = [to_m(g) for g in shapely.from_wkb(t.geometry.values)]
    out = []
    for g in geoms:
        if g.geom_type not in ('Polygon', 'MultiPolygon'): continue
        a = g.area
        if a < min_area or (max_area and a > max_area): continue
        out.append(g)
    return out

class Env:
    def __init__(self):
        # Mount Sutro's "species management area" is a park-like reserve; the marine sanctuary is water
        lu = pq.read_table('data/landuse.parquet').to_pandas()
        sutro = [to_m(g) for g, n in zip(shapely.from_wkb(lu.geometry.values), lu.names) if n is not None and (n.get('primary') or '').startswith('Mount Sutro')]
        green = _polys('landuse', GREEN_LU, min_area=400) + _polys('land', GREEN_LAND, min_area=400) + sutro
        self.green = STRtree(green); self.green_geoms = green
        ind = _polys('landuse', INDUSTRIAL, min_area=300)
        self.ind = STRtree([g.buffer(30) for g in ind])
        water = _polys('water', WATER, min_area=2000)
        self.water = STRtree([g.buffer(90) for g in water])
        self.green_touch = STRtree([g.buffer(25) for g in green if g.area > 5000])  # streets along a real park
        infra = pq.read_table('data/infra.parquet').to_pandas()
        pts = shapely.from_wkb(infra.geometry.values)
        sig = [to_m(p) for p, c in zip(pts, infra['class']) if c == 'traffic_signals']
        self.signals = STRtree(sig)
        self.amenities = []
        for p, c, n in zip(pts, infra['class'], infra.names):
            if c not in ('toilets', 'drinking_water'): continue
            if p.geom_type != 'Point': p = p.centroid
            name = (n.get('primary') if n is not None else None) or ''
            if name in ('Men', 'Women', "Men's Restroom", "Women's Restroom"): name = ''
            self.amenities.append([round(p.y, 5), round(p.x, 5), 'water' if c == 'drinking_water' else 'toilet', name[:40]])
        print('env: green', len(green), 'industrial', len(ind), 'water', len(water), 'signals', len(sig), 'amenities', len(self.amenities))

    def edge_flags(self, pts_m):
        """bit0 green (in or beside a park), bit1 waterfront, bit2 industrial. pts_m: list of (x, y) metres."""
        P = shapely.points(np.array(pts_m))
        n = len(P)
        def frac(tree):
            hits = tree.query(P, predicate='within')
            return len(set(hits[0].tolist())) / n
        f = 0
        if frac(self.green) >= 0.5 or frac(self.green_touch) >= 0.6: f |= 1
        if frac(self.water) >= 0.5: f |= 2
        if frac(self.ind) >= 0.5: f |= 4
        return f

    def node_signal(self, xy_m, radius=18):
        pt = shapely.points(np.array(xy_m))
        hits = self.signals.query(pt, predicate='dwithin', distance=radius)
        out = np.zeros(len(xy_m), np.uint8); out[np.unique(hits[0])] = 1
        return out
