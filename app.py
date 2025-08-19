import os
import io
import math
import uuid
import textwrap
from dataclasses import dataclass
from typing import List, Optional, Tuple

import streamlit as st
from gtts import gTTS
from pydub import AudioSegment
from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    CompositeVideoClip,
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ---------------------------
# Helpers & dataclasses
# ---------------------------

@dataclass
class Scene:
    text: str
    bg_image_path: Optional[str]
    audio_path: str
    duration: float  # seconds

@dataclass
class Settings:
    resolution: Tuple[int, int]
    theme: str
    padding_px: int
    font_path: Optional[str]
    font_size_pct: float
    text_box_opacity: int  # 0-255
    line_spacing: float
    speed: float  # playback speed factor for voice (audio time stretch)

THEMES = {
    "Donker": [(15, 23, 42), (30, 41, 59)],
    "Licht": [(245, 246, 248), (225, 229, 235)],
    "Aardetint": [(39, 57, 47), (98, 125, 103)],
    "Paars": [(45, 23, 66), (109, 74, 147)],
    "Sunset": [(255, 94, 98), (255, 195, 113)],
}

ASPECTS = {
    "16:9 (1920x1080)": (1920, 1080),
    "9:16 (1080x1920)": (1080, 1920),
    "1:1 (1080x1080)": (1080, 1080),
}

OUTPUT_DIR = "output"
TEMP_DIR = "tmp"
FONTS_TRY = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


def find_font(custom_path: Optional[str]) -> Optional[str]:
    if custom_path and os.path.exists(custom_path):
        return custom_path
    for p in FONTS_TRY:
        if os.path.exists(p):
            return p
    return None


def split_script(text: str) -> List[str]:
    # Split op lege regels; als niet aanwezig: op zinnen
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    if blocks:
        return blocks
    # fallback: grove zin-splitsing
    rough = []
    buf = []
    for part in text.replace("?", ".").replace("!", ".").split("."):
        t = part.strip()
        if not t:
            continue
        buf.append(t)
        if len(" ".join(buf).split()) >= 18:
            rough.append(". ".join(buf) + ".")
            buf = []
    if buf:
        rough.append(". ".join(buf) + ".")
    return rough


def tts_to_mp3(text: str, lang: str = "nl") -> Tuple[str, float]:
    """Synthesize TTS to an mp3 temp file. Returns (path, duration_sec)."""
    mp3_path = os.path.join(TEMP_DIR, f"tts_{uuid.uuid4().hex}.mp3")
    try:
        tts = gTTS(text=text, lang=lang)
        tts.save(mp3_path)
    except Exception as e:
        raise RuntimeError("TTS mislukt (gTTS heeft internet nodig).") from e
    audio = AudioSegment.from_file(mp3_path)
    duration = audio.duration_seconds
    return mp3_path, duration


def change_speed(input_path: str, speed: float) -> Tuple[str, float]:
    # Naive timestretch via sample rate trick (pitch verandert iets)
    audio = AudioSegment.from_file(input_path)
    if abs(speed - 1.0) < 1e-3:
        return input_path, audio.duration_seconds
    new_frame_rate = int(audio.frame_rate * speed)
    sped = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate}).set_frame_rate(audio.frame_rate)
    out_path = os.path.join(TEMP_DIR, f"tts_speed_{uuid.uuid4().hex}.mp3")
    sped.export(out_path, format="mp3")
    return out_path, AudioSegment.from_file(out_path).duration_seconds


def make_gradient_bg(size: Tuple[int, int], theme: str) -> Image.Image:
    w, h = size
    c1, c2 = THEMES.get(theme, THEMES["Donker"])  # two RGB tuples
    # vertical gradient
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        arr[y, :, :] = (r, g, b)
    return Image.fromarray(arr)


def draw_text_block(
    base: Image.Image,
    text: str,
    padding_px: int,
    font_path: Optional[str],
    font_size_pct: float,
    line_spacing: float,
    text_box_opacity: int,
) -> Image.Image:
    img = base.convert("RGBA")
    w, h = img.size

    # Determine font size relative to height
    font_size = max(18, int(h * font_size_pct))
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # word wrap roughly to fit width
    # estimate chars per line by measuring 'M'
    try:
        avg_char_w = font.getlength("M")
    except Exception:
        avg_char_w = font.getbbox("M")[2]
    max_chars = max(10, int((w - 2 * padding_px) / max(1, avg_char_w)))
    wrapped = "\n".join(textwrap.wrap(text, width=max_chars))

    # Measure text block
    draw = ImageDraw.Draw(img)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=int(font_size * (line_spacing - 1)), align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Position center
    x = (w - text_w) // 2
    y = (h - text_h) // 2

    # Background box for readability
    box = Image.new("RGBA", (text_w + 2 * padding_px, text_h + 2 * padding_px), (0, 0, 0, text_box_opacity))
    img.alpha_composite(box, dest=(x - padding_px, y - padding_px))

    # Draw text
    draw = ImageDraw.Draw(img)
    draw.multiline_text((x, y), wrapped, fill=(255, 255, 255, 255), font=font, align="center",
                        spacing=int(font_size * (line_spacing - 1)))

    return img.convert("RGB")


