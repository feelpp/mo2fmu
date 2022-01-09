
FROM ghcr.io/feelpp/dymola:2021

USER root
RUN pip3 install click spdlog
RUN pip3 install --editable .



CMD ["mo2fmu"]