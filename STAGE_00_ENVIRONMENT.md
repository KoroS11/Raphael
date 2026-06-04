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
