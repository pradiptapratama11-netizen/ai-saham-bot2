import yfinance as yf
import pandas as pd
import requests
import os
import numpy as np

from ta.trend import IchimokuIndicator
from sklearn.ensemble import (
RandomForestClassifier,
GradientBoostingClassifier
)

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


###################################
# 300 STOCK UNIVERSE
###################################

stocks=pd.read_csv(
"saham_list.csv",
header=None
)[0].drop_duplicates().tolist()



###################################
# FUNDAMENTAL ENGINE
###################################

def fundamental_score(stock):

 try:

   info=yf.Ticker(stock).info

   score=3

   pbv=info.get("priceToBook")
   pe=info.get("trailingPE")
   roe=info.get("returnOnEquity")

   if pbv and pbv<3:
      score+=2

   if pe and pe<20:
      score+=2

   if roe and roe>.15:
      score+=3

   return score

 except:
   return 3



###################################
# 3 MODEL ENSEMBLE
###################################

def ensemble_vote(df):

 try:

  d=df.copy()

  d["ret"]=d.Close.pct_change()
  d["ma20"]=d.Close.rolling(20).mean()
  d["ma50"]=d.Close.rolling(50).mean()

  d=d.dropna()

  if len(d)<120:
      return .5,0

  X=d[
  ["Close","Volume","ma20","ma50"]
  ]

  y=(d.ret.shift(-5)>0).astype(int)


  Xtrain=X[:-1]
  ytrain=y[:-1]


  models=[
   RandomForestClassifier(
    n_estimators=60
   ),

   GradientBoostingClassifier(),

   LogisticRegression()
  ]


  probs=[]
  votes=0

  for m in models:

      m.fit(
       Xtrain,
       ytrain
      )

      p=m.predict_proba(
       [X.iloc[-1]]
      )[0][1]

      probs.append(p)

      if p>.55:
         votes+=1


  return np.mean(probs),votes

 except:
  return .5,0



###################################
# INSTITUTIONAL ACCUMULATION
###################################

def accumulation_score(close,vol):

 score=0

 try:

   # Volume surge
   if vol.tail(5).mean() > \
      vol.tail(30).mean()*1.3:
      score+=4


   # Volatility contraction
   vr=close.pct_change().tail(
   20
   ).std()

   if vr<0.018:
      score+=3


   # Tight range breakout pressure
   if (
    close.tail(15).max()/
    close.tail(15).min()
   )<1.08:
      score+=3


   return score

 except:
   return 0




###################################
# MAIN ENGINE
###################################

strong=[]
watch=[]
avoid=[]

print(
"V9 INSTITUTIONAL ACCUMULATION..."
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


   alpha=0


   #################
   # FUNDAMENTAL
   #################

   alpha+=fundamental_score(s)



   #################
   # ICHIMOKU
   #################

   ichi=IchimokuIndicator(
    high,
    low
   )

   if close.iloc[-1] > \
   ichi.ichimoku_base_line().iloc[-1]:
      alpha+=3



   #################
   # RELATIVE STRENGTH
   #################

   rs=(
    close.iloc[-1]/
    close.iloc[-60]
   )-1

   if rs>.05:
      alpha+=3



   #################
   # ACCUMULATION
   #################

   alpha+=accumulation_score(
      close,
      vol
   )



   #################
   # ENSEMBLE AI
   #################

   prob,votes=ensemble_vote(
      df
   )

   alpha+=votes*3

   conf=round(
    alpha*(1+prob),
    1
   )



   #################
   # DISTRIBUTION AVOID
   #################

   if (
    votes==0 and
    rs<0 and
    prob<0.30
   ):
      avoid.append(
       (s,prob)
      )
      continue



   #################
   # CLASSIFY
   #################

   if conf>=24:

      strong.append(
       (
        s,
        conf,
        votes
       )
      )

   else:

      watch.append(
       (
        s,
        conf
       )
      )


 except:
   continue




strong=sorted(
strong,
key=lambda x:x[1],
reverse=True
)



###################################
# TELEGRAM SIGNAL
###################################

msg="🔥 V9 INSTITUTIONAL PICKS\n\n"

for x in strong[:7]:

 line=(
 f"{x[0]} | "
 f"Conf {x[1]} "
 f"| AI {x[2]}/3"
 )

 print(line)

 msg+=line+"\n"


kirim(msg)
