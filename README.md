# Rship Whisper

<h2 align="center">
  A nearly-live implementation of OpenAI's Whisper ... as an rship executor!
</h2>

This project is a real-time transcription application that uses the OpenAI Whisper model
to convert speech input into text output. It can be used to transcribe multiple audio input sources to individual targets in rship. 

## Installation
```bash
pip install -r requirements/client.txt
```

## Run

```bash
python rship_whisper.py
```

### Setting up NVIDIA/TensorRT-LLM for TensorRT backend
- Please follow [TensorRT_whisper readme](https://github.com/collabora/WhisperLive/blob/main/TensorRT_whisper.md) for setup of [NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) and for building Whisper-TensorRT engine.


## Whisper Live Server in Docker
it is required to have a version of the server running to use this application. we recomend the TensorRT variant as described below. 

- GPU
  - Faster-Whisper
  ```bash
  docker run -it --gpus all -p 9090:9090 ghcr.io/collabora/whisperlive-gpu:latest
  ```

  - TensorRT. 
  ```bash
  docker run -p 9090:9090 --gpus all --entrypoint /bin/bash -it ghcr.io/collabora/whisperlive-tensorrt

  # Build tiny.en engine
  bash build_whisper_tensorrt.sh /app/TensorRT-LLM-examples small.en

  # Run server with tiny.en
  python3 run_server.py --port 9090 \
                        --backend tensorrt \
                        --trt_model_path "/app/TensorRT-LLM-examples/whisper/whisper_small_en"
  ```

- CPU
```bash
docker run -it -p 9090:9090 ghcr.io/collabora/whisperlive-cpu:latest
```
**Note**: By default we use "small" model size. To build docker image for a different model size, change the size in server.py and then build the docker image.

**Another Note**
just use the docker compose file by running `docker compose up -d`