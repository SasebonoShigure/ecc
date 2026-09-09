"""Native capability boundary fixtures for ECC wrapper tests."""

import sys
from types import SimpleNamespace

import pytest


class NativeUnavailableError(RuntimeError):
    status_code = "unsupported"
    state = "created"
    capability_reason = "backend_unavailable"

    def __init__(self, request):
        super().__init__("CUDA build/device is unavailable")
        self.request = request


@pytest.fixture
def unavailable_cuda_native(monkeypatch):
    def resolve(request):
        raise NativeUnavailableError(request)

    native = SimpleNamespace(
        incregpusta_debug_checks_enabled=False,
        StaSessionError=NativeUnavailableError,
        create_incremental_sta_session=lambda request: pytest.fail("session creation must not run"),
        resolve_sta_execution=resolve,
    )
    monkeypatch.setitem(sys.modules, "ecc_tools_bin.ecc_py", native)
    return native
