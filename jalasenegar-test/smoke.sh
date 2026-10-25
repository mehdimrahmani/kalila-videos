#!/bin/bash
# Installs the app, opens each screen, records logcat and screenshots.
set -x
O=/tmp/smoke; mkdir -p $O
APK=jalasenegar-test/app.apk
adb install -r -g $APK > $O/install.txt 2>&1
adb logcat -c
adb shell am start -W -n ir.jalasenegar/.ui.MainActivity > $O/start.txt 2>&1
sleep 8
adb exec-out screencap -p > $O/1-main.png
adb shell pidof ir.jalasenegar > $O/pid-after-start.txt
# open models screen (tap "مدیریت مدل‌ها" via activity)
adb shell am start -n ir.jalasenegar/.ui.ModelsActivity
sleep 4
adb exec-out screencap -p > $O/2-models.png
adb shell input keyevent KEYCODE_BACK
sleep 2
# start + stop a short recording through the service
adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; adb pull /sdcard/ui.xml $O/ui-main.xml >/dev/null 2>&1
B=$(python3 - <<'PY'
import re
x=open('/tmp/smoke/ui-main.xml',encoding='utf-8').read()
m=re.search(r'resource-id="ir.jalasenegar:id/btnRecord"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',x)
print(f"{(int(m[1])+int(m[3]))//2} {(int(m[2])+int(m[4]))//2}" if m else "")
PY
)
if [ -n "$B" ]; then
  adb shell input tap $B; sleep 6
  adb exec-out screencap -p > $O/3-recording.png
  adb shell input tap $B; sleep 6
  adb exec-out screencap -p > $O/4-after-stop.png
fi
adb shell pidof ir.jalasenegar > $O/pid-end.txt
adb logcat -d > $O/logcat-full.txt
adb logcat -d -b crash > $O/crash.txt
grep -E "FATAL|AndroidRuntime|ir.jalasenegar" $O/logcat-full.txt | head -200 > $O/logcat-app.txt
exit 0
