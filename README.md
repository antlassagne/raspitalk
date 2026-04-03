## Lunii hacking

TODO

- [x] FreeCAD model --> A wood thingy will do
- [x] Hardware description (BOM)
- [x] Hardware soldering
- [x] Reworked state machine
- [x] Displayed information design and implementation
- [x] STT backend - running on a remote machine
- [x] TTS backend - running on a remote machine
- [ ] Free conversation mode
- [ ] Solve hat led / display SPI conflict

## What is it

It's a small box that can tell stories. It's based on raspi zero with some addons and a little pieces of software.

### Harware:

- A Raspberry Pi zero 2 W (+ power)
- A KeyeStudio KS0314 hat ([ReSpeaker 2-Mic](https://docs.keyestudio.com/projects/KS0314/en/latest/))
- A speaker - which ever you can scavenge on any broken toy
- A display ([Waveshare 2inch LCD module](https://www.waveshare.com/wiki/2inch_LCD_Module))

### Software

- A controler running on the pi
- 3 services running on an external, more powerful, machine
  - Whisper to transcribe the voice input,
  - Ollama to generate a story from the transcription,
  - AllTalk to generate an voice back.

## Installation

### On the edge

```
sudo apt install libportaudio2 portaudio19-dev git-lfs
```

### On the big bad remote machine

- Step 1: Ollama setting

```bash
sudo snap install ollama
sudo snap set ollama host=0.0.0.0:11434
ollama pull obautomation/OpenEuroLLM-French # will be done automatically but doing it before to avoid surprises
```

- Step 2: STT setting

```bash
docker run --restart=always --detach --gpus all -e LANGUAGE=fr -e MODEL=large-v3 -e DEVICE=cuda -e TRANSLATE=no -e COMPUTE_SIZE=float32 -p 9876:9876 --name stt braoutch/remotefastwhisper:latest
```

- Step 3 TTS setting

### Coqui (testing impl, not the right one)

Using https://github.com/coqui-ai/TTS

```bash
docker run --gpus all --restart always -p 5002:5002 --entrypoint /bin/bash ghcr.io/coqui-ai/tts-cpu
python3 TTS/server/server.py --model_name tts_models/fr/mai/tacotron2-DDC --use_cuda True
```

and configure the right server IP / port

### Alltalk, you ~~are~~were the chosen one

Not compatible with ARM64

```
apt install libaio-dev espeak-ng
git clone -b alltalkbeta https://github.com/erew123/alltalk_tts
cd alltalk_tts
./atsetup.sh
./start_alltalk.sh
```

### Speaches

https://speaches.ai/usage/text-to-speech/

```bash
docker run \
  --detach \
  --publish 8000:8000 \
  --name tts \
  --restart always \
  --volume hf-hub-cache:/home/ubuntu/.cache/huggingface/hub \
  --gpus=all \
  ghcr.io/speaches-ai/speaches:latest-cuda
```

and then download the models

```bash
export URL=http://localhost:8000/v1
# to list STT
# curl "$URL/registry?task=automatic-speech-recognition" | jq '[.data[].id]'

# to list TTS
# curl "$URL/registry?task=text-to-speech" | jq '[.data[].id]'

# and then download some
curl "$URL/models/Kelno/whisper-large-v3-french-distil-dec16-ct2" -X POST
curl "$URL/v1/models/speaches-ai/piper-fr_FR-tom-medium" -X POST
```

## Rebuilding the Stack

## Speaches

First, enter the docker container and source the venv

```bash
docker exec -it --user 0 speaches /bin/bash
source .venv/bin/activate
```

To list

```bash
export SPEACHES_BASE_URL="http://localhost:8000"

# Listing all available TTS models
uv tool run speaches-cli registry ls --task text-to-speech | jq '.data | [].id'

# Downloading a TTS model
uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX

# Check that the model has been installed
uv tool run speaches-cli model ls --task text-to-speech | jq '.data | map(select(.id == "speaches-ai/Kokoro-82M-v1.0-ONNX"))'
```

Kokoro models that supports fr:
suronek/Kokoro-82M-v1.1-zh-ONNX
speaches-ai/Kokoro-82M-v1.0-ONNX
speaches-ai/Kokoro-82M-v1.0-ONNX-int8
speaches-ai/Kokoro-82M-v1.0-ONNX-fp16

language: multilingual
voice: ff_siwis

### Remote fast whisper

Prepare the machine

```bash
docker run --privileged --rm tonistiigi/binfmt --install all
sudo nano /etc/docker/daemon.json
```

Add the `features` part

```json
{
    "runtimes": {
        "nvidia": {
            "args": [],
            "path": "nvidia-container-runtime"
        }
    },
    "features": {
        "containerd-snapshotter": true
    }
}
```

```bash
git clone https://github.com/joshuaboniface/remote-faster-whisper.git
cd remote-fast-whisper
docker buildx build --push --tag braoutch/remotefastwhisper:latest --platform linux/amd64,linux/arm64 .
```
