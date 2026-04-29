# Two-stage Dockerfile for the py-bitcoinkernel workshop.
#
# The `minimal` target installs only py-bitcoinkernel and runs the stdin node —
# paste a hex-encoded block, see the validation result.
#
# The `full` target adds websockets + qrcode so the node can serve a phone-facing
# WebSocket + HTTPS page. Publish port 8765, set PBK_ADVERTISE_HOST to your
# laptop's LAN IP so the phone can reach the container's published port.
#
# Build:
#   docker build --target minimal -t pbk-workshop:minimal .
#   docker build --target full    -t pbk-workshop:full    .

FROM python:3.12-slim AS base

# openssl is required at runtime to mint the self-signed cert (full mode only,
# but harmless in minimal). `ca-certificates` lets uv download py-bitcoinkernel.
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# uv is the fastest way to install Python deps. Grab a pinned copy.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install the venv outside the working directory so a host bind-mount onto
# /workshop (used in compose for live source editing) doesn't shadow it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH=/opt/venv/bin:$PATH

# /data is for cert/state that would otherwise want to live in /workshop, which
# is read-only when bind-mounted from the host.
RUN mkdir -p /data
WORKDIR /workshop

# Copy the dependency manifest.
COPY pyproject.toml ./


FROM base AS minimal

RUN uv sync --no-dev
COPY node.py run_stdin.py tree_view.py ./
# stdin requires an interactive tty: `docker run -it pbk-workshop:minimal`
CMD ["python", "run_stdin.py"]


FROM base AS full

RUN uv sync --extra full --no-dev
COPY node.py server.py run_server.py index.html tree_view.py ./
ENV PBK_CERT_DIR=/data/.certs
EXPOSE 8765
CMD ["python", "run_server.py"]
