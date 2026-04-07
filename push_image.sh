DOCKER_REGISTRY_PASSWORD=$(cat .docker_registry_password)
export DOCKER_REGISTRY_PASSWORD
echo "${DOCKER_REGISTRY_PASSWORD}" | docker login registry.test.exodushk.com -u admin --password-stdin

TIME_TAG=$(date +%y%m%d-%H%M)

WEBHOOK_PROXY_TAG=registry.test.exodushk.com/ops/webhook-proxy:0.0.3-"${TIME_TAG}"
docker tag webhook-proxy-webhook-proxy:latest "${WEBHOOK_PROXY_TAG}"
docker push "${WEBHOOK_PROXY_TAG}"
echo "${WEBHOOK_PROXY_TAG}"
