import json,os,sys,re,csv,configparser,statistics as st
S,D=sys.argv[1],sys.argv[2]
idx=json.load(open(S+'/cfg_index.json'))
out=D+'/firmware_fitted_parameters/derived'; os.makedirs(out,exist_ok=True)
# Klipper
rows=[]
for p,loc in idx['k']:
    if not loc: continue
    sec=None; cur={}
    def flush():
        if sec and 'pid_kp' in cur:
            try:
                kp,ki,kd=float(cur['pid_kp']),float(cur['pid_ki']),float(cur['pid_kd'])
            except Exception: return
            if ki<=0: return
            tu=2*kp/ki; ku=kp/0.6/255.0
            rows.append(dict(file=p,section=sec,pid_Kp=kp,pid_Ki=ki,pid_Kd=kd,Tu_s=round(tu,2),Ku_per_K=round(ku,5),Kd_check=round(kd/(kp*tu/8),3) if kp*tu else '',
                 sensor=cur.get('sensor_type',''),max_power=cur.get('max_power','')))
    for line in open(loc,errors='replace'):
        l=line.split('#')[0].strip()
        m=re.match(r'\[(.+)\]',l)
        if m: flush(); sec=m.group(1); cur={}; continue
        m=re.match(r'([A-Za-z_0-9]+)\s*[:=]\s*(.+)',l)
        if m: cur[m.group(1).lower()]=m.group(2).strip()
    flush()
with open(out+'/klipper_config_pid.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def summ(name,v):
    v=sorted(v); n=len(v)
    if n: print(name,'n',n,'p10 %.3g med %.3g p90 %.3g'%(v[n//10],v[n//2],v[9*n//10]))
ext=[r for r in rows if r['section'].startswith('extruder')]; bed=[r for r in rows if 'bed' in r['section']]
print('klipper rows',len(rows))
summ('klipper extruder Tu',[r['Tu_s'] for r in ext]); summ('klipper extruder Ku',[r['Ku_per_K'] for r in ext])
summ('klipper bed Tu',[r['Tu_s'] for r in bed]); summ('klipper bed Ku',[r['Ku_per_K'] for r in bed])
summ('Kd check',[r['Kd_check'] for r in rows if r['Kd_check']!=''])
# Marlin
mr=[]
keys=['DEFAULT_KP','DEFAULT_KI','DEFAULT_KD','DEFAULT_BED_KP','DEFAULT_BED_KI','DEFAULT_BED_KD','MPC_HEATER_POWER','MPC_BLOCK_HEAT_CAPACITY','MPC_SENSOR_RESPONSIVENESS','MPC_AMBIENT_XFER_COEFF','MPC_AMBIENT_XFER_COEFF_FAN255','MPC_FILAMENT_HEAT_CAPACITY_PERMM']
for p,loc in idx['m']:
    if not loc: continue
    t=open(loc,errors='replace').read()
    r=dict(file=p)
    r['PIDTEMP']=bool(re.search(r'^\s*#define\s+PIDTEMP\b',t,re.M)); r['MPCTEMP']=bool(re.search(r'^\s*#define\s+MPCTEMP\b',t,re.M)); r['PIDTEMPBED']=bool(re.search(r'^\s*#define\s+PIDTEMPBED\b',t,re.M))
    for k in keys:
        m=re.search(r'^\s*#define\s+'+k+r'\s+\{?\s*([-0-9.eE]+)f?',t,re.M)
        r[k]=float(m.group(1)) if m else ''
    mr.append(r)
with open(out+'/marlin_config_pid_mpc.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(mr[0])); w.writeheader(); w.writerows(mr)
print('marlin rows',len(mr),'MPC enabled',sum(r['MPCTEMP'] for r in mr))
hp=[r for r in mr if r['PIDTEMP'] and r['DEFAULT_KI']]
summ('marlin hotend Tu',[2*r['DEFAULT_KP']/r['DEFAULT_KI'] for r in hp if r['DEFAULT_KI']>0])
bp=[r for r in mr if r['PIDTEMPBED'] and r['DEFAULT_BED_KI']]
summ('marlin bed Tu',[2*r['DEFAULT_BED_KP']/r['DEFAULT_BED_KI'] for r in bp if r['DEFAULT_BED_KI']>0])
import collections
print('distinct hotend PID sets',len({(r['DEFAULT_KP'],r['DEFAULT_KI'],r['DEFAULT_KD']) for r in hp}),'distinct bed',len({(r['DEFAULT_BED_KP'],r['DEFAULT_BED_KI']) for r in bp}))
mpc=[r for r in mr if r['MPCTEMP']]
dm={(r['MPC_HEATER_POWER'],r['MPC_BLOCK_HEAT_CAPACITY'],r['MPC_SENSOR_RESPONSIVENESS'],r['MPC_AMBIENT_XFER_COEFF'],r['MPC_AMBIENT_XFER_COEFF_FAN255']) for r in mpc}
print('distinct MPC sets among enabled',len(dm))
for r in mpc[:40]: print(r['file'].split('/')[-3:-1],r['MPC_HEATER_POWER'],r['MPC_BLOCK_HEAT_CAPACITY'],r['MPC_SENSOR_RESPONSIVENESS'],r['MPC_AMBIENT_XFER_COEFF'],r['MPC_AMBIENT_XFER_COEFF_FAN255'])
allm={(r['MPC_HEATER_POWER'],r['MPC_BLOCK_HEAT_CAPACITY'],r['MPC_SENSOR_RESPONSIVENESS'],r['MPC_AMBIENT_XFER_COEFF'],r['MPC_AMBIENT_XFER_COEFF_FAN255']) for r in mr}
print('distinct MPC sets all files',len(allm)); print(sorted(allm,key=str)[:30])
c=collections.Counter((r['DEFAULT_KP'],r['DEFAULT_KI'],r['DEFAULT_KD']) for r in hp); print(c.most_common(4))
c=collections.Counter((r['DEFAULT_BED_KP'],r['DEFAULT_BED_KI'],r['DEFAULT_BED_KD']) for r in bp); print(c.most_common(4))
