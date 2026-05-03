import os
import glob
import logging
import re
import shutil
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from elevenlabs.types import VoiceSettings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- SETTINGS ---
#https://elevenlabs.io/app/voice-library?voiceId=DsbR47WNEv8o9x37ib9X
#https://elevenlabs.io/app/voice-library?voiceId=xqO6WRAnejFhRL0H6VSW
#https://elevenlabs.io/app/voice-library?voiceId=04SEuljgeCeHgjzEyD4c
#https://elevenlabs.io/app/voice-library?voiceId=6H6FG7kAHiOf7LXnwus7

API_KEY   = os.environ.get("ELEVEN_API_KEY", "sk_369e7ba58cb0b5f5c9514d322629212bc0b06e8f0d9c505f")
VOICE_ID  = "6H6FG7kAHiOf7LXnwus7"   
#VOICE_ID = "pNInz6obpgDQGcFmaJgB" # Adam (multilingual) — replace with your preferred voice ID
MODEL_ID  = "eleven_multilingual_v2"   # Recommended model for Turkish

input_dir     = "input"
output_dir    = "output"
processed_dir = "processed"
 
os.makedirs(output_dir, exist_ok=True)
os.makedirs(processed_dir, exist_ok=True)
 
# --- VOICE SETTINGS (tuned for calm/telkin style) ---
# speed:            0.7–1.2   | 0.80 = slow, calm delivery
# stability:        0.0–1.0   | 0.80 = consistent, steady tone (higher = less emotional variation)
# similarity_boost: 0.0–1.0   | 0.75 = balanced adherence to original voice
# style:            0.0–1.0   | 0.15 = slight style emphasis without overdoing it
# use_speaker_boost: True     = improves clarity and voice consistency
VOICE_SETTINGS = VoiceSettings(
    stability=0.43,
    similarity_boost=0.82,
    style=0.38,
    use_speaker_boost=True,
    speed=0.90,
)
  # passed separately in the API call
 
# ----------------
 
client = ElevenLabs(api_key=API_KEY)
 
 
def strip_xml_tags(text: str) -> str:
    """Remove SSML/XML tags and return plain text."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean
 
 
files = glob.glob(os.path.join(input_dir, "*.*"))
 
if not files:
    logging.warning("No files found in the input folder.")
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
                # ElevenLabs does not support SSML — strip tags and use plain text
                text = strip_xml_tags(content)
                logging.info("XML file — SSML tags stripped, using plain text.")
            else:
                text = content.strip()
                logging.info("Using plain text input.")
 
            if not text:
                logging.warning(f"Empty content, skipping: {file_path}")
                failure_count += 1
                continue
 
            logging.info("Sending request to ElevenLabs API...")
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
 
            # Move the source file to processed/ to avoid re-processing
            dest_path = os.path.join(processed_dir, os.path.basename(file_path))
            shutil.move(file_path, dest_path)
            logging.info(f"📁 Moved source file to: {dest_path}")
 
            success_count += 1
 
        except Exception as e:
            logging.error(f"❌ Error processing '{file_path}': {e}")
            failure_count += 1
 
    logging.info(f"Batch complete: {success_count} succeeded, {failure_count} failed.")