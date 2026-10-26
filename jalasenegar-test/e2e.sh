#!/bin/bash
# End-to-end on the emulator: share a recording -> pick speaker count -> transcription -> minutes.
# The emulator APK has no bundled models; they are pushed to the app's files/models folder instead.
set -x
O=/tmp/smoke; mkdir -p $O
P=ir.jalasenegar
D=/sdcard/Android/data/$P/files
M=https://github.com/mehdimrahmani/kalila-videos/releases/download/jalasenegar-models-v1
dump() { adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; adb pull /sdcard/ui.xml $O/ui.xml >/dev/null 2>&1; }
tapre() {  # tap first node whose resource-id or text matches regex $1
  dump
  local B=$(python3 - "$1" <<'PY'
import re,sys
x=open('/tmp/smoke/ui.xml',encoding='utf-8').read()
for n in re.finditer(r'<node [^>]*>',x):
    t=n.group(0)
    rid=re.search(r'resource-id="([^"]*)"',t).group(1); txt=re.search(r' text="([^"]*)"',t).group(1)
    if re.search(sys.argv[1],rid) or re.search(sys.argv[1],txt):
        m=re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',t)
        print(f"{(int(m[1])+int(m[3]))//2} {(int(m[2])+int(m[4]))//2}"); break
PY
)
  [ -n "$B" ] && adb shell input tap $B
  echo "tap '$1' -> $B"
}
mkdir -p /tmp/models
for f in whisper-encoder.onnx whisper-decoder.onnx whisper-tokens.txt segmentation.onnx speaker-embedding.onnx; do
  curl -sSfL -o /tmp/models/$f $M/$f
done
adb install -r -g jalasenegar-test/app.apk > $O/install.txt 2>&1
adb shell pm grant $P android.permission.POST_NOTIFICATIONS
adb shell am start -W -n $P/.ui.MainActivity
sleep 5
adb exec-out screencap -p > $O/1-main.png
adb shell mkdir -p $D/models $D/test
for f in /tmp/models/*; do adb push $f $D/models/ >/dev/null; done
adb shell ls -l $D/models > $O/models.txt
adb logcat -c
adb push jalasenegar-test/meeting.wav $D/test/meeting.wav
adb shell am start -a android.intent.action.SEND -t audio/wav \
  --eu android.intent.extra.STREAM file://$D/test/meeting.wav -n $P/.ui.MainActivity > $O/session-setup.txt 2>&1
sleep 15
adb exec-out screencap -p > $O/2-ask-speakers.png
tapre '^۳ نفر$'
for i in $(seq 1 90); do adb shell "cat $D/sessions/*/session.json" 2>/dev/null | grep -q '"t":' && break; sleep 10; done
sleep 5; adb exec-out screencap -p > $O/3-transcribed.png
# mark the first paragraph as a decision via the dialog
dump; cp $O/ui.xml $O/ui-session.xml
adb shell input swipe 160 550 160 120 400; sleep 1
adb exec-out screencap -p > $O/3b-paragraphs.png
tapre '^.?\[۰۰:'
sleep 2; adb exec-out screencap -p > $O/4-note-dialog.png
tapre 'rbDecision'
tapre '^ذخیره$'
sleep 2
adb exec-out screencap -p > $O/4b-tagged.png
for k in 1 2 3; do adb shell input swipe 160 150 160 600 300; done; sleep 1
tapre 'btnMinutes'
sleep 2; tapre '^بله، بساز$'
sleep 3; adb exec-out screencap -p > $O/5-share.png
mkdir -p $O/session
adb shell "ls -l $D/sessions/*" > $O/session/ls.txt 2>&1
adb pull $D/sessions $O/session/ >/dev/null 2>&1
adb logcat -d > $O/logcat-full.txt
adb logcat -d -b crash > $O/crash.txt
exit 0
