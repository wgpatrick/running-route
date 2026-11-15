import json,os,sys,re,csv,shutil,math
S,D=sys.argv[1],sys.argv[2]
idx=json.load(open(S+'/corpus/index.json')); lic=json.load(open(S+'/corpus/licences.json'))
OPEN={}
for r,v in lic.items():
    if not v: continue
    t=v[1]
    k='MIT' if 'MIT License' in t else 'CC0-1.0' if 'CC0' in t else 'Apache-2.0' if 'Apache' in t else 'GPL-3.0' if 'GNU GENERAL PUBLIC' in t else 'CC BY-NC-SA' if 'Non-Commercial' in t else '?'
    OPEN[r]=k
def machine(repo,path):
    s=(repo+' '+path).lower()
    for k,v in [('v0','Voron 0'),('tiny','Voron 0-class'),('trident','Voron Trident'),('switchwire','Voron Switchwire'),('2.4','Voron 2.4'),('v24','Voron 2.4'),('voron24','Voron 2.4'),('v2','Voron 2.4'),('voron350','Voron 2.4'),('voron','Voron (unspecified)'),('ender','Ender 3 class (bed slinger)'),('sv01','Sovol SV01 (bed slinger)'),('neptune','Elegoo Neptune 4 (bed slinger)'),('k1','Creality K1 (CoreXY)'),('bear','Prusa Bear (bed slinger)'),('babycube','BabyCube (CoreXY)'),('tronxy','Tronxy X5SA (CoreXY)'),('qidi','Qidi X-Max'),('gasherbrum','Annex K3 (CoreXY)'),('massportal','Mass Portal delta'),('a20m','Geeetech A20M (bed slinger)')]:
        if k in s: return v
    return 'unknown'
def load(p):
    rows=[]
    with open(p,errors='replace') as f:
        rd=csv.reader(f); h=None
        for r in rd:
            if not r or r[0].startswith('#'): continue
            if h is None: h=[c.strip() for c in r]; continue
            try: rows.append([float(x) for x in r[:len(h)]])
            except ValueError: pass
    return h,rows
def peak(fr,ps):
    best=None
    for i in range(1,len(fr)-1):
        if 15<=fr[i]<=135 and ps[i]>=ps[i-1] and ps[i]>=ps[i+1]:
            if best is None or ps[i]>ps[best]: best=i
    if best is None: return None
    pk=ps[best]; half=pk/2
    def cross(rng):
        prev=best
        for j in rng:
            if ps[j]<=half:
                # linear interp between prev and j
                t=(ps[prev]-half)/(ps[prev]-ps[j]) if ps[prev]!=ps[j] else 0
                return fr[prev]+t*(fr[j]-fr[prev])
            prev=j
        return None
    f1=cross(range(best-1,-1,-1)); f2=cross(range(best+1,len(fr)))
    # parabolic refine
    a,b,c=ps[best-1],ps[best],ps[best+1]; den=a-2*b+c
    f0=fr[best]+(0.5*(a-c)/den*(fr[best+1]-fr[best]) if den else 0)
    z=(f2-f1)/(2*f0) if f1 and f2 else None
    # prominence: ratio of peak to median psd in 15-135
    band=sorted(ps[i] for i in range(len(fr)) if 15<=fr[i]<=135)
    return f0,z,pk/band[len(band)//2] if band[len(band)//2]>0 else float('inf')
out=[]
dst=D+'/klipper_resonance_psd_corpus'
for it in idx:
    p=it['local']
    try: h,rows=load(p)
    except Exception as e: continue
    if not h or h[0]!='freq' or len(rows)<30: continue
    base=os.path.basename(it['path']).lower()
    m=re.search(r'(resonances|calibration_data)_([xyz])',base)
    kind='toolhead_'+m.group(2) if m else ('belt_sweep' if 'belt_sweeps' in it['path'] else 'other')
    fr=[r[0] for r in rows]
    col='psd_xyz' if 'psd_xyz' in h else h[-1]
    ps=[r[h.index(col)] for r in rows]
    pk=peak(fr,ps)
    stored=''
    if it['repo'] in OPEN and OPEN[it['repo']]!='CC BY-NC-SA':
        d=dst+'/'+it['repo'].replace('/','__'); os.makedirs(d,exist_ok=True)
        shutil.copy(p,d+'/'+os.path.basename(p)); stored=os.path.relpath(d+'/'+os.path.basename(p),D)
    out.append(dict(repo=it['repo'],path=it['path'],url=it['url'],licence=OPEN.get(it['repo'],'none stated'),machine_guess=machine(it['repo'],it['path']),kind=kind,
        n_bins=len(rows),df_hz=round(fr[1]-fr[0],2),peak_hz=round(pk[0],1) if pk else '',zeta_half_power=round(pk[1],3) if pk and pk[1] else '',peak_over_median=round(pk[2],1) if pk else '',stored_as=stored))
os.makedirs(dst,exist_ok=True)
with open(dst+'/corpus_index_and_peaks.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(len(out),'parsed;',sum(1 for o in out if o['stored_as']),'stored;',len({o['repo'] for o in out}),'repos;',len({o['repo'] for o in out if o['stored_as']}),'repos stored')
import collections
c=collections.Counter(o['kind'] for o in out); print(c)
