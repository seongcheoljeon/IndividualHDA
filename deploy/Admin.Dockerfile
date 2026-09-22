FROM postgres:16-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/ihda \
    && useradd --uid 10001 --create-home ihda \
    && mkdir -p /data/backups /data/blobs /data/restored \
    && chown -R ihda:ihda /data
ENV PATH="/opt/ihda/bin:$PATH"
WORKDIR /app
COPY pyproject.toml LICENSE THIRD_PARTY_LICENSES.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --group server
COPY ihda_server ./ihda_server
COPY libs ./libs
USER ihda
ENTRYPOINT ["python", "-m", "ihda_server.cli"]
CMD ["--help"]
