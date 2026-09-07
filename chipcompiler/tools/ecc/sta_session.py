"""Python lifecycle wrapper for the native incremental-STA session shell."""

from collections.abc import Callable, Mapping
from types import TracebackType
from typing import Protocol, TypeVar

from chipcompiler.tools.ecc.sta_mode import (
    StaBackend,
    StaCapabilityReason,
    StaExecutionContractError,
    StaExecutionRecord,
    StaExecutionRequest,
    StaFallbackPolicy,
    StaSessionError,
    StaSessionStatusCode,
    StaUnsupportedError,
    StaUpdateStrategy,
    execution_record_from_mapping,
    preflight_stage1_request,
)
from chipcompiler.tools.ecc.sta_snapshot import (
    StaAnalysisContext,
    StaReleaseObservationAction,
    StaSnapshotObservation,
    StaSnapshotState,
    corner_fingerprint,
    snapshot_observation_from_mapping,
    sta_analysis_context_to_native_mapping,
    validate_snapshot_observation_transition,
    validate_sta_analysis_context,
)


class _NativeStaSession(Protocol):
    @property
    def state(self) -> str: ...

    @property
    def session_token(self) -> object: ...

    @property
    def csr_snapshot_observation(self) -> object: ...

    def initialize(
        self,
        *,
        analysis_context: Mapping[str, str],
        config: str,
        config_dict: Mapping[str, str],
    ) -> None: ...

    def run_full_baseline(self) -> Mapping[str, object]: ...

    def close(self) -> None: ...


class _NativeStaModule(Protocol):
    @property
    def incregpusta_debug_checks_enabled(self) -> bool: ...

    StaSessionError: type[Exception]

    def create_incremental_sta_session(self, request: Mapping[str, str]) -> _NativeStaSession: ...


_NATIVE_REQUEST_KEYS = frozenset({"backend", "update_strategy", "fallback_policy"})
_NATIVE_SESSION_STATES = frozenset(
    {"created", "initialized", "baseline_executed", "poisoned", "closed"}
)
_MAX_SESSION_TOKEN = (1 << 64) - 1
_ResultT = TypeVar("_ResultT")


def _native_attribute(error: BaseException, name: str) -> object:
    try:
        return getattr(error, name)
    except AttributeError as exc:
        raise StaExecutionContractError(
            f"native StaSessionError is missing attribute {name!r}"
        ) from exc


def _native_string(name: str, value: object) -> str:
    if type(value) is not str:
        raise StaExecutionContractError(
            f"native StaSessionError {name} must be a string; got {type(value).__name__}"
        )
    return value


def _native_request(value: object) -> StaExecutionRequest:
    if not isinstance(value, Mapping):
        raise StaExecutionContractError("native StaSessionError request must be a mapping")

    request_values: dict[str, object] = {}
    for key, item in value.items():
        if type(key) is not str:
            raise StaExecutionContractError(
                f"native StaSessionError request key must be a string; got {type(key).__name__}"
            )
        request_values[key] = item
    keys = set(request_values)
    if keys != _NATIVE_REQUEST_KEYS:
        missing = sorted(_NATIVE_REQUEST_KEYS - keys)
        extra = sorted(keys - _NATIVE_REQUEST_KEYS)
        raise StaExecutionContractError(
            f"native StaSessionError request keys differ: missing={missing}, extra={extra}"
        )

    try:
        return StaExecutionRequest(
            backend=StaBackend(_native_string("request.backend", request_values["backend"])),
            update_strategy=StaUpdateStrategy(
                _native_string("request.update_strategy", request_values["update_strategy"])
            ),
            fallback_policy=StaFallbackPolicy(
                _native_string("request.fallback_policy", request_values["fallback_policy"])
            ),
        )
    except ValueError as exc:
        raise StaExecutionContractError(f"invalid native StaSessionError request: {exc}") from exc


