
FROM ghcr.io/feelpp/dymola:2025

USER root
COPY pyproject.toml .
COPY src/ ./src/
RUN pip3 install click spdlog xvfbwrapper pathlib
RUN pip3 install --editable .



CMD ["mo2fmu"]