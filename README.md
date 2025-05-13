# ♟️ FENVision AI – Live AI Chess Assistant

A desktop app that visually reads your screen’s chess board, detects the current position using my custom AI, and suggests the best move using Stockfish.

---

## 📦 How to Set Up (Windows)

### 1. Install Python 3.10 (if you don’t have it)

- Download from: https://www.python.org/downloads/release/python-3100/
- Windows Direct Download: https://www.python.org/ftp/python/3.10.0/python-3.10.0-amd64.exe
- During python setup, **check the box that says “Add Python to PATH”**

### 2. Add Stockfish

- Go to https://stockfishchess.org/download/
- Download the Windows version (e.g. `stockfish_15_x64.exe`)
- Rename it to: `stockfish.exe`
- Place it in this same folder

### 3. Install Dependencies

- Double-click this file:

```
setup.bat
```

### 4. Run the App

Double-click this file:

```
run_app.bat
```

---

## ⚙️ Features

- Auto/manual screen detection
- Mirrors current board and FEN display
- Suggests best move using Stockfish
- Evaluation bar, custom move depth (for analysis), and color/side toggle (White/Black)

---

## 🧠 AI Model Info

- Model file: `ccn_model_{name}.pth`
- Based on my custom Convolutional Chess Network (CCN)

---

## ❗ Notes

- This is a desktop utility. It doesn’t play moves automatically (yet).
- The downloaded version has the ability to work with any digital chess board (Chess.com, Lichess, etc.)
- Different chess board styles require different models. You can train your own model by downloading my open-source AI model.
- This is the same model I used to make the models you find inside the downloaded folder.
