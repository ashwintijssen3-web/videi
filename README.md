# Tekst-naar-Video (Streamlit + MoviePy)

Een eenvoudige, lokale app om **tekst → video** te maken met automatische **Nederlandse/Engelse voice-over**, **achtergrondslides** en optionele **SRT-ondertitels**.

## 🚀 Snel starten

0) **Uitpakken**
```bash
unzip streamlit_text2video.zip
cd streamlit_text2video
```

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
streamlit run streamlit_app.py
```

4) **Gebruik**
- Plak je script (lege regel = nieuwe scene).
- Kies formaat, thema, snelheid en taal.
- Upload (optioneel) je eigen achtergronden en logo.
- Klik **Render video** → de MP4 komt in `output/` (+ SRT indien aangevinkt).

## ℹ️ Notes
- De app gebruikt **gTTS** voor spraak (internet nodig). Voor volledig offline TTS kun je later `gTTS` vervangen door bijv. `pyttsx3`.
- De fade-in/out tussen scenes zijn zachte overgangen; wil je échte crossfades, kun je per scene een overlap bouwen met MoviePy's `concatenate_videoclips(..., transition=...)`.

## 🛠️ t2v CLI voorbeeldgebruik

Na installatie van de Node-gebaseerde `t2v` CLI kun je de volgende taken uitvoeren:

```bash
unzip text2video-app.zip
cd text2video-app
npm i
npm link  # maakt 't2v' globaal beschikbaar
```

### Frames → MP4 (9:16, H.264 preset)
```bash
t2v encode-frames --frames frames/%06d.png --preset shorts_h264_1080x1920 --out out.mp4
```

### Ken Burns (afbeelding → video) met optionele audio
```bash
t2v kenburns --image input.jpg --audio voiceover.wav --duration 15 --out kb.mp4
```

### Modeloutput fixen (CFR, kleur, moov)
```bash
t2v fix-video --in model_out.mp4 --out fixed.mp4
```

### Thumbnail genereren
```bash
t2v thumbnail --in out.mp4 --out thumb.jpg
```

## Docker
```bash
docker build -t text2video .
docker run --rm -p 8501:8501 text2video
```
