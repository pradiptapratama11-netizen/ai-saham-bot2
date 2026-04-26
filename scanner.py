import yfinance as yf
import pandas as pd
import requests
import os

from ta.trend import IchimokuIndicator
from sklearn.ensemble import RandomForestClassifier


BOT_TOKEN=os.environ["BOT_TOKEN"]
CHAT_ID=os.environ["CHAT_ID"]


def kirim(msg):

 r=requests.get(
 f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
 params={
  "chat_id":CHAT_ID,
  "text":msg
 },
 timeout=30
 )

 print(r.status_code)
 print(r.text)



stocks=pd.read_csv(
"saham_list.csv",
header=None
)[0].drop_duplicates().tolist()



def fundamental_score(stock):

 try:

  tk=yf.Ticker(stock)
  info=tk.info

  score=3

  if info.get("priceToBook",99)<3:
      score+=2

  if info.get("trailingPE",99)<22:
      score+=2

  if info.get("returnOnEquity",0)>.12:
      score+=3

  return score

 except:
  return 3



def ai_score(df):

 try:

  d=df.copy()

  d["ret"]=d.Close.pct_change()
  d["ma20"]=d.Close.rolling(20).mean()
  d["ma50"]=d.Close.rolling(50).mean()

  d=d.dropna()

  if len(d)<100:
      return .5

  X=d[
   ["Close","Volume","ma20","ma50"]
  ]

  y=(d.ret.shift(-5)>0).astype(int)

  m=RandomForestClassifier(
   n_estimators=80
  )

  m.fit(
   X[:-1],
   y[:-1]
  )

  return m.predict_proba(
   [X.iloc[-1]]
  )[0][1]

 except:
  return .5




strong=[]

print("V8 INSTITUTIONAL ENGINE...")


for s in stocks:

 try:

   df=yf.download(
    s,
    period="12mo",
    auto_adjust=True,
    progress=False
   )

   if len(df)<100:
      continue


   close=df.Close.squeeze()
   high=df.High.squeeze()
   low=df.Low.squeeze()
   vol=df.Volume.squeeze()


   alpha=0

   alpha+=fundamental_score(s)


   ichi=IchimokuIndicator(
    high,
    low
   )

   if close.iloc[-1] > ichi.ichimoku_base_line().iloc[-1]:
      alpha+=3


   rs=(
    close.iloc[-1]/
    close.iloc[-60]
   )-1

   if rs>.05:
      alpha+=3


   if vol.tail(5).mean()>vol.tail(20).mean():
      alpha+=3


   prob=ai_score(df)

   alpha+=int(prob*6)

   conf=round(
    alpha*(1+prob),
    1
   )


   if conf>=21:

      strong.append(
       (s,conf)
      )

 except:
   continue


strong=sorted(
strong,
key=lambda x:x[1],
reverse=True
)


msg="🔥 DAILY INSTITUTIONAL PICKS\n\n"

for x in strong[:5]:

 line=f"{x[0]} | Score {x[1]}"
 print(line)

 msg+=line+"\n"


kirim(msg)