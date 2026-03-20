# iOS iPad Build Guide — Step by Step

## Prerequisites
- Windows 11 PC with USB port
- iPad connected via USB cable
- Free Apple ID (no $99 developer account needed)
- GitHub repo: `construction-inspector-tracking-app`

---

## Part 1: Push Code Changes

- [ ] **1.1** Commit the iOS/Codemagic changes to your feature branch
- [ ] **1.2** Push the branch to GitHub
- [ ] **1.3** (Optional) Create a PR to merge into main — Codemagic can build from any branch

---

## Part 2: Set Up Codemagic

- [ ] **2.1** Go to [codemagic.io](https://codemagic.io) and click **Start building**
- [ ] **2.2** Sign in with your **GitHub** account
- [ ] **2.3** Authorize Codemagic to access your repositories
- [ ] **2.4** Click **Add application** and select `RobertoChavez2433/construction-inspector-tracking-app`
- [ ] **2.5** When asked about project type, select **Flutter App**
- [ ] **2.6** When asked about config, select **codemagic.yaml** (it auto-detects the file in your repo)

### Add Environment Variables

- [ ] **2.7** Go to **Settings** (gear icon) for your app in Codemagic
- [ ] **2.8** Scroll to **Environment variables** section
- [ ] **2.9** Create a new **group** named exactly: `supabase_credentials`
- [ ] **2.10** Add variable `SUPABASE_URL`:
  - Value: `https://vsqvkxvvmnnhdajtgblj.supabase.co`
  - Check **Secure** (hides value in logs)
- [ ] **2.11** Add variable `SUPABASE_ANON_KEY`:
  - Value: *(copy from your `.env` file)*
  - Check **Secure**
- [ ] **2.12** Make sure both variables are inside the `supabase_credentials` group

---

## Part 3: Trigger the Build

- [ ] **3.1** Go to your app's page in Codemagic dashboard
- [ ] **3.2** Click **Start new build**
- [ ] **3.3** Select the branch that has the `codemagic.yaml` (your feature branch or main)
- [ ] **3.4** Select workflow: **iOS Unsigned Build**
- [ ] **3.5** Click **Start new build**
- [ ] **3.6** Wait for the build to complete
  - First build: **45-70 minutes** (flusseract compiles Tesseract from C++ source)
  - Subsequent builds: **15-25 minutes** (CocoaPods cache kicks in)
- [ ] **3.7** Watch the build log for these milestones:
  1. `flutter pub get` — resolves dependencies, generates Podfile
  2. `pod install` — installs native pods including flusseract
  3. CMake Tesseract build — the longest single step (~20-40 min)
  4. `flutter build ipa --no-codesign` — produces the IPA
- [ ] **3.8** If the build succeeds, download the `.ipa` file from the **Artifacts** section

### If the Build Fails

| Error | Fix |
|-------|-----|
| `cmake: command not found` | Should not happen (we install it), but check the "Install system dependencies" step log |
| `liblzma not found` | The `brew install xz` step should handle this — check it ran |
| `No signing certificate` | Ignore — we use `--no-codesign` |
| `pod install` fails | Check if a plugin needs a higher iOS deployment target — update `ios/Podfile` min iOS version |
| Build exceeds 90 min | Free tier may be slow — retry, caching helps on second run |
| `opencv_dart` hook fails | Network issue downloading pre-built binary — retry the build |

---

## Part 4: Install on iPad (Windows + Sideloadly)

### One-Time Setup

- [ ] **4.1** Install **iTunes** from [apple.com/itunes](https://www.apple.com/itunes/)
  - **Must be the Apple website version**, NOT the Microsoft Store version
  - This installs the Apple Mobile Device drivers that Sideloadly needs
- [ ] **4.2** Install **Sideloadly** from [sideloadly.io](https://sideloadly.io/#download)
  - Download the Windows version
  - Run the installer

### Prepare iPad

- [ ] **4.3** Connect iPad to PC via USB cable
- [ ] **4.4** On iPad, tap **Trust** when prompted to trust this computer
- [ ] **4.5** Open iTunes on PC — verify iPad appears in the device list (confirms drivers work)
- [ ] **4.6** Developer Mode (iPadOS 16+ only — skip if iPadOS 15 or earlier):
  - The toggle lives at **Settings > Privacy & Security** (scroll to bottom), NOT under General
  - It may not appear until *after* you sideload an app for the first time
  - If you don't see it: sideload the IPA first (steps 4.7-4.13), then come back here
  - Toggle Developer Mode ON — iPad will restart

### Sideload the IPA

- [ ] **4.7** Open **Sideloadly**
- [ ] **4.8** Verify your iPad appears in the device dropdown (top-left)
- [ ] **4.9** Drag the downloaded `.ipa` file into the Sideloadly window (or click the IPA icon to browse)
- [ ] **4.10** Enter your **Apple ID** email in the Apple Account field
- [ ] **4.11** Click **Start**
- [ ] **4.12** Enter your Apple ID **password** when prompted
  - If you have 2FA enabled, you'll need to enter a verification code
  - Sideloadly uses this to generate a free signing certificate
- [ ] **4.13** Wait for sideloading to complete (1-3 minutes)

### Trust the App on iPad

- [ ] **4.14** On iPad: Settings > General > VPN & Device Management
- [ ] **4.15** Tap on your Apple ID email under "Developer App"
- [ ] **4.16** Tap **Trust "[your email]"**
- [ ] **4.17** Tap **Trust** to confirm
- [ ] **4.18** Open the **Field Guide** app from the home screen

---

## Part 5: Ongoing Usage

### App Expires Every 7 Days
Free Apple ID signing certificates last 7 days. When the app stops launching:

1. Connect iPad to PC
2. Open Sideloadly
3. Drag the same (or updated) `.ipa` and click Start
4. No need to re-trust — the certificate refreshes

### Rebuilding After Code Changes
1. Push changes to GitHub
2. Go to Codemagic dashboard > Start new build
3. Download new `.ipa` from artifacts
4. Sideload with Sideloadly (replaces old version, keeps app data)

### What Works Without Apple Developer Account
- All core features (entries, photos, PDF, offline mode, sync)
- Camera, location, photo library

### What Doesn't Work
- Push notifications (no APNs certificate)
- Firebase Cloud Messaging
- App Store distribution

---

## Free Tier Limits
- **Codemagic**: 500 macOS M2 minutes/month (~7-10 builds with cache)
- **Sideloadly**: Unlimited, free
- **Free Apple ID**: 7-day app expiry, max 3 sideloaded apps at once
