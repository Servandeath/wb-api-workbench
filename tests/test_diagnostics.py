from app.core.diagnostics import (
    check_encrypted_storage,
    check_libraries,
    run_diagnostics,
)


def test_run_diagnostics_returns_results():
    results = run_diagnostics()

    assert len(results) > 0
    assert all(result.name for result in results)
    assert all(result.status in {"OK", "FAIL"} for result in results)


def test_core_diagnostics_are_ok():
    results = run_diagnostics()
    failed = [result for result in results if result.status == "FAIL"]

    assert failed == []


def test_check_libraries_ok():
    result = check_libraries()

    assert result.status == "OK"


def test_check_encrypted_storage_round_trips():
    result = check_encrypted_storage()

    assert result.status == "OK"
