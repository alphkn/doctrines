import os
import glob
import logging
import re
import shutil

from elevenlabs.client import ElevenLabs
from elevenlabs import save
from elevenlabs.types import VoiceSettings

from pydub import AudioSegment

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

API_KEY   = os.environ.get("ELEVEN_API_KEY", "YOUR_API_KEY_HERE")
VOICE_ID  = "6H6FG7kAHiOf7LXnwus7"
MODEL_ID  = "eleven_multilingual_v2"   # Recommended model for Turkish

input_dir     = "input"
output_dir    = "output"
processed_dir = "processed"
final_dir     = "final"

os.makedirs(output_dir, exist_ok=True)
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

SILENCE_AT_START_MS = 1500
SILENCE_BETWEEN_PARTS_MS = 2500

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


def add_leading_silence(mp3_path, duration_ms):
    audio = AudioSegment.from_mp3(mp3_path)
    silence = AudioSegment.silent(duration=duration_ms)
    final_audio = silence + audio
    final_audio.export(mp3_path, format="mp3", bitrate="192k")
    logging.info(f"🔇 Added silence: {mp3_path}")


def combine_all_series():

    mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))

    if not mp3_files:
        logging.warning("No mp3 files found.")
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

    # =====================================================
    # COMBINE EACH SERIES — SKIP IF ALREADY COMBINED
    # =====================================================

    for series_name, files in grouped.items():

        final_output_path = os.path.join(
            final_dir, f"{series_name}_full.mp3"
        )

        # Check if all parts are already present in output/
        # by comparing against what was previously combined.
        # Skip if the final file already exists AND none of
        # the parts are newer than the final file.
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
                output_format="mp3_44100_192",
                voice_settings=VOICE_SETTINGS,
            )

            base_name   = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(output_dir, base_name + ".mp3")

            save(audio, output_path)
            logging.info(f"✔️  Generated audio: {output_path}")

            # =============================================
            # ADD LEADING SILENCE
            # =============================================

            add_leading_silence(output_path, SILENCE_AT_START_MS)

            # =============================================
            # MOVE SOURCE FILE TO PROCESSED
            # =============================================

            dest_path = os.path.join(processed_dir, os.path.basename(file_path))
            shutil.move(file_path, dest_path)
            logging.info(f"📁 Moved source file to: {dest_path}")

            success_count += 1

        except Exception as e:
            logging.error(f"❌ Error processing '{file_path}': {e}")
            failure_count += 1

    logging.info(
        f"Batch complete: {success_count} succeeded, {failure_count} failed."
    )

# =========================================================
# AUTO COMBINE — always runs regardless of input folder state
# =========================================================

combine_all_series()