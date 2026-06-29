import sys, time, numpy as np, pandas as pd, resource
from features import FeaturePipeline, time_split
df = pd.read_csv("../data/clean.csv", dtype={"postcode":str}, parse_dates=["date_sold"])
df["y_log"]=np.log(df["sold_price"].astype(float))
train,_,_=time_split(df,0.15)
pipe=FeaturePipeline().fit(train,train["y_log"])
dated=train[train["date_sold"].notna()].sort_values("date_sold")
val=dated.iloc[len(dated)-int(len(dated)*0.12):]; core=train.drop(val.index)
X=pipe.transform(core).to_numpy(float); y=core["y_log"].to_numpy()
from interpret.glassbox import ExplainableBoostingRegressor
cfg=eval(sys.argv[1])
t=time.time(); m=ExplainableBoostingRegressor(random_state=42,n_jobs=1,**cfg); m.fit(X,y)
print(f"OK {cfg} {time.time()-t:.1f}s maxRSS={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f}MB",flush=True)
