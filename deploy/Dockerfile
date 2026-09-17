FROM python:3.11-slim-bookworm
WORKDIR /app
COPY requirements-server.txt LICENSE THIRD_PARTY_LICENSES.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt \
    && useradd --uid 10001 --create-home ihda \
    && mkdir -p /data/blobs && chown -R ihda:ihda /data
COPY ihda_server ./ihda_server
COPY libs ./libs
USER ihda
EXPOSE 8000
CMD ["uvicorn", "ihda_server.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