def build_scene_image(
    size: Tuple[int, int],
    theme: str,
    text: str,
    bg_image_path: Optional[str],
    settings: Settings,
) -> Image.Image:
    if bg_image_path:
        try:
            base = Image.open(bg_image_path).convert("RGB").resize(size)
        except Exception:
            base = make_gradient_bg(size, theme)
    else:
        base = make_gradient_bg(size, theme)
    composed = draw_text_block(
        base,
        text,
        settings.padding_px,
        settings.font_path,
        settings.font_size_pct,
        settings.line_spacing,
        settings.text_box_opacity,
    )
    return composed


def save_pil_image(img: Image.Image) -> str:
    path = os.path.join(TEMP_DIR, f"frame_{uuid.uuid4().hex}.png")
    img.save(path, format="PNG")
    return path


def create_video(scenes: List[Scene], settings: Settings, resolution: Tuple[int, int], logo_path: Optional[str]) -> str:
    clips = []
    W, H = resolution

    # Optional logo overlay
    logo_overlay_path = None
    if logo_path and os.path.exists(logo_path):
        try:
            # Render logo as small PNG once
            logo_img = Image.open(logo_path).convert("RGBA")
            target_w = max(64, int(W * 0.12))
            ratio = target_w / logo_img.width
            target_h = int(logo_img.height * ratio)
            logo_img = logo_img.resize((target_w, target_h))
            logo_overlay_path = os.path.join(TEMP_DIR, f"logo_{uuid.uuid4().hex}.png")
            logo_img.save(logo_overlay_path)
        except Exception:
            logo_overlay_path = None

    for i, sc in enumerate(scenes):
        img = Image.open(sc.bg_image_path) if sc.bg_image_path else make_gradient_bg((W, H), settings.theme)
        img = img.resize((W, H))
        frame_path = save_pil_image(img)

        base = ImageClip(frame_path).set_duration(sc.duration)
        audio = AudioFileClip(sc.audio_path)
        base = base.set_audio(audio)

        # Soft fades (not true crossfades, but pleasant)
        if i > 0:
            base = base.crossfadein(0.4)
        if i < len(scenes) - 1:
            base = base.crossfadeout(0.4)

        # Logo overlay (top-right)
        if logo_overlay_path is not None:
            lc = (ImageClip(logo_overlay_path)
                  .set_duration(sc.duration)
                  .margin(right=20, top=20, opacity=0)
                  .set_pos(("right", "top")))
            base = CompositeVideoClip([base, lc])

        clips.append(base)

    final = concatenate_videoclips(clips, method="compose")
    out_path = os.path.join(OUTPUT_DIR, f"text2video_{uuid.uuid4().hex}.mp4")
    final.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=os.cpu_count() or 4,
        preset="medium",
        bitrate="4000k",
        temp_audiofile=os.path.join(TEMP_DIR, f"temp-audio-{uuid.uuid4().hex}.m4a"),
        remove_temp=True,
        verbose=False,
        logger=None,
    )
    return out_path


def srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h = ms // 3600000
    ms -= h * 3600000
    m = ms // 60000
    ms -= m * 60000
    s = ms // 1000
    ms -= s * 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt_for_scenes(scenes: List[Scene], srt_path: str) -> None:
    t = 0.0
    lines = []
    for idx, sc in enumerate(scenes, start=1):
        start = srt_timestamp(t)
        end = srt_timestamp(t + sc.duration)
        text = sc.text.strip().replace("\n", " ")
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
        t += sc.duration
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------
# Streamlit UI
# ---------------------------

st.set_page_config(page_title="Tekst → Video AI (lokaal)", page_icon="🎬", layout="wide")

st.title("🎬 Tekst → Video (lokaal)")
colA, colB = st.columns([2, 1])

with colA:
    script = st.text_area(
        "Je script (lege regel = nieuwe scene)",
        height=320,
        placeholder=(
            "Voorbeeld:\n\n"
            "Intro: In deze video leg ik uit wat een warmtepomp is.\n\n"
            "Werking: Een warmtepomp haalt warmte uit de lucht of bodem en verwarmt je huis.\n\n"
            "Voordelen: Lager energieverbruik en minder CO₂-uitstoot.\n\n"
            "Slot: Abonneer voor meer energietips!"
        ),
    )

    uploaded_bgs = st.file_uploader(
        "(Optioneel) Upload achtergrondafbeeldingen — worden op volgorde per scene gebruikt",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )
    logo = st.file_uploader("(Optioneel) Upload je logo (PNG met transparantie)", type=["png"])

