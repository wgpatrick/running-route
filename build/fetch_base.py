import pyarrow.dataset as ds, pyarrow.fs as fs, pyarrow.parquet as pq, pyarrow.compute as pc, sys, time
R = "overturemaps-us-west-2/release/2026-09-23.0"
W,S,E,N = -122.5155,37.7040,-122.3550,37.8120
s3 = fs.S3FileSystem(anonymous=True, region="us-west-2", tls_ca_file_path="/root/.ccr/ca-bundle.crt")
def grab(path, cols, out):
    t=time.time()
    d = ds.dataset(f"{R}/{path}", filesystem=s3, format="parquet")
    f = (pc.field("bbox","xmin") < E) & (pc.field("bbox","xmax") > W) & (pc.field("bbox","ymin") < N) & (pc.field("bbox","ymax") > S)
    tbl = d.to_table(columns=cols, filter=f)
    pq.write_table(tbl, out); print(out, tbl.num_rows, round(time.time()-t), "s", flush=True)
which = sys.argv[1]
if which=="landuse": grab("theme=base/type=land_use", ["subtype","class","names","geometry"], "data/landuse.parquet")
elif which=="land": grab("theme=base/type=land", ["subtype","class","names","geometry"], "data/land.parquet")
elif which=="water": grab("theme=base/type=water", ["subtype","class","names","geometry"], "data/water.parquet")
elif which=="infra": grab("theme=base/type=infrastructure", ["subtype","class","names","geometry"], "data/infra.parquet")
