# Stage 00 — Environment Setup

## Prerequisites
None. This is the first stage.

## Objective
Install every system-level dependency required to build and run Raphael. Nothing in later stages works without completing this stage first.

---

## Step 1 — Install Node.js

Download and install Node.js v20 LTS from https://nodejs.org/en/download

Verify:
```
node --version   (must show v20.x.x)
npm --version    (must show 10.x.x)
```

---

## Step 2 — Install Python

Download and install Python 3.11 from https://www.python.org/downloads

During installation on Windows, check "Add Python to PATH".

Verify:
```
python --version   (must show 3.11.x)
pip --version
```

---

## Step 3 — Install Rust and Cargo

Run the official installer:
```
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```
Windows: Download and run https://win.rustup.rs/x86_64

Verify:
```
rustc --version   (must show 1.77 or higher)
cargo --version
```

---

## Step 4 — Install Tauri System Dependencies

### Windows
Install Microsoft C++ Build Tools from:
https://visualstudio.microsoft.com/visual-cpp-build-tools
Select "Desktop development with C++" workload during install.

Install WebView2 Runtime from:
https://developer.microsoft.com/microsoft-edge/webview2

### Ubuntu / Debian Linux
```
sudo apt update
sudo apt install -y libwebkit2gtk-4.1-dev libappindicator3-dev \
  librsvg2-dev patchelf build-essential curl wget file \
  libssl-dev libgtk-3-dev libayatana-appindicator3-dev
```

### macOS
```
xcode-select --install
```

---

## Step 5 — Install GDAL System Library

GDAL must be installed at the system level before the Python gdal package works.

### Windows
