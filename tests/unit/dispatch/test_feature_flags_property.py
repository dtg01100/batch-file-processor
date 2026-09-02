"""Property-based tests for dispatch.feature_flags.

Covers the env-var-driven flag accessors and the round-trip behavior
of `set_feature_flag` / `get_feature_flags`.
"""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from webapp.pipeline import get_debug_mode, get_feature_flags, set_feature_flag
from webapp.pipeline.feature_flags import get_strict_testing_mode

pytestmark = [pytest.mark.unit, pytest.mark.property]


_TRUTHY = st.sampled_from(["true", "TRUE", "True", "tRuE"])
_FALSY = st.sampled_from(["false", "FALSE", "False", "0", "yes", "no", ""])
_RANDOM = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        blacklist_characters="\n\r",
    ),
    min_size=0,
    max_size=20,
).filter(lambda s: s.lower() != "true")


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(value=_TRUTHY)
def test_get_debug_mode_true_when_env_is_true(monkeypatch, value: str) -> None:
    """Case-insensitive 'true' -> True."""
    monkeypatch.setenv("DISPATCH_DEBUG_MODE", value)
    assert get_debug_mode() is True


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(value=_FALSY)
def test_get_debug_mode_false_for_non_true(monkeypatch, value: str) -> None:
    """Any value other than case-insensitive 'true' -> False."""
    monkeypatch.setenv("DISPATCH_DEBUG_MODE", value)
    assert get_debug_mode() is False


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(value=_TRUTHY)
def test_get_strict_testing_mode_true_when_env_is_true(monkeypatch, value: str) -> None:
    monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", value)
    assert get_strict_testing_mode() is True


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(value=_FALSY)
def test_get_strict_testing_mode_false_for_non_true(monkeypatch, value: str) -> None:
    monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", value)
    assert get_strict_testing_mode() is False


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(value=_RANDOM)
def test_get_debug_mode_default_false_when_unset(monkeypatch, value: str) -> None:
    """When the env var is unset, the default is False."""
    monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)
    assert get_debug_mode() is False


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=st.sampled_from(["debug_mode", "strict_testing_mode"]))
def test_set_feature_flag_true_sets_env_to_true(monkeypatch, name: str) -> None:
    """set_feature_flag(name, value=True) sets the env var to 'true'."""
    env_var = (
        "DISPATCH_DEBUG_MODE"
        if name == "debug_mode"
        else "DISPATCH_STRICT_TESTING_MODE"
    )
    monkeypatch.delenv(env_var, raising=False)
    set_feature_flag(name, value=True)
    import os

    assert os.environ[env_var].lower() == "true"


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=st.sampled_from(["debug_mode", "strict_testing_mode"]))
def test_set_feature_flag_false_sets_env_to_false(monkeypatch, name: str) -> None:
    """set_feature_flag(name, value=False) sets the env var to 'false'."""
    env_var = (
        "DISPATCH_DEBUG_MODE"
        if name == "debug_mode"
        else "DISPATCH_STRICT_TESTING_MODE"
    )
    monkeypatch.delenv(env_var, raising=False)
    set_feature_flag(name, value=False)
    import os

    assert os.environ[env_var].lower() == "false"


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=st.sampled_from(["debug_mode", "strict_testing_mode"]))
def test_set_feature_flag_round_trip(monkeypatch, name: str) -> None:
    """Setting a flag is observable via the corresponding getter."""
    monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)
    monkeypatch.delenv("DISPATCH_STRICT_TESTING_MODE", raising=False)
    set_feature_flag(name, value=True)
    flags = get_feature_flags()
    assert flags[name] is True
    set_feature_flag(name, value=False)
    flags = get_feature_flags()
    assert flags[name] is False


@settings(max_examples=50)
@given(
    name=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",), blacklist_characters="\n\r"
        ),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s not in ("debug_mode", "strict_testing_mode")),
)
def test_set_feature_flag_unknown_name_raises(name: str) -> None:
    """An unknown flag name raises ValueError and the message names the bad flag."""
    with pytest.raises(ValueError) as exc_info:
        set_feature_flag(name, value=True)
    # The error message must (a) name the bad flag and (b) list valid flags
    # so callers can self-correct without reading source.
    assert "Unknown feature flag" in str(exc_info.value)
    assert name in str(exc_info.value)
    assert "debug_mode" in str(exc_info.value)
    assert "strict_testing_mode" in str(exc_info.value)


def test_get_feature_flags_returns_both_keys(monkeypatch) -> None:
    """get_feature_flags always returns both known flag names."""
    monkeypatch.delenv("DISPATCH_DEBUG_MODE", raising=False)
    monkeypatch.delenv("DISPATCH_STRICT_TESTING_MODE", raising=False)
    flags = get_feature_flags()
    assert "debug_mode" in flags
    assert "strict_testing_mode" in flags
