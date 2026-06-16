---
name: watchface-extract
description: Extract and decode installed Wear OS watchfaces from a connected device using ADB and apktool.
---

# Watchface Extraction

Extract any installed watchface (Watch Face Format or Canvas API) from a Wear OS device to a local directory for inspection.

## Prerequisites

- ADB binary — `${WORKSPACE}/out/host/linux-x86/bin/adb` or system `adb`
- Device connected and authorized (`adb devices`)
- `apktool` installed on host

## Quick Start

```bash
# 1. Find active watchface package
adb shell dumpsys wallpaper | grep mWallpaperComponent

# 2. Find APK path
adb shell pm path <package.name>

# 3. Pull APK
adb pull <apk_path> /tmp/watchface.apk

# 4. Decode with apktool
apktool d /tmp/watchface.apk -o ./extracted-watchface
```

## Identifying the Active Watchface

### Via wallpaper service

```bash
adb shell dumpsys wallpaper | grep -E "mWallpaperComponent|mDefaultWallpaperComponent"
```

Output example:
```
mWallpaperComponent=ComponentInfo{com.google.wear.watchface.runtime/com.google.wear.watchface.runtime.DeclarativeWatchFaceRuntime1}
```

The DeclarativeWatchFaceRuntime is the WFF renderer. Find the actual watchface package from the runtime:

```bash
adb shell dumpsys activity service com.google.wear.watchface.runtime | grep "Resource only package name"
```

### Via device policy (alternative)

```bash
adb shell dumpsys device_policy | grep -i watchface
```

### List all installed watchface packages

```bash
adb shell pm list packages | grep -iE "watchface|facer|watch"
```

## Getting the APK

```bash
# Get APK path
WFPKG=$(adb shell dumpsys activity service com.google.wear.watchface.runtime \
  | grep "Resource only package name" | awk '{print $NF}')
APKPATH=$(adb shell pm path "$WFPKG" | sed 's/package://')
adb pull "$APKPATH" /tmp/watchface.apk
```

Or manually:

```bash
adb shell pm path com.jeremysteckling.facerrel.watchfacepush.fcrhp97OzHOB5
adb pull /data/app/~~<hash>/com.example...==/base.apk /tmp/wf.apk
```

## Decoding

### Full decode with apktool (recommended)

```bash
apktool d /tmp/watchface.apk -o ./watchface-decoded
```

This produces readable `AndroidManifest.xml`, decoded `res/values/*.xml`, and decompiled resource files.

### Manual inspection

```bash
# Check format version
aapt2 dump badging /tmp/watchface.apk | grep -E "hasCode|package|label"
aapt2 dump xmltree /tmp/watchface.apk --file AndroidManifest.xml

# List resources
aapt2 dump resources /tmp/watchface.apk

# Extract raw files
unzip /tmp/watchface.apk -d ./watchface-raw
```

## Identifying Watchface Format

### Telling WFF from Canvas

| Clue | WFF (Watch Face Format) | Canvas API |
|------|------------------------|------------|
| `hasCode` | `false` | `true` |
| Property | `com.google.wear.watchface.format.version` | (absent) |
| Raw resource | `res/raw/watchface` (WFF XML) | (absent) |
| DEX files | none | `classes.dex`, `classes2.dex` |
| Runtime | `DeclarativeWatchFaceRuntime*` | Custom service |

### Canvas watchfaces

For Canvas watchfaces (Java/Kotlin, `hasCode="true"`), also decompile DEX:

```bash
apktool d /tmp/watchface.apk -o ./canvas-decoded
# smali/ directory will contain the decompiled bytecode
```

Or use `jadx` for Java source:

```bash
jadx -d ./jadx-output /tmp/watchface.apk
```

## Restoring a decoded WFF to readable project layout

After `apktool d`, the WFF structure is already clean. For raw extraction
(`unzip`), rename resources to match their resource names from `aapt2 dump resources`:

```bash
# Map obfuscated files → resource names via aapt2 dump
# Then create res/drawable/, res/font/, res/raw/ and move accordingly
```

## Examples

### Extract currently active watchface

```bash
PKG=$(adb shell dumpsys activity service com.google.wear.watchface.runtime \
  | grep "Resource only package name" | awk '{print $NF}')
APK=$(adb shell pm path "$PKG" | sed 's/package://')
NAME=$(echo "$PKG" | tr '.' '-')
adb pull "$APK" "/tmp/${NAME}.apk"
apktool d "/tmp/${NAME}.apk" -o "./${NAME}"
```

### Extract a specific package by name

```bash
PKG="com.jeremysteckling.facerrel.watchfacepush.fcrhp97OzHOB5"
APK=$(adb shell pm path "$PKG" | sed 's/package://')
adb pull "$APK" /tmp/face.apk
apktool d /tmp/face.apk -o ./face-decoded
```

## WFF File Reference

Common files inside a decoded WFF watchface:

| Path | Contents |
|------|----------|
| `AndroidManifest.xml` | Package name, `hasCode="false"`, format version property |
| `res/raw/watchface` | Main WFF layout XML (scene graph, parts, animations) |
| `res/raw/user_editable_layer` | User-configurable complications/properties (protobuf) |
| `res/xml/watch_face_info.xml` | Preview reference, editable flag |
| `res/drawable/*.png` | Background, hands, decorations, preview |
| `res/font/*.ttf` | Custom fonts |
| `res/values/strings.xml` | Theme color names, labels |
| `res/values/public.xml` | Resource ID mappings |
