#!/bin/zsh
# Builds "Drop to MD.app" into ~/Applications and a shareable zip into dist/. Needs: Xcode command line tools, uv.
set -e
cd "${0:A:h}"

# Standalone Python with markitdown, cached outside the repo: Box offloads a synced cache and the build hangs on it.
# Delete the cache folder to start over. [all] would pull a pre-release Azure package the app never calls.
PY=~/Library/Caches/droptomd/python
if [[ ! -x $PY/bin/python3 ]]; then
  uv python install 3.12 --managed-python
  mkdir -p ${PY:h}
  cp -R "$(dirname "$(dirname "$(realpath "$(uv python find 3.12 --managed-python)")")")" $PY
fi
uv pip install -q --python $PY/bin/python3 --break-system-packages \
  'markitdown[docx,outlook,pdf,pptx,xls,xlsx,audio-transcription]==0.1.7'

APP=~/Applications/"Drop to MD.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -O -o "$APP/Contents/MacOS/DropToMD" main.swift
swift icon.swift && iconutil -c icns AppIcon.iconset -o "$APP/Contents/Resources/AppIcon.icns" && rm -rf AppIcon.iconset
cp -R $PY "$APP/Contents/Resources/python"
cp mdconvert.py "$APP/Contents/Resources/"
cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>NSAppleEventsUsageDescription</key><string>Drop to MD opens Pages, Numbers and Keynote files in their app to convert them.</string>
  <key>CFBundleExecutable</key><string>DropToMD</string>
  <key>CFBundleIdentifier</key><string>se.telepathic.droptomd</string>
  <key>CFBundleName</key><string>Drop to MD</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
EOF
codesign -s - --force --deep "$APP"
mkdir -p dist && rm -f dist/DropToMD.zip
ditto -c -k --keepParent "$APP" dist/DropToMD.zip
echo "Built $APP and dist/DropToMD.zip ($(du -h dist/DropToMD.zip | cut -f1))"
