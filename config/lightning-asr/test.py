#!/usr/bin/env python3

import requests
import sys
import os
from pathlib import Path
import time


def test_asr_endpoint(audio_file_path, base_url="http://localhost:7100/api/v1", language=None, model=None):
    if not os.path.exists(audio_file_path):
        print(f"Error: Audio file not found: {audio_file_path}")
        return None

    url = f"{base_url}/speech-to-text"

    try:
        with open(audio_file_path, 'rb') as audio_file:
            files = {'file': (os.path.basename(
                audio_file_path), audio_file, 'audio/wav')}

            data = {}
            if language:
                data['language'] = language
            if model:
                data['model'] = model

            print(f"Sending request to: {url}")
            print(f"Audio file: {audio_file_path}")
            if language:
                print(f"Language: {language}")
            if model:
                print(f"Model: {model}")

            start_time = time.time()

            response = requests.post(url, files=files, data=data)

            print(f"Time taken: {time.time() - start_time} seconds")

            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")

            if response.status_code == 200:
                print(f"Transcription: {response.text}")
            else:
                print(f"Error Response: {response.text}")

            return response

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python test_asr_endpoint.py <audio_file_path> [base_url] [language] [model]")
        print("Example: python test_asr_endpoint.py sample.wav")
        print("Example: python test_asr_endpoint.py sample.wav http://localhost:7100 en")
        sys.exit(1)

    audio_file_path = sys.argv[1]
    base_url = sys.argv[2] if len(
        sys.argv) > 2 else "http://localhost:7100/api/v1"
    language = sys.argv[3] if len(sys.argv) > 3 else None
    model = sys.argv[4] if len(sys.argv) > 4 else None

    test_asr_endpoint(audio_file_path, base_url, language, model)


if __name__ == "__main__":
    main()
