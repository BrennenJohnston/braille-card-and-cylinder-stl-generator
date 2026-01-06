"""
Smoke tests for the minimal backend (client-side generation architecture).

These tests verify that:
1. Basic endpoints are responsive
2. /geometry_spec works for all 4 combinations (card/cylinder × positive/negative)
3. Legacy server-side STL endpoints are deprecated (410 Gone)
"""

from __future__ import annotations

from app.models import CardSettings
from app.utils import braille_to_dots


def _count_raised_dots(lines: list[str], max_cols: int | None = None) -> int:
    """Count raised dots implied by braille characters in lines."""
    total = 0
    for line in lines:
        for col, ch in enumerate(line or ''):
            if max_cols is not None and col >= max_cols:
                break
            dots = braille_to_dots(ch)
            total += sum(1 for d in dots if d == 1)
    return total


def test_health_endpoint(client):
    """Test the /health endpoint returns 200."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert 'status' in data


def test_liblouis_tables_endpoint(client):
    """Test the /liblouis/tables endpoint returns table list."""
    response = client.get('/liblouis/tables')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert 'tables' in data
    assert len(data['tables']) > 0


def test_geometry_spec_card_positive(client):
    """Card + positive plate returns a geometry spec with expected dot/marker counts."""
    lines = ['⠁⠃', '', '', '']
    payload = {
        'lines': lines,
        'plate_type': 'positive',
        'shape_type': 'card',
        'grade': 'g1',
        # Keep the grid small/deterministic for test stability
        'settings': {'grid_rows': 4, 'grid_columns': 4},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data and data.get('shape_type') == 'card'
    assert data.get('plate_type') == 'positive'
    assert 'plate' in data and isinstance(data['plate'], dict)
    assert 'dots' in data and isinstance(data['dots'], list)
    assert 'markers' in data and isinstance(data['markers'], list)

    settings = CardSettings(**payload['settings'])
    assert len(data['markers']) == settings.grid_rows * 2  # rect/character + triangle per row
    assert len(data['dots']) == _count_raised_dots(lines, max_cols=settings.grid_columns)


def test_geometry_spec_card_negative(client):
    """Card + negative plate returns a dense grid of recess dots (all cells)."""
    payload = {
        'lines': ['⠁⠃', '', '', ''],  # ignored for negative cards
        'plate_type': 'negative',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'recess_shape': 1},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data and data.get('shape_type') == 'card'
    assert data.get('plate_type') == 'negative'
    assert 'plate' in data and isinstance(data['plate'], dict)
    assert 'dots' in data and isinstance(data['dots'], list)
    assert 'markers' in data and isinstance(data['markers'], list)

    settings = CardSettings(**payload['settings'])
    assert len(data['markers']) == settings.grid_rows * 2
    assert len(data['dots']) == settings.grid_rows * settings.grid_columns * 6


def test_geometry_spec_cylinder_positive(client):
    """Cylinder + positive plate returns cylinder spec and dot list."""
    lines = ['⠁⠃', '', '', '']
    payload = {
        'lines': lines,
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4},
        'cylinder_params': {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data and data.get('shape_type') == 'cylinder'
    assert data.get('plate_type') == 'positive'
    assert 'cylinder' in data and isinstance(data['cylinder'], dict)
    assert 'dots' in data and isinstance(data['dots'], list)
    assert 'markers' in data and isinstance(data['markers'], list)

    settings = CardSettings(**payload['settings'])
    reserved = 2 if settings.indicator_shapes else 0
    max_text_cols = settings.grid_columns - reserved
    assert len(data['markers']) == settings.grid_rows * 2
    assert len(data['dots']) == _count_raised_dots(lines, max_cols=max_text_cols)


def test_geometry_spec_cylinder_negative(client):
    """Cylinder + negative plate returns all recess dots for all text cells (no text required)."""
    payload = {
        'lines': ['⠁⠃', '', '', ''],  # ignored for negative cylinders (all cells generated)
        'plate_type': 'negative',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'recess_shape': 1},
        'cylinder_params': {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data and data.get('shape_type') == 'cylinder'
    assert data.get('plate_type') == 'negative'
    assert 'cylinder' in data and isinstance(data['cylinder'], dict)
    assert 'dots' in data and isinstance(data['dots'], list)
    assert 'markers' in data and isinstance(data['markers'], list)

    settings = CardSettings(**payload['settings'])
    reserved = 2 if settings.indicator_shapes else 0
    num_text_cols = settings.grid_columns - reserved
    assert len(data['markers']) == settings.grid_rows * 2
    assert len(data['dots']) == settings.grid_rows * num_text_cols * 6


def test_deprecated_endpoints_return_410(client):
    """Legacy server-side endpoints should remain present but return 410 Gone."""
    endpoints = [
        ('/generate_braille_stl', 'POST', {}),
        ('/generate_counter_plate_stl', 'POST', {}),
        ('/lookup_stl', 'GET', None),
        ('/debug/blob_upload', 'GET', None),
    ]

    for path, method, payload in endpoints:
        if method == 'POST':
            resp = client.post(path, json=payload, headers={'Content-Type': 'application/json'})
        else:
            resp = client.get(path)
        assert resp.status_code == 410, f'{path} expected 410, got {resp.status_code}'
        data = resp.get_json()
        assert data and data.get('status') == 'deprecated'


def test_validation_empty_input(client):
    """Empty braille input should still return a valid geometry spec (markers only)."""
    payload = {'lines': ['', '', '', ''], 'plate_type': 'positive', 'shape_type': 'card', 'grade': 'g1', 'settings': {}}

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    data = response.get_json()
    assert data and data.get('shape_type') == 'card'
    assert 'dots' in data and isinstance(data['dots'], list)


def test_validation_invalid_shape_type(client):
    """Test that invalid shape_type returns 400."""
    payload = {'lines': ['⠁'], 'plate_type': 'positive', 'shape_type': 'invalid', 'grade': 'g1', 'settings': {}}

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
