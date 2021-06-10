FROM continuumio/miniconda3

RUN conda update conda && conda install pip

COPY environment.yml /tmp/environment.yml
RUN conda env update -f /tmp/environment.yml -n base && rm /tmp/environment.yml

COPY . /tmp/stactools-sentinel2
RUN cd /tmp/stactools-sentinel2 && pip install . && rm -rf /tmp/stactools-sentinel2

ENTRYPOINT [ "python", "-m", "stactools.cli" ]
