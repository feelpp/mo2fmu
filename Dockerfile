
FROM ghcr.io/feelpp/dymola:2021

USER root
RUN pip3 install click spdlog
# Own local files to user to avoid permissions problems
RUN git clone https://github.com/feelpp/mo2fmu.git && pip install --editable mo2fmu
RUN chown -R user:user /home/user
USER user

CMD ["python3"]