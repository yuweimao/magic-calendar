#!/usr/bin/env python3
"""Portable Magic Calendar image generator.
Renders the day view for a date/theme/language, dithers to the panel's 7 colors,
and returns the packed 800x480 buffer (192000 bytes) ready for the device.

Fonts are bundled in ./fonts so this runs identically on macOS / Linux / a Pi / cloud.
Requires: pillow, numpy   (pip install pillow numpy)
"""
import os, datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
def fp(n): return os.path.join(FONT_DIR, n)
LSANS=fp("LiberationSans-Regular.ttf"); LSANSB=fp("LiberationSans-Bold.ttf")
SERB=fp("LiberationSerif-Bold.ttf"); SERI=fp("LiberationSerif-Italic.ttf"); SER=fp("LiberationSerif-Regular.ttf")
DEJB=fp("DejaVuSans-Bold.ttf"); CJK=fp("DroidSansFallbackFull.ttf")

CREAM=(244,241,231); BLACK=(26,26,26); RED=(178,58,46); BLUE=(52,83,143)
GREEN=(76,122,63); YELLOW=(227,201,63); ORANGE=(213,127,51)
PAL=np.array([BLACK,CREAM,RED,BLUE,GREEN,YELLOW,ORANGE],float)
NUMY,WKY=330,500

WD={"en":["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"],
    "zh":["星期一","星期二","星期三","星期四","星期五","星期六","星期日"],
    "ja":["月曜日","火曜日","水曜日","木曜日","金曜日","土曜日","日曜日"]}
QUOTES={"zh":[("千里之行，始于足下。","—— 老子"),("学而时习之，不亦说乎。","—— 孔子"),
              ("天行健，君子以自强不息。","—— 周易")],
        "en":[("A journey of a thousand miles begins with a single step.","— Lao Tzu"),
              ("Well begun is half done.","— Aristotle"),
              ("The obstacle is the way.","— Marcus Aurelius")],
        "ja":[("千里の道も一歩から。","—— 老子"),("継続は力なり。","—— 諺"),
              ("七転び八起き。","—— 諺")]}
DOT={'0':["01110","10001","10011","10101","11001","10001","01110"],
'1':["00100","01100","00100","00100","00100","00100","01110"],
'2':["01110","10001","00001","00010","00100","01000","11111"],
'3':["11111","00010","00100","00010","00001","10001","01110"],
'4':["00010","00110","01010","10010","11111","00010","00010"],
'5':["11111","10000","11110","00001","00001","10001","01110"],
'6':["00110","01000","10000","11110","10001","10001","01110"],
'7':["11111","00001","00010","00100","01000","01000","01000"],
'8':["01110","10001","10001","01110","10001","10001","01110"],
'9':["01110","10001","10001","01111","00001","00010","01100"]}

def F(p,s): return ImageFont.truetype(p,s)
def cmix(d,cx,ym,s,size,fill,latin=LSANSB):
    fl=F(latin,size); fc=F(CJK,size); m=[]
    for ch in s:
        f=fl if ord(ch)<0x2E80 else fc
        if m and m[-1][1] is f: m[-1][0]+=ch
        else: m.append([ch,f])
    ws=[d.textlength(t,font=f) for t,f in m]; x=cx-sum(ws)/2
    for (t,f),w in zip(m,ws): d.text((x,ym),t,font=f,fill=fill,anchor="lm"); x+=w
def ctext(d,cx,y,s,font,fill): d.text((cx,y),s,font=font,fill=fill,anchor="mm")
def stipple(d,x0,y0,x1,y1,color,density=0.30):
    B=[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]; thr=density*16
    for y in range(y0,y1):
        row=B[y&3]
        for x in range(x0,x1):
            if row[x&3] < thr: d.point((x,y),fill=color)
def dots_num(d,cx,cy,day,col,sp=34,r=15):
    cw=5*sp; gap=sp; tot=len(day)*cw+(len(day)-1)*gap; x=cx-tot/2; top=cy-3.5*sp
    for ch in day:
        for ry,row in enumerate(DOT[ch]):
            for ci,b in enumerate(row):
                if b=='1':
                    dx=x+ci*sp+sp/2; dy=top+ry*sp+sp/2; d.ellipse([dx-r,dy-r,dx+r,dy+r],fill=col)
        x+=cw+gap
