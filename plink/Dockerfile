ARG BASEIMAGE

# Stage 1: Get plink binary from base image
FROM ${BASEIMAGE} AS plink-source
# Find and copy plink to known location
RUN cp $(which plink2 || which plink) /tmp/plink2

# Stage 2: Build final image with Python 3.11 + plink
FROM python:3.11-slim

# Copy plink binary from base image
COPY --from=plink-source /tmp/plink2 /usr/local/bin/plink2

# Create nonroot user and venv
RUN useradd -m -s /bin/bash nonroot
USER nonroot
WORKDIR /home/nonroot

RUN python -m venv /home/nonroot/venv && \
    /home/nonroot/venv/bin/pip install --upgrade pip && \
    /home/nonroot/venv/bin/pip install urgap["all"]

# Add venv to PATH
ENV PATH="/home/nonroot/venv/bin:$PATH"

# Run upi-server with PlinkFreq node
ENTRYPOINT ["/home/nonroot/venv/bin/uctl", "run", "upi-server"]
CMD ["-n", "PlinkFreq:latest"]
