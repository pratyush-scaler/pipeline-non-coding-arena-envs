FROM node:22-bookworm-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c AS node
FROM python:3.11-slim-bookworm@sha256:a36c24f9cbdf4fd0f52d67f0823eeac19c2028c637cecc392d97f980d4fec56b
RUN rm -f /etc/apt/sources.list.d/debian.sources && printf 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20260919T000000Z bookworm main\n' > /etc/apt/sources.list && apt-get -o Acquire::Check-Valid-Until=false update && apt-get install -y --no-install-recommends tmux=3.3a-3 ripgrep procps ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx && npm install -g --no-audit --no-fund @anthropic-ai/claude-code@2.1.283 @openai/codex@0.157.1 && npm cache clean --force && claude --version && codex --version
RUN useradd --create-home --uid 1000 agent
WORKDIR /app
COPY files/ /app/environment/files/
RUN chmod -R a-w /app/environment && mkdir -p /app/deliverables && chown agent:agent /app/deliverables
USER agent
CMD ["sleep", "infinity"]
