import time, numpy as np, pandas as pd, traceback, sys
from features import FeaturePipeline, time_split
df = pd.read_csv("../data/clean.csv", dtype={"postcode":str}, parse_dates=["date_sold"])
df["y_log"]=np.log(df["sold_price"].astype(float))
train,test,_=time_split(df,0.15)
pipe=FeaturePipeline().fit(train,train["y_log"])
dated=train[train["date_sold"].notna()].sort_values("date_sold")
val=dated.iloc[len(dated)-int(len(dated)*0.12):]; core=train.drop(val.index)
X=pipe.transform(core).to_numpy(float); y=core["y_log"].to_numpy()
print(f"core rows={len(core)} feats={X.shape[1]}", flush=True)
from interpret.glassbox import ExplainableBoostingRegressor
t=time.time()
m=ExplainableBoostingRegressor(random_state=42, interactions=6, outer_bags=6, n_jobs=1, feature_names=pipe.feature_names_)
m.fit(X,y)
print(f"OK fit {time.time()-t:.1f}s", flush=True)
