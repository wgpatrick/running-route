import pyarrow.dataset as ds, pyarrow.fs as fs, pyarrow.parquet as pq, pyarrow.compute as pc, sys, time
R = "overturemaps-us-west-2/release/2026-09-23.0"
W,S,E,N = -122.5155,37.7040,-122.3550,37.8120
s3 = fs.S3FileSystem(anonymous=True, region="us-west-2", tls_ca_file_path="/root/.ccr/ca-bundle.crt")
def grab(path, cols, extra, out):
    t=time.time()
    d = ds.dataset(f"{R}/{path}", filesystem=s3, format="parquet")
    f = (pc.field("bbox","xmin") > W) & (pc.field("bbox","xmax") < E) & (pc.field("bbox","ymin") > S) & (pc.field("bbox","ymax") < N)
    if extra is not None: f = f & extra
    tbl = d.to_table(columns=cols, filter=f)
    pq.write_table(tbl, out); print(out, tbl.num_rows, round(time.time()-t), "s", flush=True)
which = sys.argv[1]
if which=="seg":
    grab("theme=transportation/type=segment", ["id","class","subclass","names","geometry","connectors","road_flags","access_restrictions","road_surface"], pc.field("subtype")=="road", "data/segments.parquet")
elif which=="addr":
    grab("theme=addresses/type=address", ["number","street","postcode","geometry"], None, "data/addresses.parquet")
elif which=="places":
    grab("theme=places/type=place", ["names","categories","geometry","confidence"], None, "data/places.parquet")
