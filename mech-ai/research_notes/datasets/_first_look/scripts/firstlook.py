import sys,csv,os,math,collections,json
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
D=sys.argv[1]; O=D+'/_first_look'
BLUE,ORANGE,AQUA='#2a78d6','#eb6834','#1baf7a'; INK='#0b0b0b'; MUT='#52514e'; SURF='#fcfcfb'
plt.rcParams.update({'figure.facecolor':SURF,'axes.facecolor':SURF,'axes.edgecolor':'#c9c8c2','axes.labelcolor':MUT,'xtick.color':MUT,'ytick.color':MUT,'text.color':INK,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.color':'#e6e5df','grid.linewidth':0.6,'font.size':9,'lines.linewidth':2})
res={}
# ---- 1 PSD corpus
rows=list(csv.DictReader(open(D+'/klipper_resonance_psd_corpus/corpus_index_and_peaks.csv')))
th=[r for r in rows if r['kind'].startswith('toolhead') and r['zeta_half_power'] and float(r['peak_over_median'])>=5]
def cls(m): return 'CoreXY (Voron etc.)' if ('Voron' in m and 'Switchwire' not in m) or 'CoreXY' in m else 'bed slinger' if 'slinger' in m or 'Switchwire' in m else 'other/unknown'
z={a:np.array([float(r['zeta_half_power']) for r in th if r['kind']=='toolhead_'+a]) for a in 'xy'}
f={a:np.array([float(r['peak_hz']) for r in th if r['kind']=='toolhead_'+a]) for a in 'xy'}
res['psd']={a:dict(n=int(len(z[a])),zeta_p10=float(np.percentile(z[a],10)),zeta_med=float(np.median(z[a])),zeta_p90=float(np.percentile(z[a],90)),f_p10=float(np.percentile(f[a],10)),f_med=float(np.median(f[a])),f_p90=float(np.percentile(f[a],90))) for a in 'xy'}
res['psd']['machines']=len({r['repo'] for r in th}); res['psd']['files_total']=len(rows)
bycls=collections.defaultdict(list)
for r in th: bycls[(cls(r['machine_guess']),r['kind'][-1])].append((float(r['peak_hz']),float(r['zeta_half_power'])))
res['psd']['by_class']={f'{k[0]} {k[1]}':dict(n=len(v),f_med=float(np.median([a for a,b in v])),zeta_med=float(np.median([b for a,b in v]))) for k,v in bycls.items()}
fig,ax=plt.subplots(1,2,figsize=(10,3.8))
bins=np.arange(0,0.30,0.02)
ax[0].hist([np.clip(z['x'],0,0.29),np.clip(z['y'],0,0.29)],bins=bins,color=[BLUE,ORANGE],label=[f"X axis (n={len(z['x'])})",f"Y axis (n={len(z['y'])})"],rwidth=0.85)
for v,lab,hh in[(0.05,'twin belt damper 0.05',0.93),(0.10,'Klipper assumes 0.1',0.84)]:
    ax[0].axvline(v,color=MUT,lw=1,ls='--'); ax[0].text(v+0.003,ax[0].get_ylim()[1]*hh,lab,color=MUT,fontsize=8)
ax[0].set_xlabel('damping ratio of main peak (half-power width; floor about 0.02-0.03 from 1.5 Hz bins)'); ax[0].set_ylabel('resonance test files'); ax[0].legend(frameon=False,loc='center right')
ax[0].set_title('Damping ratio, toolhead resonance tests from public config repos',loc='left',fontsize=10)
ax[1].scatter(f['x'],z['x'],s=22,color=BLUE,label='X axis',edgecolor=SURF,linewidth=0.8); ax[1].scatter(f['y'],z['y'],s=22,color=ORANGE,label='Y axis',edgecolor=SURF,linewidth=0.8)
ax[1].set_xlabel('main peak frequency (Hz)'); ax[1].set_ylabel('damping ratio'); ax[1].set_ylim(0,0.3); ax[1].legend(frameon=False)
ax[1].set_title('Peak frequency against damping',loc='left',fontsize=10)
fig.tight_layout(); fig.savefig(O+'/psd_corpus_damping.png',dpi=140); plt.close(fig)
# ---- 2 hotend log: single-node and two-node fit
def load(p):
    r=list(csv.DictReader(open(p)))
    t=np.array([float(x['time']) for x in r]); t-=t[0]
    return t,np.array([float(x['T1_real']) for x in r]),np.array([float(x['pwm']) for x in r]),np.array([float(x['fan_state']) for x in r])
p=D+'/ender3_hotend_twin_logs/benchmark__2026-09-25_1443_klipper_245tutma_fan_soguma.csv'
t,T,pwm,fan=load(p)
PMAX,TA=40.0,25.0
tg=np.arange(0,t[-1],0.25); Tg=np.interp(tg,t,T); pg=np.interp(tg,t,pwm); fg=np.interp(tg,t,fan)
def sim1(x):
    C,h0,hf,lag=x; out=np.empty_like(tg); Tm=Tg[0]; n=int(round(lag/0.25))
    for i in range(len(tg)):
        out[i]=Tm; pw=pg[max(i-n,0)]
        Tm+=0.25*(PMAX*pw-(h0+hf*fg[i])*(Tm-TA))/C
    return out
def sim2(x):
    C1,C2,R12,h0,hf=x; out=np.empty_like(tg); a=b=Tg[0]
    for i in range(len(tg)):
        out[i]=b
        qa=(a-b)/R12
        a+=0.25*(PMAX*pg[i]-qa)/C1
        b+=0.25*(qa-(h0+hf*fg[i])*(b-TA))/C2
    return out
r1=least_squares(lambda x:sim1(x)-Tg,[8,0.1,0.05,2],bounds=([1,0.01,0,0],[40,1,1,10]))
r2=least_squares(lambda x:sim2(x)-Tg,[2,6,3,0.1,0.05],bounds=([0.2,0.5,0.1,0.01,0],[20,40,30,1,1]))
res['hotend']=dict(file=os.path.basename(p),duration_s=float(t[-1]),n=int(len(t)),Tmax=float(T.max()),
   one_node=dict(C_J_per_K=float(r1.x[0]),h_still_W_per_K=float(r1.x[1]),h_fan_extra_W_per_K=float(r1.x[2]),lag_s=float(r1.x[3]),rmse_C=float(np.sqrt(np.mean(r1.fun**2))),tau_s=float(r1.x[0]/r1.x[1])),
   two_node=dict(C_heater=float(r2.x[0]),C_block=float(r2.x[1]),R12_K_per_W=float(r2.x[2]),h_still=float(r2.x[3]),h_fan_extra=float(r2.x[4]),rmse_C=float(np.sqrt(np.mean(r2.fun**2)))))
fig,ax=plt.subplots(3,1,figsize=(10,6.6),sharex=True,gridspec_kw={'height_ratios':[3,1.3,1.2]})
ax[0].plot(tg,Tg,color=INK,lw=1.6,label='measured thermistor'); ax[0].plot(tg,sim1(r1.x),color=BLUE,lw=1.4,label=f"1-node fit (RMSE {res['hotend']['one_node']['rmse_C']:.1f} °C)"); ax[0].plot(tg,sim2(r2.x),color=ORANGE,lw=1.4,label=f"2-node fit (RMSE {res['hotend']['two_node']['rmse_C']:.1f} °C)")
ax[0].set_ylabel('temperature (°C)'); ax[0].legend(frameon=False); ax[0].set_title('Ender 3 hotend calibration run (heat to 245 °C, hold, fan on, cool): open-loop fits driven by logged heater PWM',loc='left',fontsize=10)
ax[1].plot(tg,sim1(r1.x)-Tg,color=BLUE,lw=1.2); ax[1].plot(tg,sim2(r2.x)-Tg,color=ORANGE,lw=1.2); ax[1].axhline(0,color=MUT,lw=0.8); ax[1].set_ylabel('model − measured (°C)')
ax[2].plot(tg,pg,color=INK,lw=1,label='heater PWM'); ax[2].plot(tg,fg,color=AQUA,lw=1.4,label='part fan'); ax[2].set_ylabel('duty (0–1)'); ax[2].set_xlabel('time (s)'); ax[2].legend(frameon=False,ncol=2)
fig.tight_layout(); fig.savefig(O+'/hotend_log_fit.png',dpi=140); plt.close(fig)
# ---- 3 belt plucks
pl={}
fig,ax=plt.subplots(figsize=(8,3.6))
for name,col in[('a_belt_86hz_1',BLUE),('b_belt_82hz_1',ORANGE)]:
    a=np.array([[float(v) for v in l.split(',')] for l in open(D+f'/helixscreen_belt_plucks/{name}.csv') if l[0] not in '#'])
    fs=1/np.median(np.diff(a[:,0])); s=np.linalg.norm(a[:,1:4]-a[:,1:4].mean(0),axis=1); 
    best=None
    for c in range(1,4):
        y=(a[:,c]-a[:,c].mean())*np.hanning(len(a)); Y=np.abs(np.fft.rfft(y,8*len(y))); fr=np.fft.rfftfreq(8*len(y),1/fs)
        if best is None or Y.max()>best[1].max(): best=(fr,Y)
    fr,Y=best; m=(fr>30)&(fr<200); fp=float(fr[m][np.argmax(Y[m])])
    rho,L=0.0084,0.151; pl[name]=dict(fs=float(fs),n=int(len(a)),peak_hz=fp,tension_N_if_6mm=4*rho*L*L*fp*fp,tension_N_if_9mm=4*0.0126*L*L*fp*fp)
    ax.plot(fr[m],Y[m]/Y[m].max(),color=col,label=f"{name}: peak {fp:.1f} Hz")
ax.set_xlabel('frequency (Hz)'); ax.set_ylabel('normalised amplitude'); ax.legend(frameon=False); ax.set_title('Belt pluck ring-down spectra, Voron 2.4 300, 151 mm span',loc='left',fontsize=10)
fig.tight_layout(); fig.savefig(O+'/belt_pluck_spectra.png',dpi=140); plt.close(fig)
res['plucks']=pl
# ---- 4 ARTS lvm peek
p=D+'/arts_fff_lifecycle_vibration/raw_vibration__Sample01.lvm'
hdr=[];n=0;first=None
with open(p,errors='replace') as fh:
    for i,l in enumerate(fh):
        if i<30: hdr.append(l.rstrip()[:120])
        n+=1
res['arts']=dict(lines=n,header=hdr[:26])
json.dump(res,open(O+'/first_look_results.json','w'),indent=1)
print(json.dumps({k:v for k,v in res.items() if k!='arts'},indent=1)); print('\n'.join(hdr[20:26]),n)
