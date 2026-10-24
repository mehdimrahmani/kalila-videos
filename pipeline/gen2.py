import soundfile as sf, json
from kokoro_onnx import Kokoro
k=Kokoro("kokoro-v1.0.onnx","voices-v1.0.bin")
LINES={
 "h0":("af_sky",0.95,"Oh no... today it's my turn."),
 "l1":("am_onyx",0.9,"I am the king of this forest! Bring me my dinner!"),
 "l2":("am_onyx",0.9,"Another lion? In MY forest?! Show me where he is!"),
 "l3":("am_onyx",0.95,"You there! Get out of my forest!"),
 "h3":("af_sky",1.05,"Hooray! The forest is free!"),
}
d={}
for key,(v,sp,txt) in LINES.items():
    a,sr=k.create(txt,voice=v,speed=sp,lang="en-us"); sf.write(f"{key}.wav",a,sr); d[key]=round(len(a)/sr,2)
print(json.dumps(d))
