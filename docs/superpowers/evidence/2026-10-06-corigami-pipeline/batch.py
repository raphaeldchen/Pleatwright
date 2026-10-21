import sys, os, json, glob, multiprocessing as mp, time
ROOT="<repo>/mcp_harness"
def work(args):
    roll,out,cert,q=args
    sys.path.insert(0,ROOT); os.chdir(ROOT)
    import warnings; warnings.filterwarnings("ignore")
    from pleatwright import pipeline
    try:
        rec=pipeline.run(roll,out,certify_global=cert,verbose=False)
    except Exception as e:
        import traceback; rec={"roll":roll,"failure":"exception","error":repr(e),"trace":traceback.format_exc()[-1500:]}
    q.put(rec)
def one(roll,out,cert,TO):
    q=mp.Queue(); p=mp.Process(target=work,args=((roll,out,cert,q),)); p.start(); p.join(TO)
    if p.is_alive(): p.kill(); return {"roll":roll,"failure":"timeout"}
    return q.get() if not q.empty() else {"roll":roll,"failure":"crash","code":p.exitcode}
if __name__=="__main__":
    mp.set_start_method("spawn")
    out=sys.argv[1]; rec=sys.argv[2]; cert=sys.argv[3]=="1"; TO=int(sys.argv[4]); workers=int(sys.argv[5])
    rolls=sys.argv[6:] or sorted(os.path.basename(f)[:-5] for f in glob.glob(ROOT+"/fixtures/full17_v3_sticks/*.json"))
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(workers) as ex, open(rec,"a") as f:
        for r in ex.map(lambda r: one(r,out,cert,TO), rolls):
            f.write(json.dumps(r,default=float)+"\n"); f.flush()
            print(r.get("roll"), r.get("failure") or (r.get("grid_size"), r.get("solving_flat_foldable"), r.get("shaping_flat_foldable"), round(r.get("closure_error",0),6), round(r.get("tree_similarity",0),3), r.get("total_secs")), flush=True)