def patt_num(im,cx,cy,day,size=300):
    import random
    pats=["dots","stripes"]; parts=[]
    for k,ch in enumerate(day):
        f=F(DEJB,size); bb=f.getbbox(ch); w=bb[2]-bb[0]; h=bb[3]-bb[1]; pad=2; W=w+2*pad; H=h+2*pad
        mask=Image.new("L",(W,H),0); ImageDraw.Draw(mask).text((pad-bb[0],pad-bb[1]),ch,font=f,fill=255)
        fill=Image.new("RGB",(W,H),BLACK); fd=ImageDraw.Draw(fill); rnd=random.Random(7+k)
        if pats[k%2]=="dots":
            spc=int(size*0.115); r0=size*0.030
            for yy in range(0,H+spc,spc):
                for xx in range(0,W+spc,spc):
                    jx=xx+spc/2+rnd.randint(-spc//5,spc//5); jy=yy+spc/2+rnd.randint(-spc//5,spc//5)
                    rad=r0*rnd.uniform(0.65,1.3); fd.ellipse([jx-rad,jy-rad,jx+rad,jy+rad],fill=CREAM)
        else:
            spc=int(size*0.060); th=max(2,int(size*0.024)); y=2
            while y<H: yj=y+rnd.randint(-1,2); fd.rectangle([0,yj,W,yj+th],fill=CREAM); y+=spc
        parts.append((fill,mask,W,H))
    gap=4; totw=sum(p[2] for p in parts)+gap*(len(parts)-1); x=int(cx-totw/2)
    for fill,mask,W,H in parts: im.paste(fill,(x,int(cy-H/2)),mask); x+=W+gap

# ---- weather icons + bottom-band layouts (used when bottom mode == "weather") ----
def _sun(d,cx,cy,r=40):
    import math
    for a in range(0,360,45):
        dx,dy=math.cos(math.radians(a)),math.sin(math.radians(a))
        d.line([cx+dx*(r+8),cy+dy*(r+8),cx+dx*(r+22),cy+dy*(r+22)],fill=ORANGE,width=7)
    d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=YELLOW,outline=ORANGE,width=4)
def _cloud(d,cx,cy,s=1.0,fill=CREAM,outline=BLACK):
    w=90*s; h=52*s
    d.ellipse([cx-w*0.5,cy-h*0.2,cx-w*0.5+h,cy-h*0.2+h],fill=fill,outline=outline,width=4)
    d.ellipse([cx-h*0.35,cy-h*0.55,cx-h*0.35+h*1.25,cy-h*0.55+h*1.25],fill=fill,outline=outline,width=4)
    d.ellipse([cx+w*0.5-h,cy-h*0.2,cx+w*0.5,cy-h*0.2+h],fill=fill,outline=outline,width=4)
    d.rectangle([cx-w*0.5+h*0.4,cy+h*0.1,cx+w*0.5-h*0.4,cy+h*0.5],fill=fill)
def _drops(d,cx,cy,n=3):
    for i in range(n):
        x=cx-20+i*20
        d.polygon([(x,cy),(x-6,cy+12),(x+6,cy+12)],fill=BLUE); d.ellipse([x-6,cy+6,x+6,cy+18],fill=BLUE)
def _bolt(d,cx,cy):
    d.polygon([(cx,cy-14),(cx-12,cy+6),(cx-2,cy+6),(cx-8,cy+22),(cx+12,cy-2),(cx+2,cy-2)],fill=YELLOW,outline=ORANGE)
def wicon(d,cx,cy,kind,scale=1.0,dark=False):
    # on a colored card (dark=True): clouds get cream fill + blue outline, drops cream
    cf=CREAM; co=(BLUE if dark else BLACK); dc=(CREAM if dark else BLUE)
    def cl(x,y,s): _cloud(d,x,y,s,fill=cf,outline=co)
    def dr(x,y):
        for i in range(3):
            xx=x-20+i*20
            d.polygon([(xx,y),(xx-6,y+12),(xx+6,y+12)],fill=dc); d.ellipse([xx-6,y+6,xx+6,y+18],fill=dc)
    if kind=="sunny": _sun(d,cx,cy,int(44*scale))
    elif kind=="partly": _sun(d,cx-22*scale,cy-16*scale,int(30*scale)); cl(cx+8*scale,cy+8*scale,scale)
    elif kind=="cloudy": cl(cx,cy,scale*1.1)
    elif kind=="rain": cl(cx,cy-8*scale,scale); dr(cx,cy+26*scale)
    elif kind=="storm": cl(cx,cy-8*scale,scale); _bolt(d,cx,cy+22*scale)

# Dynamic sky color: stormy=ink, golden hour=orange, otherwise daytime blue.
def _hm(date, s):
    try:
        h,m=map(int,s.split(":")); return datetime.datetime(date.year,date.month,date.day,h,m)
    except Exception: return None