def _parent_session_error(
    native_error: BaseException,
    expected_request: StaExecutionRequest,
) -> StaSessionError:
    request = _native_request(_native_attribute(native_error, "request"))
    if request != expected_request:
        raise StaExecutionContractError(
            "native StaSessionError request differs from the immutable session request"
        )

    status_token = _native_string("status_code", _native_attribute(native_error, "status_code"))
    try:
        status_code = StaSessionStatusCode(status_token)
    except ValueError as exc:
        raise StaExecutionContractError(
            f"invalid native StaSessionError status_code: {status_token!r}"
        ) from exc

    state = _native_string("state", _native_attribute(native_error, "state"))
    if state not in _NATIVE_SESSION_STATES:
        raise StaExecutionContractError(f"invalid native StaSessionError state: {state!r}")

    capability_value = _native_attribute(native_error, "capability_reason")
    capability_reason = None
    if capability_value is not None:
        capability_token = _native_string("capability_reason", capability_value)
        try:
            capability_reason = StaCapabilityReason(capability_token)
        except ValueError as exc:
            raise StaExecutionContractError(
                f"invalid native StaSessionError capability_reason: {capability_token!r}"
            ) from exc

    message = str(native_error)
    if status_code is StaSessionStatusCode.UNSUPPORTED:
        if capability_reason is None:
            raise StaExecutionContractError(
                "native unsupported status requires a capability_reason"
            )
        return StaUnsupportedError(
            request=request,
            state=state,
            message=message,
            capability_reason=capability_reason,
        )
    if capability_reason is not None:
        raise StaExecutionContractError(
            "native lifecycle status must not include a capability_reason"
        )
    return StaSessionError(
        request=request,
        status_code=status_code,
        state=state,
        message=message,
    )


def _request_payload(request: StaExecutionRequest) -> dict[str, str]:
    return {
        "backend": request.backend.value,
        "update_strategy": request.update_strategy.value,
        "fallback_policy": request.fallback_policy.value,
    }


def _require_session_token(value: object) -> int:
    if type(value) is not int or not 0 < value <= _MAX_SESSION_TOKEN:
        raise StaExecutionContractError("native STA session token must be a nonzero uint64")
    return value


