import requests
import wave
import io
import time
sample_rate = 24000 
num_channels = 1
sample_width = 2  

url = "http://localhost:4444/api/v1/lightning-large/get_speech"

headers = {
    "Content-Type": "application/json"
}

request_body = {
    "voice_id":"chirag",
    "text": "hey there",
    "consistency":1
}

sent_time = time.time()
print("sending request")

response = requests.post(url, json=request_body, headers=headers)

print("response received")
print(time.time() - sent_time)

if response.status_code == 200:
    print("audio received")
    audio_bytes = response.content

    buffer = io.BytesIO()
    
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)
    
    with open("output.wav", "wb") as f:
        f.write(buffer.getvalue())
    
    print("Audio saved as output.wav with WAV header.")
else:
    print(f"Request failed with status code {response.status_code}: {response.text}")

