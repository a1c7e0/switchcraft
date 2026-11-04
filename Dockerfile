FROM devkitpro/devkita64@sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282
RUN if command -v apt-get >/dev/null; then apt-get update && apt-get install -y --no-install-recommends pkg-config libcurl4-openssl-dev libssl-dev openssl && rm -rf /var/lib/apt/lists/*; else pacman -S --needed --noconfirm pkgconf curl openssl; fi
WORKDIR /src
ENV DEVKITPRO=/opt/devkitpro
# Run with a source bind mount. Dependency downloads happen at runtime so the
# managed environment's CA bundle can be mounted without storing it in an image.
CMD ["bash", "scripts/build-all.sh"]