with colB:
    aspect = st.selectbox("Formaat", list(ASPECTS.keys()), index=0)
    theme = st.selectbox("Thema", list(THEMES.keys()), index=0)
    speed = st.slider("Stem-snelheid", 0.7, 1.5, 1.0, 0.05)
    font_size_pct = st.slider("Tekstgrootte (% van hoogte)", 0.03, 0.12, 0.065, 0.005)
    line_spacing = st.slider("Regelafstand (x)", 1.0, 2.0, 1.2, 0.05)
    padding_px = st.slider("Padding tekstbox (px)", 10, 120, 40, 2)
    text_box_opacity = st.slider("Achtergrond dekking (0-255)", 0, 255, 140, 5)
    lang = st.selectbox("TTS-taal (gTTS)", ["nl", "en"], index=0)
    gen_srt = st.checkbox("Ondertitels (SRT) genereren", value=True)

    custom_font = st.text_input("(Optioneel) Pad naar .ttf font op je systeem", value="")

    st.caption("Tip: gebruik lege regels om scenes te bepalen. Anders splitst de app zelf op zinsniveau.")

# Resolve settings
W, H = ASPECTS[aspect]
font_path = find_font(custom_font if custom_font.strip() else None)
settings = Settings(
    resolution=(W, H),
    theme=theme,
    padding_px=padding_px,
    font_path=font_path,
    font_size_pct=float(font_size_pct),
    text_box_opacity=int(text_box_opacity),
    line_spacing=float(line_spacing),
    speed=float(speed),
)

# Process backgrounds
bg_paths: List[Optional[str]] = []
if uploaded_bgs:
    for f in uploaded_bgs:
        data = f.read()
        p = os.path.join(TEMP_DIR, f"bg_{uuid.uuid4().hex}.png")
        with open(p, "wb") as out:
            out.write(data)
        bg_paths.append(p)

logo_path = None
if logo is not None:
    logo_path = os.path.join(TEMP_DIR, f"logo_{uuid.uuid4().hex}.png")
    with open(logo_path, "wb") as out:
        out.write(logo.read())

st.markdown("---")

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🔊 Test één scene als audio (TTS)"):
        if not script.strip():
            st.warning("Plak eerst je script.")
        else:
            first = split_script(script)[0]
            try:
                mp3_path, dur = tts_to_mp3(first, lang=lang)
                st.audio(mp3_path)
                st.info(f"Duur: {dur:.1f}s")
            except Exception as e:
                st.error(str(e))

with col2:
    render = st.button("🎥 Render video")

if render:
    if not script.strip():
        st.error("Geen script gevonden.")
        st.stop()

    blocks = split_script(script)

    st.write(f"Aantal scenes: **{len(blocks)}**")

    scenes: List[Scene] = []
    progress = st.progress(0)

    for i, blk in enumerate(blocks):
        progress.progress(min(1.0, (i) / max(1, len(blocks))))
        # TTS
        try:
            mp3_path, dur = tts_to_mp3(blk, lang=lang)
        except Exception as e:
            st.error(str(e))
            st.stop()
        mp3_path, dur = change_speed(mp3_path, settings.speed)

        # Visual
        bg = bg_paths[i] if i < len(bg_paths) else None
        frame_img = build_scene_image(
            (W, H),
            settings.theme,
            blk,
            bg,
            settings,
        )
        frame_path = save_pil_image(frame_img)

        scenes.append(
            Scene(text=blk, bg_image_path=frame_path, audio_path=mp3_path, duration=dur)
        )

    progress.progress(1.0)

    st.write("Compositie en export… dit kan even duren bij langere video’s.")
    try:
        out_path = create_video(scenes, settings, (W, H), logo_path)
        st.success("Klaar! Hieronder een preview en downloadlink.")
        st.video(out_path)
        st.write(f"📁 Output: `{out_path}`")
        if gen_srt:
            base = os.path.splitext(os.path.basename(out_path))[0]
            srt_path = os.path.join(OUTPUT_DIR, base + ".srt")
            write_srt_for_scenes(scenes, srt_path)
            with open(srt_path, "rb") as f:
                st.download_button("⬇️ Download SRT-ondertitels", data=f, file_name=os.path.basename(srt_path), mime="text/plain")
    except Exception as e:
        st.exception(e)

st.caption("Let op: MoviePy en pydub gebruiken ffmpeg. Zorg dat ffmpeg werkt via je PATH (controleer met `ffmpeg -version`).")
