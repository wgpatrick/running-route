import json,os,sys,subprocess,urllib.parse,csv,concurrent.futures as cf
S,D=sys.argv[1],sys.argv[2]
d=json.load(open(S+'/bbl.json'))
od=S+'/bbl_fil'; os.makedirs(od,exist_ok=True)
def f(e):
    out=od+'/'+e['sub_path'].replace('/','__')
    if not os.path.exists(out):
        subprocess.run(['curl','-sS','-m','60','-f','-o',out,'https://raw.githubusercontent.com/bambulab/BambuStudio/HEAD/resources/profiles/BBL/'+urllib.parse.quote(e['sub_path'])],capture_output=True)
    return e['name'],out
with cf.ThreadPoolExecutor(12) as ex: res=list(ex.map(f,d['filament_list']))
prof={}
for n,out in res:
    try: prof[n]=json.load(open(out))
    except Exception as ex: pass
print(len(prof),'of',len(res))
keys=['pressure_advance','enable_pressure_advance','filament_max_volumetric_speed','nozzle_temperature','filament_flow_ratio','filament_density','filament_type','filament_shrink','temperature_vitrification','hot_plate_temp','filament_retraction_length','nozzle_temperature_range_high']
def res_key(n,k,depth=0):
    p=prof.get(n)
    if p is None or depth>8: return None
    if k in p: return p[k]
    if p.get('inherits'): return res_key(p['inherits'],k,depth+1)
    return None
rows=[]
for n,p in prof.items():
    if p.get('instantiation')!='true': continue
    r={'name':n,'compatible_printers':'|'.join(p.get('compatible_printers',[]))[:300]}
    for k in keys:
        v=res_key(n,k)
        r[k]=v[0] if isinstance(v,list) and v else v
    rows.append(r)
od2=D+'/slicer_profiles/bambustudio_filament_derived'; os.makedirs(od2,exist_ok=True)
with open(od2+'/bbl_filament_pa_flow.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows),'instantiated')
import collections
pa=collections.defaultdict(list); mv=collections.defaultdict(list)
for r in rows:
    try: pa[r['filament_type']].append(float(r['pressure_advance']))
    except Exception: pass
    try: mv[r['filament_type']].append(float(r['filament_max_volumetric_speed']))
    except Exception: pass
for t in sorted(pa,key=lambda t:-len(pa[t]))[:12]:
    v=sorted(pa[t]); m=sorted(mv[t])
    print(t,len(v),'PA min/med/max',v[0],v[len(v)//2],v[-1],'| maxvol min/med/max',m[0],m[len(m)//2],m[-1])
