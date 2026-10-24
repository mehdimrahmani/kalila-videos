import soundfile as sf, sys, json
from kokoro_onnx import Kokoro
k=Kokoro("kokoro-v1.0.onnx","voices-v1.0.bin")
print([v for v in k.get_voices()][:60])
LINES={
 "title":("af_heart",0.92,"Kalila and Dimna. The Lion and the Hare."),
 "n1":("af_heart",0.92,"Long ago, in a green forest, there lived a big, cruel lion."),
 "n2":("af_heart",0.92,"Every day, one animal had to go to him... to become his dinner."),
 "h1":("af_sky",1.0,"Oh, great King! Another lion has stolen your lunch!"),
 "h2":("af_sky",1.0,"He is hiding in a deep well. Come, I'll show you!"),
 "n3":("af_heart",0.92,"So the clever little hare led the lion through the forest, all the way to an old well."),
 "n4":("af_heart",0.92,"The lion looked down into the water... and saw a fierce lion, staring right back at him!"),
 "n5":("af_heart",0.95,"With a mighty roar, he leapt in to fight... his own reflection!"),
 "n6":("af_heart",0.92,"And so, the little hare saved the whole forest. Because wisdom is stronger than strength."),
 "end":("af_heart",0.92,"Next time: The Monkey and the Tortoise."),
}
d={}
for key,(v,sp,txt) in LINES.items():
    a,sr=k.create(txt,voice=v,speed=sp,lang="en-us")
    sf.write(f"{key}.wav",a,sr); d[key]=round(len(a)/sr,2)
print(json.dumps(d))
