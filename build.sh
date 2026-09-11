#!/bin/zsh
# Builds "Drop to MD.app" into ~/Applications and a shareable zip into dist/. Needs: Xcode command line tools, uv.
set -e
cd "${0:A:h}"

# Standalone Python with markitdown[all], built once and cached in build/. Delete build/ to refresh.
if [[ ! -x build/python/bin/python3 ]]; then
  uv python install 3.12 --managed-python
  rm -rf build && mkdir build
  cp -R "$(dirname "$(dirname "$(realpath "$(uv python find 3.12 --managed-python)")")")" build/python
  uv pip install --python build/python/bin/python3 --break-system-packages 'markitdown[all]'
fi

APP=~/Applications/"Drop to MD.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -O -o "$APP/Contents/MacOS/DropToMD" main.swift
swift icon.swift && iconutil -c icns AppIcon.iconset -o "$APP/Contents/Resources/AppIcon.icns" && rm -rf AppIcon.iconset
cp -R build/python "$APP/Contents/Resources/python"
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
