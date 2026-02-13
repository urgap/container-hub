ARG BASEIMAGE

FROM ${BASEIMAGE}

ARG URGAP

RUN addgroup --system nonroot && \
    adduser --system \
      --ingroup nonroot \
      --home /home/nonroot \
      nonroot

COPY ${URGAP} /home/nonroot

ENV HOME=/home/nonroot
ENV VENV_PATH=$HOME/venv
ENV PATH=$VENV_PATH/bin:$PATH
USER nonroot

RUN python -m venv "$VENV_PATH" --system-site-packages

RUN pip install uv
RUN uv pip install /home/nonroot/${URGAP}["all"]

WORKDIR $HOME

ENTRYPOINT ["uctl", "run", "upi-server", "-n", "FilterTabularToCSV:1.0.0", "-n", "FilterTabularToParquet:1.0.0", "-n", "FilterTabularToXlsx:1.0.0", "-n", "FilterTabularToCSV:latest", "-n", "FilterTabularToParquet:latest", "-n", "FilterTabularToXlsx:latest"]
