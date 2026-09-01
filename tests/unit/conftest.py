import httpx2
import logging
import pytest
import tempfile
import threading

from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		kwargs["directory"] = Path(__file__).parent.parent / "http_data"
		super().__init__(*args, **kwargs)


@pytest.fixture
def http_server(server_address: str = "127.0.0.1", server_port: int = 8079):
	server = HTTPServer((server_address, server_port), Handler)
	thread = threading.Thread(target=server.serve_forever)
	thread.daemon = True
	thread.start()
	address = f"http://{server_address}:{server_port}"

	with httpx2.Client(base_url=address) as client:
		response = client.get("/index.html")
		assert response.status_code == 200

	yield address
	server.shutdown()


@pytest.fixture
def default_search_query():
	with tempfile.TemporaryDirectory() as tmpdir:
		yield {
			"open": True,
			"sortby": "relevant",
			"results_dir": tmpdir,
			"name": "test",
			"maximum_scraped": 1
		}


@pytest.fixture
def default_logger():
	logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
	logger = logging.getLogger("exsclaim-test")
	yield logger