def sky_palette(kind, now_dt=None, date=None, sunrise="", sunset=""):
    if kind in ("rain","storm"): return BLACK, CREAM, YELLOW          # stormy sky
    if now_dt and date:                                              # golden hour
        for t in (_hm(date,sunrise), _hm(date,sunset)):
            if t and abs((now_dt-t).total_seconds())<=45*60:
                return ORANGE, CREAM, BLACK                          # sunrise/sunset
    return BLUE, CREAM, YELLOW                                        # daytime sky

# Sky mood from condition. Scatter pixels RANDOMLY (not on a 4x4 lattice) so the
# background reads as fine natural noise instead of a coarse repeating grid.
# No native grey in the 7-color palette, so cloud/rain use sparse black = grey.
import random as _rnd
def _noise(d,color,p,y0=560,y1=800,seed=42):
    r=_rnd.Random(seed)
    for y in range(y0,y1):
        for x in range(480):
            if r.random()<p: d.point((x,y),fill=color)
def sky_bg(d,kind):
    if kind=="sunny":    _noise(d,BLUE,0.16)
    elif kind=="partly": _noise(d,BLUE,0.10)
    elif kind=="cloudy": _noise(d,BLACK,0.07)
    elif kind=="rain":   _noise(d,BLACK,0.08,seed=7); _noise(d,BLUE,0.04,seed=9)
    elif kind=="storm":  _noise(d,BLACK,0.11)
    else:                _noise(d,BLUE,0.10)

def band_today(d,w,lang,now_dt=None,date=None):   # variant A: dynamic sky card
    bg,tx,ac=sky_palette(w["kind"],now_dt,date,w.get("sunrise",""),w.get("sunset","")); dark=True
    d.rectangle([0,560,480,800],fill=bg)
    cmix(d,240,586,w["loc"],22,tx,latin=LSANSB)
    wicon(d,100,706,w["kind"],1.45,dark)
    ctext(d,352,684,f'{w["now"]}°',F(DEJB,92),tx)
    hl=(f'高 {w["hi"]}°   低 {w["lo"]}°' if lang=="zh" else f'H {w["hi"]}°   L {w["lo"]}°')
    cmix(d,352,742,hl,25,tx,latin=LSANSB)
    cmix(d,352,776,w["cond"],24,ac,latin=LSANSB)

def band_3day(d,w,lang,now_dt=None,date=None):    # variant B: dynamic sky card
    bg,tx,ac=sky_palette(w["days"][0]["kind"],now_dt,date,w.get("sunrise",""),w.get("sunset","")); dark=True
    d.rectangle([0,560,480,800],fill=bg)
    cmix(d,240,584,w["loc"],22,tx,latin=LSANSB)
    for cx,day in zip([80,240,400], w["days"][:3]):
        cmix(d,cx,620,day["wd"],27,tx,latin=LSANSB)
        wicon(d,cx,688,day["kind"],0.8,dark)
        cmix(d,cx,752,f'{day["hi"]}°',30,tx,latin=DEJB)
        cmix(d,cx,780,f'{day["lo"]}°',24,ac,latin=DEJB)
    for x in (160,320): d.line([x,612,x,786],fill=(90,120,175),width=2)

# --- alert band (replaces the weather section for warnings) ---
def _batt_icon(d,cx,cy,col):
    w,h=104,54
    d.rectangle([cx-w/2,cy-h/2,cx+w/2,cy+h/2],outline=col,width=6)
    d.rectangle([cx+w/2,cy-13,cx+w/2+11,cy+13],fill=col)            # + terminal
    d.rectangle([cx-w/2+9,cy-h/2+9,cx-w/2+25,cy+h/2-9],fill=col)    # low charge bar
def _warn_icon(d,cx,cy,col):
    d.polygon([(cx,cy-42),(cx-46,cy+34),(cx+46,cy+34)],outline=col,width=6)
    d.rectangle([cx-4,cy-16,cx+4,cy+12],fill=col)                   # !
    d.ellipse([cx-5,cy+20,cx+6,cy+31],fill=col)
def band_alert(d,al,lang):
    kind=al.get("kind","low")
    bg = RED if kind=="critical" else ORANGE
    d.rectangle([0,560,480,800],fill=bg)
    (_warn_icon if kind=="critical" else _batt_icon)(d,108,688,CREAM)
    cmix(d,300,668,al.get("title",""),32,CREAM,latin=LSANSB)
    cmix(d,300,714,al.get("sub",""),25,CREAM,latin=LSANSB)

