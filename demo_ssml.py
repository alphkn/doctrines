from google.cloud import texttospeech
import os

# Set credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "tts-credential.json"

# Output base directory
BASE_DIR = "output"
MALE_DIR = os.path.join(BASE_DIR, "male")
FEMALE_DIR = os.path.join(BASE_DIR, "female")

os.makedirs(MALE_DIR, exist_ok=True)
os.makedirs(FEMALE_DIR, exist_ok=True)

def demo_ssml_tts():
    client = texttospeech.TextToSpeechClient()

    ssml_text = """
    <speak>
      Gün başladı. Koştun. Terledin. Şimdi zihin sırada. <break time="500ms"/> Dik dur.<break time="700ms"/>
      Sert olacağım. Sağlam duracağım. Kendimi ezdirmeyeceğim.
    </speak>
    """

    voices = client.list_voices()

    male_voices = []
    female_voices = []

    for voice in voices.voices:
        if "tr-TR" in voice.language_codes:
            print(f"\n🔊 Trying voice: {voice.name} | Gender: {texttospeech.SsmlVoiceGender(voice.ssml_gender).name}")

            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

            voice_params = texttospeech.VoiceSelectionParams(
                language_code="tr-TR",
                name=voice.name,
                ssml_gender=voice.ssml_gender,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            try:
                response = client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=audio_config,
                )

                gender = texttospeech.SsmlVoiceGender(voice.ssml_gender).name
                if gender == "MALE":
                    path = os.path.join(MALE_DIR, f"{voice.name}.mp3")
                    male_voices.append(voice.name)
                elif gender == "FEMALE":
                    path = os.path.join(FEMALE_DIR, f"{voice.name}.mp3")
                    female_voices.append(voice.name)
                else:
                    # Neutral or undefined: Save in both
                    male_voices.append(voice.name)
                    female_voices.append(voice.name)
                    path = os.path.join(BASE_DIR, f"{voice.name}.mp3")

                with open(path, "wb") as out:
                    out.write(response.audio_content)
                print(f"✔️ SSML supported. Saved: {path}")

            except Exception as e:
                print(f"⚠️ Skipped (no SSML support): {voice.name} | Reason: {e}")

    # Print lists
    print("\n✅ SSML-SUPPORTED MALE VOICES:")
    for name in sorted(set(male_voices)):
        print(f" - {name}")

    print("\n✅ SSML-SUPPORTED FEMALE VOICES:")
    for name in sorted(set(female_voices)):
        print(f" - {name}")

if __name__ == "__main__":
    demo_ssml_tts()
