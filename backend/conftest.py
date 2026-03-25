import os
import sys
import asyncio
import inspect

# Ensure the backend folder itself is on sys.path so imports like `routing.*` and `chatbot` work in tests
BACKEND_DIR = os.path.dirname(__file__)
sys.path.insert(0, BACKEND_DIR)


def pytest_configure(config):
	# Register marker so pytest doesn't warn when plugin is unavailable.
	config.addinivalue_line("markers", "asyncio: mark test as asyncio coroutine")


def pytest_pyfunc_call(pyfuncitem):
	"""Run async tests via asyncio when pytest-asyncio is not installed."""
	test_func = pyfuncitem.obj
	if not inspect.iscoroutinefunction(test_func):
		return None

	kwargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
	asyncio.run(test_func(**kwargs))
	return True
