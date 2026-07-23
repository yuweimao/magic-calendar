#!/usr/bin/env python3
"""Weather-in-the-bottom-band mockups. Reuses calendar_gen's palette/fonts/dither
so the output looks exactly like the 7-color ACeP panel. Renders 3 layout variants
of the day view with weather replacing the quote section, then a side-by-side sheet.
"""
import os, datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import calendar_gen as CG

CREAM=CG.CREAM; BLACK=CG.BLACK; RED=CG.RED; BLUE=CG.BLUE
GREEN=CG.GREEN; YELLOW=CG.YELLOW; ORANGE=CG.ORANGE
F=CG.F; cmix=CG.cmix; ctext=CG.ctext; stipple=CG.stipple
LSANS=CG.LSANS; LSANSB=CG.LSANSB; SERB=CG.SERB; DEJB=CG.DEJB; CJK=CG.CJK

# ---------- weather icons (bold, low-res friendly; dither handles shading) ----------
def sun(d,cx,cy,r=40,col=YELLOW,edge=ORANGE):
    for a in range(0,360,45):
        import math
        dx,dy=math.cos(math.radians(a)),math.sin(math.radians(a))
        d.line([cx+dx*(r+8),cy+dy*(r+8),cx+dx*(r+22),cy+dy*(r+22)],fill=ORANGE,width=7)
    d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=col,outline=edge,width=4)

def cloud(d,cx,cy,s=1.0,fill=CREAM,outline=BLACK):
    w=90*s; h=52*s
    d.ellipse([cx-w*0.5,cy-h*0.2,cx-w*0.5+h,cy-h*0.2+h],fill=fill,outline=outline,width=4)
    d.ellipse([cx-h*0.35,cy-h*0.55,cx-h*0.35+h*1.25,cy-h*0.55+h*1.25],fill=fill,outline=outline,width=4)
    d.ellipse([cx+w*0.5-h,cy-h*0.2,cx+w*0.5,cy-h*0.2+h],fill=fill,outline=outline,width=4)
    d.rectangle([cx-w*0.5+h*0.4,cy+h*0.1,cx+w*0.5-h*0.4,cy+h*0.5],fill=fill)

def drops(d,cx,cy,n=3,col=BLUE):
    for i in range(n):
        x=cx-20+i*20
        d.polygon([(x,cy),(x-6,cy+12),(x+6,cy+12)],fill=col)
        d.ellipse([x-6,cy+6,x+6,cy+18],fill=col)

def bolt(d,cx,cy,col=YELLOW):
    d.polygon([(cx,cy-14),(cx-12,cy+6),(cx-2,cy+6),(cx-8,cy+22),(cx+12,cy-2),(cx+2,cy-2)],
              fill=col,outline=ORANGE)

def icon(d,cx,cy,kind,scale=1.0):
    if kind=="sunny": sun(d,cx,cy,int(44*scale))
    elif kind=="partly":
        sun(d,cx-22*scale,cy-16*scale,int(30*scale))
        cloud(d,cx+8*scale,cy+8*scale,scale)
    elif kind=="cloudy": cloud(d,cx,cy,scale*1.1)
    elif kind=="rain":
        cloud(d,cx,cy-8*scale,scale); drops(d,cx,cy+26*scale,3)
    elif kind=="storm":
        cloud(d,cx,cy-8*scale,scale); bolt(d,cx,cy+22*scale)

# ---------- shared top (header + big date + weekday) reused from retro ----------
def top_retro(im,ctx):
    d=ImageDraw.Draw(im)
    d.rectangle([0,0,480,106],fill=ctx["barcolor"]); cmix(d,240,52,ctx["header"],46,CREAM,latin=SERB)
    ctext(d,240,300,ctx["day"],F(SERB,270),BLACK)
    cmix(d,240,470,ctx["weekday"],54,ctx["barcolor"],latin=SERB)
    return d

