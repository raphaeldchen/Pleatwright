import json,os,re,ast,statistics as st,sys
S=sys.argv[1]
rs=[json.loads(l) for l in open(S+'/bp_eff.jsonl')]
old={json.loads(l)['roll']:json.loads(l) for l in open('../../docs/superpowers/evidence/2026-10-06-corigami-pipeline/records.jsonl')}
rows=[]
print("roll rung N Ginit D N/G N/D sumflap nflap rivercells% minball% exp_med virt tm_ratio stage")
for r in rs:
    d=json.load(open('full17_v3_trees/'+r['roll']+'.json'))
    fo=json.loads(d['served_fold']); s_tm=float(re.search(r'scale=([0-9.]+)',fo['frame_title']).group(1))
    tn=ast.literal_eval(d['tree_nodes']) if isinstance(d['tree_nodes'],str) else d['tree_nodes']
    names=ast.literal_eval(d['names']) if isinstance(d['names'],str) else d['names']
    s=json.load(open('full17_v3_sticks/'+r['roll']+'.json')); sl={n['name']:n['length'] for n in s['nodes']}
    ks=[sl[names[str(n['id'])]]/n['length'] for n in tn if n['length']>0 and names[str(n['id'])] in sl]
    k=st.median(ks); N=r['N']
    tm=(k/N)/s_tm
    assert N==old[r['roll']]['grid_size'], r['roll']
    exps=[e for e in r['flap_expansion'] if e]
    row=dict(roll=r['roll'],rung=r['rung'],N=N,G=r['grid_init'],D=r['diameter'],NG=N/r['grid_init'],ND=N/r['diameter'],
             sumflap=r['sum_flap'],nflap=r['n_flaps'],riv=r['river_cells']/N**2,ball=r['min_ball_sum']/N**2,
             exp=st.median(exps),virt=r['virtual_lines'],tm=tm,stage=d['served_stage'],hubs=r['n_hubs'])
    rows.append(row)
    print(f"{row['roll']} {row['rung'][:4]} {N} {row['G']} {row['D']} {row['NG']:.2f} {row['ND']:.2f} {row['sumflap']} {row['nflap']} {100*row['riv']:.1f} {100*row['ball']:.1f} {row['exp']:.2f} {row['virt']} {tm:.3f} {row['stage']} hubs={row['hubs']}")
def q(k):
    v=sorted(x[k] for x in rows); return f"{k}: min {v[0]:.3f} med {st.median(v):.3f} mean {st.mean(v):.3f} max {v[-1]:.3f}"
for k in ('N','NG','ND','riv','ball','exp','tm','virt','hubs'): print(q(k))
print('N==G_init:',sum(1 for x in rows if x['N']==x['G']), ' tm>=1:',sum(1 for x in rows if x['tm']>=1))
clean=[x for x in rows if x['stage'] not in ('stub','jitter')]
v=[x['tm'] for x in clean]; print('tm ratio excl stub/jitter n=',len(v),'med',round(st.median(v),3),'mean',round(st.mean(v),3))
import collections; print(collections.Counter(x['hubs'] for x in rows))