def _render(theme,ctx):
    im=Image.new("RGB",(480,800),CREAM); d=ImageDraw.Draw(im)
    wc=ctx["wcolor"]; day=ctx["day"]
    # header
    if theme=="retro":
        d.rectangle([0,0,480,106],fill=ctx["barcolor"]); cmix(d,240,52,ctx["header"],46,CREAM,latin=SERB)
    elif theme=="mono":
        d.rectangle([0,0,480,98],fill=BLACK); cmix(d,240,46,ctx["header"],32,CREAM)
    else:
        cmix(d,240,58,ctx["header"],30,BLACK); d.line([60,92,420,92],fill=(212,207,192),width=1)
    # number
    if theme=="dots": dots_num(d,240,NUMY,day,wc)
    elif theme=="diy": patt_num(im,240,NUMY,day); d=ImageDraw.Draw(im)
    elif theme=="retro": ctext(d,240,NUMY,day,F(SERB,300),BLACK)
    else: ctext(d,240,NUMY,day,F(DEJB,300),BLACK)
    # weekday
    if theme=="retro": wcol=ctx["barcolor"]; wf=SERB
    elif theme=="mono": wcol=BLACK; wf=LSANSB
    else: wcol=wc; wf=LSANSB
    cmix(d,240,WKY,ctx["weekday"],54,wcol,latin=wf)
    # bottom band: an alert takes over the whole section; else weather; else quote
    al=ctx.get("alert")
    w=ctx.get("weather")
    if al:
        band_alert(d,al,ctx["lang"])
    elif w:
        fn=band_3day if ctx.get("wx_layout","3day")=="3day" else band_today
        fn(d,w,ctx["lang"],ctx.get("now_dt"),ctx.get("date"))
    else:
        stipple(d,0,600,480,800,BLUE,0.30)
        cmix(d,240,686,ctx["quote"],34,BLACK,latin=LSANS)
        cmix(d,240,724,ctx["author"],24,BLACK,latin=LSANS)
    return im

def _dither(im,spread=95):
    a=np.asarray(im).astype(float); H,W,_=a.shape
    b=np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]])/16.0-0.5
    t=np.tile(b,((H+3)//4,(W+3)//4))[:H,:W]*spread
    a=a+t[...,None]; diff=a[:,:,None,:]-PAL[None,None,:,:]
    return Image.fromarray(PAL[diff.__pow__(2).sum(3).argmin(2)].astype(np.uint8))

IDX={(26,26,26):0,(244,241,231):1,(178,58,46):4,(52,83,143):3,(76,122,63):2,(227,201,63):5,(213,127,51):6}
def _pack(land):
    px=land.load(); data=bytearray()
    for i in range(480):
        for j in range(400):
            data.append((IDX[px[2*j,i]]<<4)|IDX[px[2*j+1,i]])
    return bytes(data)

def context(date,lang,weather=None,wx_layout="3day",now_dt=None,alert=None):
    wi=date.weekday()  # Mon=0..Sun=6
    if lang=="en": header=date.strftime("%B %Y")
    elif lang=="ja": header=f"{date.year}年{date.month}月"
    else: header=f"{date.year} 年 {date.month} 月"
    q=QUOTES[lang][date.timetuple().tm_yday % len(QUOTES[lang])]
    return dict(day=str(date.day), weekday=WD[lang][wi],
                wcolor=(RED if wi==6 else (BLUE if wi==5 else BLACK)),
                barcolor=(RED if wi==6 else (GREEN if wi==5 else BLACK)),
                header=header, quote=q[0], author=q[1], lang=lang,
                weather=weather, wx_layout=wx_layout, now_dt=now_dt, date=date,
                alert=alert)

def generate(theme="retro", lang="zh", date=None, preview_path=None,
             weather=None, wx_layout="3day", now_dt=None, alert=None):
    """Return packed 192000-byte buffer for the given date (default: today).
    If weather is a dict, the bottom band shows weather instead of the quote.
    now_dt (default: now) drives the golden-hour orange sky near sunrise/sunset.
    alert: optional dict {kind: 'low'|'critical', title, sub} -> the bottom band
    becomes a full-width warning card (battery icon / warning triangle + message)."""
    date = date or datetime.date.today()
    now_dt = now_dt or datetime.datetime.now()
    raw = _render(theme, context(date, lang, weather, wx_layout, now_dt, alert))
    im = _dither(raw)                                  # spread dither (nice date edges)
    if weather or alert:                               # crisp solid bottom card
        band = _dither(raw.crop((0,560,480,800)), spread=0)
        im.paste(band, (0,560))
    if preview_path: im.save(preview_path)
    return _pack(im.transpose(Image.ROTATE_90))

if __name__ == "__main__":
    import sys
    th=sys.argv[1] if len(sys.argv)>1 else "retro"
    lg=sys.argv[2] if len(sys.argv)>2 else "zh"
    data=generate(th,lg,preview_path="preview.png")
    open(f"cal_{th}.bin","wb").write(data)
    print(f"wrote cal_{th}.bin ({len(data)} bytes) + preview.png for {datetime.date.today()}")
