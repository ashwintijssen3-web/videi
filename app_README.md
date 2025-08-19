# Tekst-naar-Video (Streamlit + MoviePy)

Een eenvoudige, lokale app om **tekst → video** te maken met automatische **Nederlandse/Engelse voice-over**, **achtergrondslides** en optionele **SRT-ondertitels**.

## 🚀 Snel starten

1) **Vereisten**
   - Python 3.10+
   - ffmpeg beschikbaar in je PATH

   macOS (Homebrew): `brew install ffmpeg`  
   Ubuntu/Debian: `sudo apt-get install ffmpeg`  
   Windows (winget): `winget install Gyan.FFmpeg` (of download van ffmpeg.org en voeg toe aan PATH)

2) **Installeer**
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

3) **Run**
```bash
streamlit run app.py
```

4) **Gebruik**
- Plak je script (lege regel = nieuwe scene).
- Kies formaat, thema, snelheid en taal.
- Upload (optioneel) je eigen achtergronden en logo.
- Klik **Render video** → de MP4 komt in `output/` (+ SRT indien aangevinkt).

## ℹ️ Notes
- De app gebruikt **gTTS** voor spraak (internet nodig). Voor volledig offline TTS kun je later `gTTS` vervangen door bijv. `pyttsx3`.
- De fade-in/out tussen scenes zijn zachte overgangen; wil je échte crossfades, kun je per scene een overlap bouwen met MoviePy's `concatenate_videoclips(..., transition=...)`.
- De ingestelde **stem-snelheid** gebruikt ffmpeg's `atempo` filter zodat de toonhoogte gelijk blijft.
