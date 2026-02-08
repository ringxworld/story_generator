FROM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        make \
        cmake \
        g++ \
        clang-format \
        cppcheck \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/local/bin/python
RUN pip3 install --no-cache-dir uv

WORKDIR /workspace

COPY . .

RUN uv sync --all-groups
RUN npm ci --prefix web

CMD ["bash", "-lc", "make check && uv run mkdocs build --strict"]
