import time, numpy as np, pandas as pd, traceback
from features import FeaturePipeline, time_split
df = pd.read_csv("../data/clean.csv", dtype={"postcode":str}, parse_dates=["date_sold"])
df["y_log"]=np.log(df["sold_price"].astype(float))
train,test,_=time_split(df,0.15)
pipe=FeaturePipeline().fit(train,train["y_log"])
sub=train.iloc[:6000]
X=pipe.transform(sub).to_numpy(float); y=sub["y_log"].to_numpy()
from interpret.glassbox import ExplainableBoostingRegressor
for cfg in [dict(n_jobs=1,outer_bags=6,interactions=6)]:
    try:
        t=time.time()
        m=ExplainableBoostingRegressor(random_state=42, **cfg)
        m.fit(X,y)
        print("OK", cfg, f"{time.time()-t:.1f}s rows={len(sub)} pred={np.exp(m.predict(X[:2]))}")
    except Exception:
        traceback.print_exc()
