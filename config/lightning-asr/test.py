#!/usr/bin/env python3

import requests
import sys
import os
from pathlib import Path
import time
import json


def test_asr_endpoint(
    audio_file_path, 
    base_url="http://localhost:7100",
    language="en",
    model="lightning",
    word_timestamps=False,
    age_detection=False,
    gender_detection=False,
    emotion_detection=False
):
    if not os.path.exists(audio_file_path):
        print(f"Error: Audio file not found: {audio_file_path}")
        return None

    url = f"{base_url}/api/v1/lightning/get_text"

    try:
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        params = {
            'model': model,
            'language': language,
            'word_timestamps': str(word_timestamps).lower(),
            'age_detection': str(age_detection).lower(),
            'gender_detection': str(gender_detection).lower(),
            'emotion_detection': str(emotion_detection).lower()
        }

        headers = {
            'Content-Type': 'application/octet-stream'
        }

        print(f"Sending request to: {url}")
        print(f"Audio file: {audio_file_path}")
        print(f"Parameters:")
        print(f"  - Model: {model}")
        print(f"  - Language: {language}")
        print(f"  - Word timestamps: {word_timestamps}")
        print(f"  - Age detection: {age_detection}")
        print(f"  - Gender detection: {gender_detection}")
        print(f"  - Emotion detection: {emotion_detection}")
        print()

        start_time = time.time()

        response = requests.post(url, params=params, data=audio_data, headers=headers)

        elapsed_time = time.time() - start_time
        print(f"Time taken: {elapsed_time:.2f} seconds")
        print(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n=== Transcription Result ===")
            print(f"Status: {result.get('status')}")
            print(f"Transcription: {result.get('transcription')}")
            
            if 'word_timestamps' in result:
                print(f"\nWord Timestamps: {len(result['word_timestamps'])} words")
                for word_info in result['word_timestamps'][:5]:
                    print(f"  - {word_info['word']}: {word_info['start']:.2f}s - {word_info['end']:.2f}s")
                if len(result['word_timestamps']) > 5:
                    print(f"  ... and {len(result['word_timestamps']) - 5} more words")
            
            if 'age' in result:
                print(f"\nAge: {result['age']}")
            
            if 'gender' in result:
                print(f"Gender: {result['gender']}")
            
            if 'emotions' in result:
                print("\nEmotions:")
                for emotion, score in result['emotions'].items():
                    print(f"  - {emotion.capitalize()}: {score:.2f}")
            
            if 'metadata' in result:
                metadata = result['metadata']
                print(f"\nMetadata:")
                if 'duration' in metadata:
                    print(f"  - Duration: {metadata['duration']} minutes")
                if 'fileSize' in metadata:
                    print(f"  - File size: {metadata['fileSize']:,} bytes")
            
            print("\n=== Full Response ===")
            print(json.dumps(result, indent=2))
        else:
            print(f"\nError Response: {response.text}")

        return response

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_asr_endpoint.py <audio_file_path> [options]")
        print("\nOptions:")
        print("  --base-url <url>        Base URL (default: http://localhost:7100)")
        print("  --language <lang>       Language code (default: en)")
        print("  --model <model>         Model name (default: lightning)")
        print("  --word-timestamps       Include word-level timestamps")
        print("  --age-detection         Predict speaker age")
        print("  --gender-detection      Predict speaker gender")
        print("  --emotion-detection     Predict speaker emotions")
        print("\nExamples:")
        print("  python test_asr_endpoint.py sample.wav")
        print("  python test_asr_endpoint.py sample.wav --language en --word-timestamps")
        print("  python test_asr_endpoint.py sample.wav --emotion-detection --age-detection")
        sys.exit(1)

    audio_file_path = sys.argv[1]
    base_url = "http://localhost:7100"
    language = "en"
    model = "lightning"
    word_timestamps = False
    age_detection = False
    gender_detection = False
    emotion_detection = False

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--base-url' and i + 1 < len(sys.argv):
            base_url = sys.argv[i + 1]
            i += 2
        elif arg == '--language' and i + 1 < len(sys.argv):
            language = sys.argv[i + 1]
            i += 2
        elif arg == '--model' and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
            i += 2
        elif arg == '--word-timestamps':
            word_timestamps = True
            i += 1
        elif arg == '--age-detection':
            age_detection = True
            i += 1
        elif arg == '--gender-detection':
            gender_detection = True
            i += 1
        elif arg == '--emotion-detection':
            emotion_detection = True
            i += 1
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)

    test_asr_endpoint(
        audio_file_path,
        base_url,
        language,
        model,
        word_timestamps,
        age_detection,
        gender_detection,
        emotion_detection
    )


if __name__ == "__main__":
    main()
