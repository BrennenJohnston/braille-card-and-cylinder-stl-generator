"""
Golden/regression tests for geometry specs (/geometry_spec).

The project now uses client-side CSG for STL generation; the backend is minimal
and only returns deterministic geometry specs (positions + parameters).

These tests validate the geometry spec response shape and key invariants to
catch unintended changes that would break client-side generation.
"""

import json
from pathlib import Path

import pytest

from app.models import CardSettings
from app.utils import braille_to_dots


@pytest.fixture(scope='module')
def fixtures_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / 'fixtures'


def load_fixture_metadata(fixtures_dir, fixture_name):
    """Load metadata for a golden fixture."""
    metadata_path = fixtures_dir / f'{fixture_name}.json'
    with open(metadata_path) as f:
        return json.load(f)


def _count_raised_dots(lines: list[str], max_cols: int | None = None) -> int:
    total = 0
    for line in lines:
        for col, ch in enumerate(line or ''):
            if max_cols is not None and col >= max_cols:
                break
            dots = braille_to_dots(ch)
            total += sum(1 for d in dots if d == 1)
    return total


def _expected_counts(payload: dict) -> tuple[int, int]:
    """
    Return (expected_dots, expected_markers) for /geometry_spec based on the
    behavior in app/geometry_spec.py.
    """
    settings = CardSettings(**payload.get('settings', {}))
    shape_type = payload.get('shape_type', 'card')
    plate_type = payload.get('plate_type', 'positive')
    lines = payload.get('lines', ['', '', '', ''])

    indicator_shapes = bool(getattr(settings, 'indicator_shapes', 1))
    expected_markers = settings.grid_rows * 2 if indicator_shapes else 0

    if shape_type == 'card':
        if plate_type == 'negative':
            expected_dots = settings.grid_rows * settings.grid_columns * 6
        else:
            expected_dots = _count_raised_dots(lines, max_cols=settings.grid_columns)
        return expected_dots, expected_markers

    # cylinder
    reserved = 2 if indicator_shapes else 0
    max_text_cols = settings.grid_columns - reserved

    if plate_type == 'negative':
        expected_dots = settings.grid_rows * max_text_cols * 6
    else:
        expected_dots = _count_raised_dots(lines, max_cols=max_text_cols)

    return expected_dots, expected_markers


@pytest.mark.parametrize(
    'fixture_name',
    ['card_positive_small', 'card_counter_small', 'cylinder_positive_small', 'cylinder_counter_small'],
)
def test_golden_geometry_spec(client, fixtures_dir, fixture_name):
    """Validate /geometry_spec invariants for each fixture payload."""
    metadata = load_fixture_metadata(fixtures_dir, fixture_name)
    payload = metadata['request_payload']

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data is not None

    assert data.get('shape_type') == payload.get('shape_type')
    assert data.get('plate_type') == payload.get('plate_type')
    assert isinstance(data.get('dots'), list)
    assert isinstance(data.get('markers'), list)

    expected_dots, expected_markers = _expected_counts(payload)
    assert len(data['markers']) == expected_markers
    assert len(data['dots']) == expected_dots

    # Minimal structural validation on dot specs
    if data['shape_type'] == 'card':
        assert 'plate' in data
        if data['dots']:
            d0 = data['dots'][0]
            assert 'x' in d0 and 'y' in d0 and 'z' in d0
            assert 'type' in d0
            assert 'params' in d0 and isinstance(d0['params'], dict)
    else:
        assert 'cylinder' in data
        if data['dots']:
            d0 = data['dots'][0]
            assert 'x' in d0 and 'y' in d0 and 'z' in d0
            assert 'theta' in d0 and 'radius' in d0
            assert 'type' in d0
            assert 'params' in d0 and isinstance(d0['params'], dict)
