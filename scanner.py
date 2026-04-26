import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np

from ta.trend import IchimokuIndicator
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

BOT_TOKEN=os.environ["BOT_TOKEN"]
CHAT_ID=os.environ["CHAT_ID"]

def kirim(msg):
    r=requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={
            "chat_id":CHAT_ID,
            "text":msg
        }
    )
    print(r.status_code)


stocks=pd.read_csv(
"saham_list.csv",
header=None
)[0].drop_duplicates().tolist()



###################################
# FUNDAMENTAL FACTOR
###################################

def factor_fundamental(stock):

    try:
        info=yf.Ticker(stock).info

        pbv=info.get("priceToBook",5)
        pe=info.get("trailingPE",30)
        roe=info.get("returnOnEquity",0)

        score=50

        if pbv<3:
            score+=15

        if pe<20:
            score+=15

        if roe>.15:
            score+=20

        return score

    except:
        return 50



###################################
# WEIGHTED ENSEMBLE
###################################

def ensemble_score(df):

    try:

        d=df.copy()

        d["ret"]=d.Close.pct_change()
        d["ma20"]=d.Close.rolling(20).mean()
        d["ma50"]=d.Close.rolling(50).mean()

        d=d.dropna()

        if len(d)<120:
            return .5


        X=d[
        ["Close","Volume","ma20","ma50"]
        ]

        y=(d.ret.shift(-5)>0).astype(int)

        Xtrain=X[:-1]
        ytrain=y[:-1]


        models=[

        RandomForestClassifier(
        n_estimators=70
        ),

        GradientBoostingClassifier(),

        LogisticRegression(
         solver="liblinear",
         max_iter=1000
        )

        ]


        weights=[.4,.35,.25]

        p=0

        for m,w in zip(
        models,
        weights
        ):

            m.fit(
             Xtrain,
             ytrain
            )

            prob=m.predict_proba(
            [X.iloc[-1]]
            )[0][1]

            p+=prob*w


        return p

    except:
        return .5




###################################
# INSTITUTIONAL ACCUMULATION
###################################

def accumulation_factor(
close,
vol
):

    s=0

    try:

      if vol.tail(5).mean() > \
      vol.tail(30).mean()*1.5:
         s+=30


      vc=close.pct_change(
      ).tail(20).std()

      if vc<0.018:
         s+=20


      rng=(
      close.tail(15).max()/
      close.tail(15).min()
      )

      if rng<1.08:
         s+=20


      return s

    except:
      return 0




###################################
# RISK
###################################

def risk_factor(close):

 try:

   vol=close.pct_change(
   ).tail(30).std()

   if vol>.045:
      return -20

   return 0

 except:
   return 0




###################################
# MAIN ENGINE
###################################

rank=[]

print(
"V10.1 INSTITUTIONAL ALPHA..."
)

for s in stocks:

 try:

   df=yf.download(
    s,
    period="12mo",
    auto_adjust=True,
    progress=False
   )

   if len(df)<120:
      continue


   close=df.Close.squeeze()
   high=df.High.squeeze()
   low=df.Low.squeeze()
   vol=df.Volume.squeeze()


   quality=factor_fundamental(
   s
   )


   ichi=IchimokuIndicator(
   high,
   low
   )

   trend=50

   if close.iloc[-1] > \
   ichi.ichimoku_base_line(
   ).iloc[-1]:
      trend=75


   rs=(
   close.iloc[-1]/
   close.iloc[-60]
   )-1


   momentum=50

   if rs>.05:
      momentum=80


   acc=accumulation_factor(
      close,
      vol
   )


   risk=risk_factor(
      close
   )


   ml=ensemble_score(
      df
   )*100



   alpha=round(

   quality*.20+
   trend*.20+
   momentum*.25+
   acc*.20+
   ml*.15+
   risk

   ,1)



   if alpha>=72:
      grade="A+"

   elif alpha>=65:
      grade="A"

   elif alpha>=58:
      grade="B"

   else:
      continue


   rank.append(
    (
     s,
     alpha,
     grade
    )
   )


 except:
   continue




rank=sorted(
rank,
key=lambda x:x[1],
reverse=True
)



###################################
# TELEGRAM A/A+ ONLY
###################################

msg="🔥 V10.1 INSTITUTIONAL BUYS\n\n"

picks=[
r for r in rank
if r[2]!="B"
][:5]


for x in picks:

 line=(
 f"{x[0]} "
 f"| Score {x[1]} "
 f"| {x[2]}"
 )

 print(line)

 msg+=line+"\n"


kirim(msg)
