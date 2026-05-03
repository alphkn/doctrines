import os
import glob
import logging
from google.cloud import texttospeech
import xml.etree.ElementTree as ET

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "tts-credential.json"
client = texttospeech.TextToSpeechClient()

input_dir = "input"
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

files = glob.glob(os.path.join(input_dir, "*.*"))

def validate_ssml(ssml_content):
    """Validate SSML syntax."""
    try:
        ET.fromstring(f"<root>{ssml_content}</root>")
        logging.info("SSML syntax is valid.")
        return True
    except ET.ParseError as e:
        logging.error(f"Invalid SSML syntax: {e}")
        return False

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
                if not validate_ssml(content):
                    logging.error("Skipping file due to invalid SSML.")
                    failure_count += 1
                    continue

                synthesis_input = texttospeech.SynthesisInput(ssml=content)
                logging.info("Using SSML input.")

                voice = texttospeech.VoiceSelectionParams(
                    language_code="tr-TR",
                    name="tr-TR-Wavenet-E",
                    ssml_gender=texttospeech.SsmlVoiceGender.MALE
                )

                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    speaking_rate=1.0,
                    pitch=0.0
                )

            else:
                synthesis_input = texttospeech.SynthesisInput(text=content.strip())
                logging.info("Using plain text input.")

                voice = texttospeech.VoiceSelectionParams(
                    language_code="tr-TR",
                    name="tr-TR-Chirp3-HD-Iapetus",
                    ssml_gender=texttospeech.SsmlVoiceGender.MALE
                )

                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    speaking_rate=1.0,
                    pitch=0.0
                )

            logging.info("Sending request to TTS API...")
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            logging.info(f"Response received. Audio content size: {len(response.audio_content)} bytes")

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(output_dir, base_name + ".mp3")

            with open(output_path, "wb") as out:
                out.write(response.audio_content)

            logging.info(f"✔️ Generated audio: {output_path}")
            success_count += 1

        except Exception as e:
            logging.error(f"❌ Error processing '{file_path}': {str(e)}")
            failure_count += 1

    logging.info(f"Batch complete: {success_count} succeeded, {failure_count} failed.")