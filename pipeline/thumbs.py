import sys, os
sys.argv=[sys.argv[0]]
import make_episode as m
from PIL import Image, ImageDraw, ImageFont
m.init_assets()
SS=m.SS; W,H=m.W,m.H
def shot(real_t, box):
    tr=real_t; t=m.story(tr)
    fr=m.scene_frame(t,tr)            # SSx resolution, includes border
    x0,y0,x1,y1=[v*SS for v in box]
    im=fr.crop((x0,y0,x1,y1)).resize((W*SS,H*SS),Image.LANCZOS)
    im.alpha_composite(m.ASSETS['border'])
    return im
def label(im,text,pos,size=120,fill=(255,236,170,255)):
    f=ImageFont.truetype(m.FB,size*SS); d=ImageDraw.Draw(im)
    l,t,r,b=d.textbbox((0,0),text,font=f,stroke_width=10*SS)
    x,y=pos; x=x*SS-(r-l)//2 if x>=0 else (W*SS-(r-l))//2
    d.text((x,y*SS),text,font=f,fill=fill,stroke_width=10*SS,stroke_fill=(40,22,8,255))
def badge(im,text):
    f=ImageFont.truetype(m.FB,30*SS); d=ImageDraw.Draw(im)
    l,t,r,b=d.textbbox((0,0),text,font=f)
    pad=14*SS; x=40*SS; y=40*SS
    d.rounded_rectangle([x,y,x+r-l+2*pad,y+b-t+2*pad],radius=12*SS,fill=(28,52,99,235),outline=(212,166,60,255),width=3*SS)
    d.text((x+pad-l,y+pad-t),text,font=f,fill=(240,200,90,255))
def save(im,name):
    out=im.convert('RGB').resize((W,H),Image.LANCZOS); out.save(f'publish/{name}.png')
    out.resize((168,94),Image.LANCZOS).save(f'publish/{name}_168.png')
box=(160,268,920,695)   # 760x427 around lion + well
A=shot(48.6,box); badge(A,"KALILA & DIMNA · EP 1"); label(A,"Who's there?",(-1,545)); save(A,'thumb_primary')
B=shot(48.6,box); badge(B,"KALILA & DIMNA · EP 1"); save(B,'thumb_variant_notext')
C=shot(24.0,(60,155,1000,684)) ; badge(C,"KALILA & DIMNA · EP 1"); label(C,"Clever Hare!",(-1,90)); save(C,'thumb_variant_hare')
