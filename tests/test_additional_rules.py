"""Testes adicionais: cobrem regras do README que os testes fornecidos não exercitam."""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

from helpers import PROJECT_ROOT, SRC_DIR, run_cli

SAMPLE_CSV = PROJECT_ROOT / "data" / "exemplo-validacao.csv"


def _sample_rows() -> list[dict[str, str]]:
    with SAMPLE_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_validation_sample_matches_readme(tmp_path):
    """A amostra de validação reproduz exatamente as tabelas do README."""
    report = run_cli(tmp_path, _sample_rows())

    assert report["report_version"] == "1.0"
    assert report["summary"] == {
        "total_reservations": 12,
        "confirmed_reservations": 9,
        "cancelled_reservations": 2,
        "no_show_reservations": 1,
        "total_room_nights": 28,
        "total_amount_brl": "7566.00",
        "average_nightly_rate_brl": "270.21",
    }
    assert report["by_month"] == [
        {"month": "2025-01", "reservations": 8, "room_nights": 25, "total_brl": "6684.00"},
        {"month": "2025-02", "reservations": 1, "room_nights": 3, "total_brl": "882.00"},
    ]
    assert report["top_hotels"] == [
        {"hotel_id": "H01", "hotel_name": "Hotel Aurora Paulista", "room_nights": 3, "total_brl": "1200.00"},
        {"hotel_id": "H02", "hotel_name": "Hotel Mirante", "room_nights": 2, "total_brl": "1084.00"},
        {"hotel_id": "H12", "hotel_name": "Hotel Miami Beach", "room_nights": 1, "total_brl": "1000.00"},
        {"hotel_id": "H10", "hotel_name": "Hotel Madrid, Gran Vía", "room_nights": 4, "total_brl": "900.00"},
        {"hotel_id": "H09", "hotel_name": "Hotel Lisboa, Centro", "room_nights": 3, "total_brl": "882.00"},
    ]
    assert list(report) == ["report_version", "generated_at", "summary", "by_month", "top_hotels"]
    assert report["generated_at"].endswith("-03:00")


def test_all_rows_are_read_beyond_200(tmp_path):
    """Nenhuma linha é descartada, mesmo em arquivos com mais de 200 reservas."""
    rows = [{"reservation_id": f"R-{index}", "amount": "10.00"} for index in range(250)]
    report = run_cli(tmp_path, rows)

    assert report["summary"]["total_reservations"] == 250
    assert report["summary"]["confirmed_reservations"] == 250
    assert report["summary"]["total_room_nights"] == 250
    assert report["summary"]["total_amount_brl"] == "2500.00"


def test_nights_across_year_boundary_multiplied_by_rooms(tmp_path):
    """Virada de ano e multiplicação por quartos; o mês é o do check-in."""
    report = run_cli(
        tmp_path,
        [{"checkin_date": "2024-12-30", "checkout_date": "2025-01-02", "rooms": "2", "amount": "600.00"}],
    )
    assert report["summary"]["total_room_nights"] == 6
    assert report["summary"]["average_nightly_rate_brl"] == "100.00"
    assert report["by_month"] == [{"month": "2024-12", "reservations": 1, "room_nights": 6, "total_brl": "600.00"}]


def test_non_confirmed_excluded_from_breakdowns(tmp_path):
    """CANCELLED e NO_SHOW não aparecem em by_month nem em top_hotels."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H01", "checkin_date": "2025-01-10", "checkout_date": "2025-01-11"},
            {
                "reservation_id": "R-2",
                "hotel_id": "H02",
                "status": "NO_SHOW",
                "checkin_date": "2025-03-10",
                "checkout_date": "2025-03-11",
            },
            {
                "reservation_id": "R-3",
                "hotel_id": "H03",
                "status": "CANCELLED",
                "checkin_date": "2025-04-10",
                "checkout_date": "2025-04-11",
            },
        ],
    )
    assert [entry["month"] for entry in report["by_month"]] == ["2025-01"]
    assert [hotel["hotel_id"] for hotel in report["top_hotels"]] == ["H01"]


def test_top_hotels_tie_breaks_by_hotel_id_and_respects_limit(tmp_path):
    """Empate em total_brl é desempatado por hotel_id ascendente; --top limita a lista."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H03", "amount": "500.00"},
            {"reservation_id": "R-2", "hotel_id": "H01", "amount": "500.00"},
            {"reservation_id": "R-3", "hotel_id": "H02", "amount": "500.00"},
            {"reservation_id": "R-4", "hotel_id": "H04", "amount": "900.00"},
        ],
        top=3,
    )
    assert [hotel["hotel_id"] for hotel in report["top_hotels"]] == ["H04", "H01", "H02"]


def test_top_hotels_returns_fewer_when_not_enough_hotels(tmp_path):
    report = run_cli(tmp_path, [{"hotel_id": "H01"}], top=5)
    assert len(report["top_hotels"]) == 1


def test_amounts_summed_exactly_and_rounded_half_up_on_serialization(tmp_path):
    """Soma exata antes de arredondar (0.333 * 3 = 0.999 -> 1.00) e half-up (0.125 -> 0.13)."""
    summed = run_cli(tmp_path, [{"reservation_id": f"R-{i}", "amount": "0.333"} for i in range(3)])
    assert summed["summary"]["total_amount_brl"] == "1.00"

    half = run_cli(tmp_path, [{"amount": "0.125"}])
    assert half["summary"]["total_amount_brl"] == "0.13"


def test_currency_conversion_keeps_decimal_precision(tmp_path):
    """EUR 0.01 * 5.88 = 0.0588; dez reservas somam 0.588 -> 0.59 (sem erro de float)."""
    report = run_cli(tmp_path, [{"reservation_id": f"R-{i}", "currency": "EUR", "amount": "0.01"} for i in range(10)])
    assert report["summary"]["total_amount_brl"] == "0.59"


def test_no_confirmed_reservations_yields_zeroes(tmp_path):
    report = run_cli(tmp_path, [{"status": "CANCELLED"}, {"reservation_id": "R-2", "status": "NO_SHOW"}])
    assert report["summary"]["total_room_nights"] == 0
    assert report["summary"]["total_amount_brl"] == "0.00"
    assert report["summary"]["average_nightly_rate_brl"] == "0.00"
    assert report["by_month"] == []
    assert report["top_hotels"] == []


def _run_raw(args: list[str]) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "onfly_report", *args],
        cwd=str(PROJECT_ROOT),
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_exit_code_2_for_missing_input(tmp_path):
    rates = _write(tmp_path / "rates.csv", "currency,rate_to_brl\nBRL,1\n")
    result = _run_raw(["--input", str(tmp_path / "nao-existe.csv"), "--rates", str(rates)])
    assert result.returncode == 2


def test_exit_code_2_for_invalid_top(tmp_path):
    rates = _write(tmp_path / "rates.csv", "currency,rate_to_brl\nBRL,1\n")
    result = _run_raw(["--input", str(SAMPLE_CSV), "--rates", str(rates), "--top", "0"])
    assert result.returncode == 2


def test_exit_code_2_for_currency_without_rate(tmp_path):
    rates = _write(tmp_path / "rates.csv", "currency,rate_to_brl\nBRL,1\n")
    output = tmp_path / "report.json"
    result = _run_raw(["--input", str(SAMPLE_CSV), "--rates", str(rates), "--output", str(output)])
    assert result.returncode == 2
    assert not output.exists()
