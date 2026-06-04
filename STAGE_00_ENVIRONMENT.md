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
Download OSGeo4W installer from https://trac.osgeo.org/osgeo4w
Run installer, select "Advanced Install", choose gdal package.
Add `C:\OSGeo4W\bin` to system PATH.

### Ubuntu / Debian
```
sudo apt install -y gdal-bin libgdal-dev python3-gdal
```

### macOS
```
brew install gdal
```

Verify:
```
gdal-config --version   (must show 3.x.x)
```

---

## Step 6 — Install SpatiaLite (for low-RAM deployments)

### Windows
Download mod_spatialite from https://www.gaia-gis.it/gaia-sins
Place mod_spatialite.dll in C:\Windows\System32

### Ubuntu
```
sudo apt install -y spatialite-bin libsqlite3-mod-spatialite
```

### macOS
```
brew install spatialite-tools
```

---

## Step 7 — Install PostgreSQL + PostGIS (for high-RAM deployments)

### Windows
Download PostgreSQL 15 installer from https://www.postgresql.org/download/windows
During install, open Stack Builder after completion and install PostGIS 3.4 extension.

### Ubuntu
```
sudo apt install -y postgresql-15 postgresql-15-postgis-3
sudo systemctl start postgresql
```

### macOS
```
brew install postgresql@15 postgis
brew services start postgresql@15
```

---

## Step 8 — Install Git

Download from https://git-scm.com/downloads

Verify:
```
git --version
```

---

## Step 9 — Install Tauri CLI

```
npm install -g @tauri-apps/cli@next
```

Verify:
```
tauri --version
```

---

## Step 10 — Install Playwright System Browsers

This is required for the report generation pipeline (map screenshot capture).
Run after Python is installed:

```
pip install playwright
playwright install chromium
```

---

## Step 11 — Install WeasyPrint System Dependencies

WeasyPrint requires system-level libraries for PDF rendering.

### Windows
Download and install GTK3 runtime from:
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
Add GTK bin directory to PATH.

### Ubuntu
```
sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
  libfontconfig1 libcairo2 libgdk-pixbuf2.0-0
```

### macOS
```
brew install pango libffi
```

---

## Step 12 — Set Up API Keys

Create a file named `.env` in the root of the project. Add the following keys, obtained by registering free accounts at each listed URL:

```
# NASA (register at urs.earthdata.nasa.gov)
EARTHDATA_USERNAME=
