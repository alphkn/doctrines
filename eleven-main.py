import os
import glob
import logging
import re
import shutil

from elevenlabs.client import ElevenLabs
from elevenlabs import save
from elevenlabs.types import VoiceSettings

# =========================================================
# FFMPEG — looked up relative to this script's folder.
# Place ffmpeg.exe and ffprobe.exe next to eleven-main.py.
# =========================================================

import pydub.utils as _pydub_utils

_BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH  = os.path.join(_BASE_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(_BASE_DIR, "ffprobe.exe")

if not os.path.isfile(FFMPEG_PATH):
    raise FileNotFoundError(
        f"ffmpeg.exe not found in project folder: {_BASE_DIR}\n"
        "Download from https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip "
        "and place ffmpeg.exe + ffprobe.exe next to this script."
    )

_original_which = _pydub_utils.which

def _patched_which(name):
    if name == "ffmpeg":
        return FFMPEG_PATH
    if name == "ffprobe":
        return FFPROBE_PATH
    return _original_which(name)

_pydub_utils.which = _patched_which

from pydub import AudioSegment

AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffmpeg    = FFMPEG_PATH
AudioSegment.ffprobe   = FFPROBE_PATH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =========================================================
# SETTINGS
# =========================================================

#https://elevenlabs.io/app/voice-library?voiceId=DsbR47WNEv8o9x37ib9X
#https://elevenlabs.io/app/voice-library?voiceId=xqO6WRAnejFhRL0H6VSW
#https://elevenlabs.io/app/voice-library?voiceId=04SEuljgeCeHgjzEyD4c
#https://elevenlabs.io/app/voice-library?voiceId=6H6FG7kAHiOf7LXnwus7

API_KEY   = os.environ.get("ELEVEN_API_KEY", "sk_369e7ba58cb0b5f5c9514d322629212bc0b06e8f0d9c505f")
VOICE_ID  = "6H6FG7kAHiOf7LXnwus7"
MODEL_ID  = "eleven_multilingual_v2"   # Recommended model for Turkish

input_dir     = "input"      # source text files
output_dir    = "output"     # raw TTS audio (no silence yet)
silenced_dir  = "silenced"   # silence added, ready for combine
processed_dir = "processed"  # source text files after TTS
final_dir     = "final"      # combined full series

os.makedirs(output_dir, exist_ok=True)
os.makedirs(silenced_dir, exist_ok=True)
os.makedirs(processed_dir, exist_ok=True)
os.makedirs(final_dir, exist_ok=True)

# =========================================================
# AUDIO SETTINGS
# =========================================================

VOICE_SETTINGS = VoiceSettings(
    stability=0.43,
    similarity_boost=0.82,
    style=0.38,
    use_speaker_boost=True,
    speed=0.90,
)

SILENCE_AT_START_MS      = 3000
SILENCE_BETWEEN_PARTS_MS = 6000

# =========================================================

client = ElevenLabs(api_key=API_KEY)

# =========================================================
# HELPERS
# =========================================================

def strip_xml_tags(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def get_series_name(filename):
    """
    character_stoa_deepseek_part_01.mp3
    ->
    character_stoa_deepseek
    """
    match = re.match(r"(.+)_part_\d+", filename)
    if match:
        return match.group(1)
    return None


def apply_leading_silence(src_path, dst_path, duration_ms):
    """
    Read src_path, prepend silence, write to dst_path.
    src_path and dst_path can be the same file.
    """
    audio = AudioSegment.from_mp3(src_path)
    silence = AudioSegment.silent(duration=duration_ms)
    result = silence + audio
    result.export(dst_path, format="mp3", bitrate="192k")
    logging.info(f"🔇 Silence added: {dst_path}")


def process_pending_silence():
    """
    Pick up any raw mp3s sitting in output/ that have not yet
    been moved to silenced/.  Useful when a previous run
    completed TTS but crashed before adding silence.
    """
    raw_files = glob.glob(os.path.join(output_dir, "*.mp3"))

    if not raw_files:
        return

    logging.info(
        f"🔁 Found {len(raw_files)} unsilenced file(s) in output/ — processing..."
    )

    for raw_path in sorted(raw_files):
        filename = os.path.basename(raw_path)
        dst_path = os.path.join(silenced_dir, filename)
        try:
            apply_leading_silence(raw_path, dst_path, SILENCE_AT_START_MS)
            os.remove(raw_path)
            logging.info(f"✅ Moved to silenced/: {filename}")
        except Exception as e:
            logging.warning(
                f"⚠️  Could not add silence to '{filename}': {e}. "
                f"Will retry on next run."
            )


def combine_all_series():
    """
    Combine parts from silenced/ into final/.
    Skips series whose final file is already up-to-date.
    """
    mp3_files = glob.glob(os.path.join(silenced_dir, "*.mp3"))

    if not mp3_files:
        logging.info("No files in silenced/ — nothing to combine.")
        return

    # =====================================================
    # GROUP FILES BY SERIES
    # =====================================================

    grouped = {}

    for path in mp3_files:
        filename = os.path.basename(path)
        series_name = get_series_name(filename)
        if not series_name:
            continue
        grouped.setdefault(series_name, []).append(path)

    if not grouped:
        logging.info("No series found to combine.")
        return

    # =====================================================
    # COMBINE EACH SERIES — SKIP IF ALREADY UP-TO-DATE
    # =====================================================

    for series_name, files in grouped.items():

        final_output_path = os.path.join(
            final_dir, f"{series_name}_full.mp3"
        )

        if os.path.exists(final_output_path):
            final_mtime = os.path.getmtime(final_output_path)
            newer_parts = [
                f for f in files
                if os.path.getmtime(f) > final_mtime
            ]
            if not newer_parts:
                logging.info(
                    f"⏭️  Skipping '{series_name}' — "
                    f"final file already up-to-date: {final_output_path}"
                )
                continue
            else:
                logging.info(
                    f"🔄 Re-combining '{series_name}' — "
                    f"{len(newer_parts)} new part(s) detected."
                )

        logging.info(f"🎬 Combining series: {series_name}")

        parts = sorted(files)
        final_audio = AudioSegment.empty()

        for mp3_file in parts:
            logging.info(f"➕ Adding: {mp3_file}")
            audio = AudioSegment.from_mp3(mp3_file)
            final_audio += audio
            silence = AudioSegment.silent(duration=SILENCE_BETWEEN_PARTS_MS)
            final_audio += silence

        final_audio.export(final_output_path, format="mp3", bitrate="192k")
        logging.info(f"🔥 Created final audio: {final_output_path}")

# =========================================================
# MAIN
# =========================================================

files = sorted(glob.glob(os.path.join(input_dir, "*.*")))

if not files:
    logging.warning("No files found in input folder.")

else:
    success_count = 0
    failure_count = 0

    for file_path in files:

        try:
            logging.info(f"Processing file: {file_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            ext = os.path.splitext(file_path)[1].lower()

            if ext == ".xml":
                text = strip_xml_tags(content)
                logging.info("XML detected — stripped tags.")
            else:
                text = content.strip()
                logging.info("Using plain text input.")

            if not text:
                logging.warning(f"Empty content, skipping: {file_path}")
                failure_count += 1
                continue

            logging.info("Sending request to ElevenLabs...")

            audio = client.text_to_speech.convert(
                voice_id=VOICE_ID,
                text=text,
                model_id=MODEL_ID,
                output_format="mp3_44100_128",
                voice_settings=VOICE_SETTINGS,
            )

            base_name   = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(output_dir, base_name + ".mp3")

            save(audio, output_path)
            logging.info(f"✔️  Generated audio: output/{base_name}.mp3")

            # =============================================
            # MOVE SOURCE FILE TO PROCESSED
            # Happens right after save() so the source is
            # never re-sent to the API on the next run.
            # =============================================

            dest_path = os.path.join(processed_dir, os.path.basename(file_path))
            shutil.move(file_path, dest_path)
            logging.info(f"📁 Moved to processed/: {os.path.basename(file_path)}")

            success_count += 1

        except Exception as e:
            logging.error(f"❌ Error processing '{file_path}': {e}")
            failure_count += 1

    logging.info(
        f"Batch complete: {success_count} succeeded, {failure_count} failed."
    )

# =========================================================
# STAGE 2 — ADD SILENCE (output/ -> silenced/)
# Runs even if input was empty, picks up leftovers too.
# =========================================================

process_pending_silence()

# =========================================================
# STAGE 3 — COMBINE (silenced/ -> final/)
# Runs even if input was empty.
# =========================================================

combine_all_series()