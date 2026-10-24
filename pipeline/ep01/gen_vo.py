import soundfile as sf, json
from kokoro_onnx import Kokoro
T="/home/claude/kalila_test/tts/"
k=Kokoro(T+"kokoro-v1.0.onnx",T+"voices-v1.0.bin")
V={"K":("am_michael",0.92),"D":("am_puck",1.0),"N":("af_heart",0.92),"L":("am_onyx",0.9),
   "H":("af_sky",1.0),"E":("af_bella",0.95),"F":("am_eric",1.0),"T":("bm_george",0.82)}
LINES=[
("o1","D","Kalila, do you think a tiny hare could ever beat a big, strong lion?"),
("o2","K","A hare? Against a lion? Impossible."),
("o3","D","Then sit down, brother. Let me tell you a story."),
("n1","N","Once upon a time, there was a green and peaceful forest. The deer drank from the cool stream, the fox slept in the sun, and a little hare hopped among the flowers."),
("n2","N","But one day, a huge lion came to the forest. He was strong, and he was hungry, and he was very, very proud."),
("l1","L","I am the king of this forest! Everyone here belongs to ME!"),
("n3","N","Every day he hunted, and every day the animals ran and hid. Nobody played by the stream anymore."),
("e1","E","We can't live like this. Every day we run, every day we are afraid."),
("f1","F","Maybe we should all move far away?"),
("t1","T","This is our home, little ones. Let us go and talk to the lion."),
("t2","T","Great King, you do not need to hunt. Each day, one of us will come to you."),
("l2","L","Hmm. No running, no chasing... I like it. But if anyone is late, I will eat you ALL!"),
("n4","N","So every morning, the animals drew lots. And every day, one animal had to go."),
("h1","H","Oh no... today it's my turn."),
("h2","H","Wait. I may be small... but my brain is not! I have an idea. I'll go slowly. Very... slowly."),
("l3","L","YOU! You're late, and you're tiny! Where is my lunch?!"),
("h3","H","Oh, great King! They sent a big fat hare with me, for your lunch. But on the way, another lion stole him!"),
("l4","L","ANOTHER lion? In MY forest?! Show me where he is!"),
("h4","H","He said he's the real king, and he's hiding in a deep well. Come, I'll show you!"),
("n5","N","So the little hare led the big lion through the forest, all the way to an old, deep well."),
("h5","H","There he is, Your Majesty. Look!"),
("l5","L","You there! Get out of my forest!"),
("n6","N","The lion roared. The lion in the water roared too. So, with a mighty leap, he jumped in to fight... his own reflection!"),
("h6","H","Hooray! The forest is free!"),
("t3","T","The smallest of us has saved us all."),
("c1","K","Hmm. So the hare didn't win with strong legs, or sharp teeth..."),
("c2","D","...he won with his head! Wisdom is stronger than strength, brother."),
("c3","K","And next time: a monkey, a tortoise, and a very tricky friendship."),
]
out=[]
for key,sp,txt in LINES:
    v,s=V[sp]; a,sr=k.create(txt,voice=v,speed=s,lang="en-us"); sf.write(f"vo/{key}.wav",a,sr)
    out.append(dict(key=key,spk=sp,text=txt,dur=round(len(a)/sr,2)))
json.dump(out,open("vo/lines.json","w"),indent=1)
print(round(sum(o['dur'] for o in out),1))
