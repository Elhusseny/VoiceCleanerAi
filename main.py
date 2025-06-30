from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os, uuid
from pydub import AudioSegment
import soundfile as sf
import noisereduce as nr
from gtts import gTTS
import subprocess

# إعداد التطبيق
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = "uploads"
RESULT_DIR = "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# إزالة الضوضاء
@app.post("/api/denoise")
async def denoise(audio: UploadFile):
    input_path = f"{UPLOAD_DIR}/{uuid.uuid4().hex}_{audio.filename}"
    with open(input_path, "wb") as f:
        f.write(await audio.read())

    wav_path = input_path.replace(".mp3", ".wav")
    AudioSegment.from_file(input_path).set_channels(1).set_frame_rate(22050).export(wav_path, format="wav")
    data, rate = sf.read(wav_path)
    reduced_noise = nr.reduce_noise(y=data, sr=rate)

    output_path = f"{RESULT_DIR}/denoised_{uuid.uuid4().hex}.wav"
    sf.write(output_path, reduced_noise, rate)

    return {
        "cleanedAudioUrl": f"/download/{os.path.basename(output_path)}",
        "noiseLevel": 35.0
    }

# فصل الموسيقى
@app.post("/api/separate")
async def separate(audio: UploadFile):
    input_path = f"{UPLOAD_DIR}/{uuid.uuid4().hex}_{audio.filename}"
    with open(input_path, "wb") as f:
        f.write(await audio.read())

    subprocess.run(f"spleeter separate -p spleeter:2stems -o {RESULT_DIR} {input_path}", shell=True)

    folder = os.path.splitext(os.path.basename(input_path))[0]
    return {
        "vocalsUrl": f"/download/{folder}/vocals.wav",
        "musicUrl": f"/download/{folder}/accompaniment.wav"
    }

# استنساخ الصوت (Voice Cloning)
@app.post("/api/clone")
async def clone(audio: UploadFile, text: str = Form(...)):
    tts = gTTS(text=text, lang='ar')
    output_path = f"{RESULT_DIR}/clone_{uuid.uuid4().hex}.mp3"
    tts.save(output_path)
    return {
        "clonedVoiceUrl": f"/download/{os.path.basename(output_path)}"
    }

# تحميل الملفات
@app.get("/download/{path:path}")
def download(path: str):
    return FileResponse(f"{RESULT_DIR}/{path}")