# ---------- three weather-band variants (y=560..800) ----------
def bandA(d,w):   # TODAY FOCUS: big icon left, big temp right
    stipple(d,0,560,480,800,BLUE,0.16)
    d.line([30,560,450,560],fill=BLACK,width=3)
    cmix(d,240,590,w["loc"],26,BLACK,latin=LSANSB)
    icon(d,120,710,w["kind"],1.45)
    ctext(d,335,688,f'{w["now"]}°',F(DEJB,92),BLACK)
    cmix(d,335,748,f'高 {w["hi"]}°   低 {w["lo"]}°',25,BLACK,latin=LSANSB)
    cmix(d,335,782,w["cond"],24,BLUE,latin=LSANSB)

def bandB(d,w):   # 3-DAY forecast columns
    stipple(d,0,560,480,800,BLUE,0.16)
    d.line([30,560,450,560],fill=BLACK,width=3)
    cmix(d,240,588,w["loc"],26,BLACK,latin=LSANSB)
    cols=[80,240,400]
    for cx,day in zip(cols,w["days"]):
        cmix(d,cx,626,day["wd"],27,(RED if day.get("sun") else BLACK),latin=LSANSB)
        icon(d,cx,700,day["kind"],0.8)
        cmix(d,cx,754,f'{day["hi"]}°',30,BLACK,latin=DEJB)
        cmix(d,cx,784,f'{day["lo"]}°',24,BLUE,latin=DEJB)
    for x in (160,320): d.line([x,616,x,796],fill=(200,196,182),width=2)

def bandC(d,w):   # TODAY + STATS
    stipple(d,0,560,480,800,BLUE,0.16)
    d.line([30,560,450,560],fill=BLACK,width=3)
    icon(d,115,655,w["kind"],1.25)
    ctext(d,115,745,f'{w["now"]}°',F(DEJB,60),BLACK)
    rows=[("降雨",f'{w["rain"]}%',BLUE),("高/低",f'{w["hi"]}°/{w["lo"]}°',BLACK),
          ("日出",w["sunrise"],ORANGE),("日落",w["sunset"],RED)]
    y=602
    for lab,val,col in rows:
        cmix(d,278,y,lab,26,BLACK,latin=LSANSB)
        cmix(d,415,y,val,28,col,latin=LSANSB)
        y+=48
    d.line([230,582,230,796],fill=(200,196,182),width=2)

def render(band_fn,ctx,w):
    im=Image.new("RGB",(480,800),CREAM); d=top_retro(im,ctx); band_fn(d,w)
    return CG._dither(im)

def main():
    date=datetime.date(2026,7,23)  # Thu
    ctx=CG.context(date,"zh")
    W=dict(loc="台北市", now=31, hi=33, lo=26, cond="多雲時晴",
           kind="partly", rain=20, sunrise="05:18", sunset="18:42",
           days=[dict(wd="今天",kind="partly",hi=33,lo=26),
                 dict(wd="週五",kind="rain",hi=30,lo=25),
                 dict(wd="週六",kind="sunny",hi=34,lo=27,sun=True)])
    variants=[("A  今日為主",bandA),("B  三日預報",bandB),("C  今日+統計",bandC)]
    panels=[]
    for name,fn in variants:
        p=render(fn,ctx,W); panels.append((name,p)); p.save(f"wx_{name[0]}.png")
    # comparison sheet
    scale=0.62; pw,ph=int(480*scale),int(800*scale); gap=40; top=70
    sheet=Image.new("RGB",(gap+len(panels)*(pw+gap), top+ph+30),(250,250,248))
    sd=ImageDraw.Draw(sheet); title=F(LSANSB,26); sub=F(CJK,24)
    sd.text((gap,20),"Weather in the bottom band  —  3 layouts (true panel render)",font=title,fill=(20,20,20))
    x=gap
    for name,p in panels:
        r=p.resize((pw,ph),Image.NEAREST); sheet.paste(r,(x,top))
        sd.rectangle([x,top,x+pw,top+ph],outline=(180,180,178),width=2)
        cmix(sd,x+pw//2,top+ph+16,name,24,(20,20,20),latin=LSANSB)
        x+=pw+gap
    sheet.save("weather_variants.png")
    print("wrote weather_variants.png + wx_A/B/C.png")

if __name__=="__main__": main()
