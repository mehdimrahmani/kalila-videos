import soundfile as sf, json, sys
from kokoro_onnx import Kokoro
T="/home/claude/kalila_test/tts/"
k=Kokoro(T+"kokoro-v1.0.onnx",T+"voices-v1.0.bin")
V={"K":("am_michael",0.92),"D":("am_puck",1.0),"N":("af_heart",0.92)}
LINES=[
("d1","D","Psst! Hey, you! Yes, you! Want to hear a story?"),
("k1","K","Dimna, you can't just jump out of bushes. Introduce us first!"),
("d2","D","Oh, right. I'm Dimna, the clever one. And this is my big brother, Kalila..."),
("k2","K","...the wise one."),
("k3","K","We are two jackals from a very, very old book. It's called Kalila and Dimna."),
("d3","D","Named after us, of course."),
("n1","N","About two thousand years ago, wise storytellers in India wrote animal stories, to teach young princes how to live wisely."),
("n2","N","Then a Persian doctor named Borzuy traveled all the way to India, to bring the stories home to Persia."),
("n3","N","From Persia, the stories flew to the whole world. Into Arabic, Persian, Hebrew, Latin, Spanish, and many more languages."),
("d4","D","We're famous! We're basically the oldest cartoon stars in the world."),
("k4","K","There were no cartoons two thousand years ago, Dimna."),
("k5","K","Inside the book live clever hares, silly monkeys, brave mice, and proud lions."),
("d5","D","And every story hides a secret. A little piece of wisdom!"),
("k6","K","Like being kind, being a good friend, and thinking before you act."),
("k7","K","Every week, we'll bring you a new story from this old book."),
("d6","D","And our first one is about a tiny hare, and a very, very big lion. Guess who wins!"),
("k8","K","Come and listen. Old stories, for new friends."),
]
out=[]
for key,sp,txt in LINES:
    v,s=V[sp]; a,sr=k.create(txt,voice=v,speed=s,lang="en-us"); sf.write(f"vo/{key}.wav",a,sr)
    out.append(dict(key=key,spk=sp,text=txt,dur=round(len(a)/sr,2)))
json.dump(out,open("vo/lines.json","w"),indent=1)
print(sum(o['dur'] for o in out), [(o['key'],o['dur']) for o in out])