class IncrementalStaSession:
    """Own one native STA lifecycle and validate its execution telemetry."""

    def __init__(
        self,
        native_module: _NativeStaModule,
        request: StaExecutionRequest,
        analysis_context: StaAnalysisContext,
        *,
        config: str = "",
        config_dict: Mapping[str, str] | None = None,
    ) -> None:
        self._native_module = native_module
        self._debug_checks = native_module.incregpusta_debug_checks_enabled
        if type(self._debug_checks) is not bool:
            raise StaExecutionContractError("native IncreGPUSTA build flag must be a bool")
        self._request = request
        validate_sta_analysis_context(analysis_context)
        self._analysis_context = analysis_context
        self._expected_record = preflight_stage1_request(request)
        self._config = config
        self._config_dict = dict(config_dict or {})
        self._native_session: _NativeStaSession | None = None
        self._session_token: int | None = None
        self._active_observation: StaSnapshotObservation | None = None
        self._snapshot_observation: StaSnapshotObservation | None = None
        self._entered = False
        self._closed = False

    @property
    def request(self) -> StaExecutionRequest:
        return self._request

    @property
    def snapshot_observation(self) -> StaSnapshotObservation | None:
        return self._snapshot_observation

    @property
    def state(self) -> str:
        if self._native_session is not None:
            return self._native_session.state
        if self._closed:
            return "closed"
        return "created"

    def __enter__(self) -> "IncrementalStaSession":
        if self._entered or self._closed:
            raise RuntimeError("STA session may only be entered once")

        try:
            native_session = self._call_native(
                lambda: self._native_module.create_incremental_sta_session(
                    _request_payload(self._request)
                )
            )
            self._native_session = native_session
            initialize_result = self._call_native(
                lambda: native_session.initialize(
                    analysis_context=sta_analysis_context_to_native_mapping(self._analysis_context),
                    config=self._config,
                    config_dict=self._config_dict,
                )
            )
            if initialize_result is not None:
                raise StaExecutionContractError(
                    "native STA session initialize must return None on success"
                )
            self._session_token = _require_session_token(
                self._call_native(lambda: native_session.session_token)
            )
        except BaseException as primary_error:
            try:
                self.close()
            except BaseException as cleanup_error:
                raise primary_error.with_traceback(primary_error.__traceback__) from cleanup_error
            raise

        self._entered = True
        return self

    def run_full_baseline(self) -> StaExecutionRecord:
        if not self._entered or self._closed or self._native_session is None:
            raise RuntimeError("STA session is not active")

        native_session = self._native_session
        record = execution_record_from_mapping(self._call_native(native_session.run_full_baseline))
        if record != self._expected_record:
            raise StaExecutionContractError(
                "native STA execution record differs from the stage-1 preflight outcome"
            )
        if not self._debug_checks:
            return record
        raw_observation = self._call_native(lambda: native_session.csr_snapshot_observation)
        observation = snapshot_observation_from_mapping(raw_observation)
        if self._request.update_strategy is StaUpdateStrategy.FULL:
            if observation is not None:
                raise StaExecutionContractError(
                    "cpu/full native STA session must not expose a snapshot observation"
                )
        else:
            if observation is None:
                raise StaExecutionContractError(
                    "cpu/incremental native STA session requires a ready snapshot observation"
                )
            if (
                observation.state is not StaSnapshotState.READY
                or observation.identity.graph_generation != 0
                or observation.identity.session_token != self._session_token
                or observation.identity.corner_fingerprint
                != corner_fingerprint(self._analysis_context)
                or observation.last_rejection is not None
                or observation.last_invalidation is not None
                or observation.timing_ms.reference is not None
                or observation.timing_ms.scatter is not None
            ):
                raise StaExecutionContractError(
                    "native initial snapshot observation violates the capture contract"
                )
        self._active_observation = observation
        self._snapshot_observation = observation
        return record

    def close(self) -> None:
        if self._closed:
            return

        native_session = self._native_session
        active_observation = self._active_observation
        try:
            if native_session is None:
                return

            close_result = self._call_native(native_session.close)
            if not self._debug_checks:
                if close_result is not None:
                    raise StaExecutionContractError(
                        "native STA session close must return None on success"
                    )
                return
            released_error: BaseException | None = None
            released_observation: StaSnapshotObservation | None = None
            try:
                raw_observation = self._call_native(lambda: native_session.csr_snapshot_observation)
                released_observation = snapshot_observation_from_mapping(raw_observation)
                validate_snapshot_observation_transition(
                    active_observation,
                    released_observation,
                    StaReleaseObservationAction(),
                )
            except BaseException as error:
                released_error = error

            if close_result is not None:
                wrong_return = StaExecutionContractError(
                    "native STA session close must return None on success"
                )
                if released_error is not None:
                    raise wrong_return from released_error
                raise wrong_return
            if released_error is not None:
                raise released_error

            self._snapshot_observation = released_observation
        except BaseException:
            self._snapshot_observation = None
            raise
        finally:
            self._active_observation = None
            self._native_session = None
            self._closed = True

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            self.close()
        except BaseException as cleanup_error:
            if exc is None:
                raise
            raise exc.with_traceback(traceback) from cleanup_error
        return False

    def _call_native(self, operation: Callable[[], _ResultT]) -> _ResultT:
        try:
            return operation()
        except self._native_module.StaSessionError as native_error:
            try:
                parent_error = _parent_session_error(native_error, self._request)
            except StaExecutionContractError as contract_error:
                raise contract_error from native_error
            raise parent_error from native_error
