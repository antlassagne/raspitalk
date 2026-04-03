#!/bin/bash
docker run -it --restart always --gpus all -e LANGUAGE=fr -e MODEL=large-v3 -e DEVICE=cpu -e TRANSLATE=no -e COMPUTE_SIZE=float32 -p 9876:9876 --name stt braoutch/remotefastwhisper:latest
