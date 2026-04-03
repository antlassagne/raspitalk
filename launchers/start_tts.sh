#!/bin/bash
set -e

CONTAINER_NAME="tts"
IMAGE="ghcr.io/speaches-ai/speaches:latest-cuda"
PUBLISH_PORT="8000:8000"

RUN=1

if [[ $1 == "norun" ]]; then
  RUN=0
fi

echo "Will I start the cont: $RUN"

if [[ $RUN -eq 1 ]]; then
  echo "Creating and starting container ${CONTAINER_NAME} from image ${IMAGE}"
  docker run \
  --detach \
  --publish ${PUBLISH_PORT} \
  --name ${CONTAINER_NAME} \
  --restart always \
  --volume hf-hub-cache:/home/ubuntu/.cache/huggingface/hub \
  --gpus=all \
  ${IMAGE}
fi

# Wait for the container to report as running (timeout after 30s)
echo "Waiting for container to be ready..."
for i in {1..30}; do
  if [ "$(docker inspect -f '{{.State.Running}}' ${CONTAINER_NAME})" = "true" ]; then
    echo "Container is running"
    break
  fi
  sleep 1
done

if [ "$(docker inspect -f '{{.State.Running}}' ${CONTAINER_NAME})" != "true" ]; then
  echo "Container failed to start" >&2
  docker ps -a --filter "name=${CONTAINER_NAME}"
  exit 1
fi

# Run a few bash lines inside the running container.
echo "Running default commands inside ${CONTAINER_NAME}"
docker exec -i ${CONTAINER_NAME} bash -s <<'EOF'
set -e
echo "Inside container:"
source .venv/bin/activate
uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX
uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX-in8
uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX-fp16
uv tool run speaches-cli model download suronek/Kokoro-82M-v1.1-zh-ONNX
uv tool run speaches-cli model download speaches-ai/piper-fr_FR-siwis-medium
uv tool run speaches-cli model download speaches-ai/piper-fr_FR-upmc-medium
uv tool run speaches-cli model download speaches-ai/piper-fr_FR-tom-medium
echo "Done"
EOF
fi

echo "Done."
