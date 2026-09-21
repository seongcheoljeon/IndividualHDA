"""Isolated loopback HTTP server for transport integration tests; never imports Qt."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

# Direct script execution puts tests/ rather than the application root on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402

from ihda_server.app import make_app  # noqa: E402
from ihda_server.auth import TokenIdentity  # noqa: E402
from ihda_server.catalog import SqlCatalog  # noqa: E402
from ihda_server.database import make_engine  # noqa: E402
from ihda_server.service import LibraryService  # noqa: E402
from ihda_server.storage import FileBlobStore  # noqa: E402

if __name__ == "__main__":
    configuration = json.loads(os.environ["IHDA_HTTP_TEST_CONFIG"])
    engine = make_engine(configuration["url"])
    if configuration["schema"] is not None:
        engine = engine.execution_options(
            schema_translate_map={None: configuration["schema"]}
        )
    application = make_app(
        LibraryService(
            SqlCatalog(engine),
            FileBlobStore(Path(configuration["storage"]), max_size=4096),
            TokenIdentity(engine),
        ),
        max_upload=4096,
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    ready = Path(configuration["ready"])
    temporary = ready.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"port": listener.getsockname()[1]}), encoding="utf-8"
    )
    temporary.replace(ready)
    try:
        uvicorn.Server(
            uvicorn.Config(application, log_level="error", access_log=False)
        ).run(sockets=[listener])
    finally:
        listener.close()
        engine.dispose()
