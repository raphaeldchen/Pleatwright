# Runs only on archive/treemaker-box-pleat (box_pleat is retired on main).
import json, glob, sys, os, time, multiprocessing as mp
ROOT="<repo>/mcp_harness"
sys.path.insert(0, ROOT)
MODE=sys.argv[1]; TO=int(sys.argv[2])
def run(fn, q):
    sys.path.insert(0, ROOT)
    from box_pleat.compile import compile_tree
    fx=json.load(open(fn))
    kw = dict(dense=True, sat_layers=True) if MODE=="dense" else (dict(sat_layers=True) if MODE=="sat" else {})
    t=time.time()
    r=compile_tree(fx["tree_nodes"], fx["symmetric_pairs"], **kw)
    q.put(dict(roll=fx["roll"], stage=r.stage_reached, fail=repr(r.failure)[:160], N=getattr(r.layout,"N",None),
               emit=r.fold is not None, secs=round(time.time()-t,1), timings=r.timings))
def one(fn):
    q=mp.Queue(); p=mp.Process(target=run,args=(fn,q)); p.start(); p.join(TO)
    if p.is_alive(): p.kill(); return dict(roll=os.path.basename(fn)[:-5], stage="TIMEOUT")
    return q.get() if not q.empty() else dict(roll=os.path.basename(fn), stage="CRASH", code=p.exitcode)
if __name__=="__main__":
    mp.set_start_method("spawn")
    fns=sorted(glob.glob(ROOT+"/fixtures/full17_v3_trees/*_*.json"))
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(one, fns): print(json.dumps(r), flush=True)
