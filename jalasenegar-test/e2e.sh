#!/bin/bash
# End-to-end: in-app model download -> transcription -> minutes, on the emulator.
set -x
O=/tmp/smoke; mkdir -p $O
P=ir.jalasenegar
D=/sdcard/Android/data/$P/files
tapid() {  # tap a view by resource id
  adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; adb pull /sdcard/ui.xml $O/ui.xml >/dev/null 2>&1
  local B=$(python3 -c "
import re,sys
x=open('$O/ui.xml',encoding='utf-8').read()
m=re.search(r'resource-id=\"$P:id/$1\"[^>]*bounds=\"\[(\d+),(\d+)\]\[(\d+),(\d+)\]\"',x)
print(f'{(int(m[1])+int(m[3]))//2} {(int(m[2])+int(m[4]))//2}' if m else '')")
  [ -n "$B" ] && adb shell input tap $B
  echo "tap $1 -> $B"
}
adb install -r -g jalasenegar-test/app.apk > $O/install.txt 2>&1
adb shell pm grant $P android.permission.POST_NOTIFICATIONS
adb logcat -c
adb shell am start -W -n $P/.ui.MainActivity
sleep 6
tapid btnDlFull
sleep 20; adb exec-out screencap -p > $O/1-downloading.png
# wait for models (max 25 min)
for i in $(seq 1 150); do
  n=$(adb shell ls $D/models 2>/dev/null | grep -c -E '^(whisper-encoder.onnx|whisper-decoder.onnx|whisper-tokens.txt|segmentation.onnx|speaker-embedding.onnx|llm.litertlm)$')
  [ "$n" = "6" ] && break; sleep 10
done
adb shell ls -l $D/models > $O/models.txt
adb exec-out screencap -p > $O/2-models-done.png
# import the test recording the way a user would: share it to the app
# (a messenger app would grant access to its file; here the file is placed in the app's own folder)
adb shell mkdir -p $D/test
adb push jalasenegar-test/meeting.wav $D/test/meeting.wav
adb shell am start -a android.intent.action.SEND -t audio/wav \
  --eu android.intent.extra.STREAM file://$D/test/meeting.wav -n $P/.ui.MainActivity > $O/session-setup.txt 2>&1
for i in $(seq 1 90); do adb shell "cat $D/sessions/*/session.json" 2>/dev/null | grep -q '"t":' && break; sleep 10; done
sleep 5; adb exec-out screencap -p > $O/3-transcribed.png
sleep 2
tapid btnMinutes
for i in $(seq 1 120); do adb shell "cat $D/sessions/*/session.json" | grep -q '"minutes": "#' && break; sleep 10; done
sleep 5; adb exec-out screencap -p > $O/4-minutes.png
mkdir -p $O/session
adb shell "ls -l $D/sessions/*" > $O/session/ls.txt 2>&1
adb pull $D/sessions $O/session/ >/dev/null 2>&1
adb logcat -d > $O/logcat-full.txt
adb logcat -d -b crash > $O/crash.txt
exit 0
