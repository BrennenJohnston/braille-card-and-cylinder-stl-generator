"""
Smoke tests for the minimal backend (client-side generation architecture).

These tests verify that:
1. Basic endpoints are responsive
2. /geometry_spec works for all 4 combinations (card/cylinder × positive/negative)
3. Legacy server-side STL endpoints are deprecated (410 Gone)
"""

from __future__ import annotations

import pytest

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


def test_validation_card_column_overflow(client):
    """
    SAFETY-CRITICAL: Test that card column overflow returns 400.

    This tests PR-2 fix for silent truncation (S0 bug).
    Previously, characters exceeding grid_columns were silently dropped
    at geometry_spec.py:211-212. Now they must fail with validation error.
    """
    # Create a braille line longer than grid_columns
    # 10 braille characters but only 4 columns allowed
    long_braille_line = '⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚'  # 10 characters
    payload = {
        'lines': [long_braille_line, '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4},  # Only 4 columns allowed
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400, f'Expected 400 for column overflow, got {response.status_code}: {response.data}'
    data = response.get_json()
    assert 'error' in data
    # Error message should mention the overflow
    assert (
        'column' in data['error'].lower() or 'overflow' in data['error'].lower() or 'exceeds' in data['error'].lower()
    )


def test_validation_cylinder_column_overflow(client):
    """
    SAFETY-CRITICAL: Test that cylinder column overflow returns 400.

    This tests PR-2 fix for silent truncation (S0 bug).
    Previously, characters were silently truncated via [:max_cols] at
    geometry_spec.py:602. Now they must fail with validation error.
    """
    # Cylinders reserve 2 columns for indicators, so with grid_columns=4,
    # only 2 columns are available for text
    long_braille_line = '⠁⠃⠉⠙⠑'  # 5 characters, but only 2 available after indicator reservation
    payload = {
        'lines': [long_braille_line, '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'indicator_shapes': 1},  # 2 reserved for indicators
        'cylinder_params': {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400, (
        f'Expected 400 for cylinder overflow, got {response.status_code}: {response.data}'
    )
    data = response.get_json()
    assert 'error' in data


def test_validation_cylinder_no_indicators_overflow(client):
    """
    Test cylinder column overflow when indicators are disabled.

    With indicators disabled, all grid_columns are available for text.
    This test verifies the indicator_shapes=0 path.
    """
    # 10 braille characters but only 4 columns allowed (no indicator reservation)
    long_braille_line = '⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚'  # 10 characters
    payload = {
        'lines': [long_braille_line, '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {
            'grid_rows': 4,
            'grid_columns': 4,
            'indicator_shapes': 0,
        },  # No indicators, all 4 columns available
        'cylinder_params': {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400, f'Expected 400 for overflow, got {response.status_code}: {response.data}'
    data = response.get_json()
    assert 'error' in data


def test_validation_card_exact_fit_succeeds(client):
    """Test that card with exact column count succeeds (boundary test)."""
    # Exactly 4 braille characters with 4 columns = should succeed
    exact_fit_line = '⠁⠃⠉⠙'  # 4 characters
    payload = {
        'lines': [exact_fit_line, '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4},
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 200, f'Expected 200 for exact fit, got {response.status_code}: {response.data}'
    data = response.get_json()
    assert data and data.get('shape_type') == 'card'


def test_validation_negative_plate_skips_column_check(client):
    """Test that negative plates skip column validation (they generate all dots)."""
    # Long braille line for a negative plate - should succeed because
    # negative plates ignore the text content
    long_braille_line = '⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚'  # 10 characters
    payload = {
        'lines': [long_braille_line, '', '', ''],
        'plate_type': 'negative',  # Negative plate
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'recess_shape': 1},
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    # Negative plates should succeed regardless of line length
    # because they generate recesses for all cells, ignoring text
    assert response.status_code == 200, f'Expected 200 for negative plate, got {response.status_code}: {response.data}'


# =============================================================================
# PR-8: braille_to_dots() Strict Mode Tests (Defense-in-Depth)
# =============================================================================


def test_braille_to_dots_valid_character():
    """Test that valid braille characters return correct dot patterns."""
    # ⠁ (U+2801) = dot 1 only
    result = braille_to_dots('⠁')
    assert result == [1, 0, 0, 0, 0, 0], f'Expected [1,0,0,0,0,0] for ⠁, got {result}'

    # ⠓ (U+2813) = dots 1, 2, 5 (binary: 010011 = 1+2+16)
    result = braille_to_dots('⠓')
    assert result == [1, 1, 0, 0, 1, 0], f'Expected [1,1,0,0,1,0] for ⠓, got {result}'

    # ⠿ (U+283F) = all 6 dots (binary: 111111 = 63)
    result = braille_to_dots('⠿')
    assert result == [1, 1, 1, 1, 1, 1], f'Expected [1,1,1,1,1,1] for ⠿, got {result}'


def test_braille_to_dots_space_returns_empty():
    """Test that space character returns empty cell (valid blank braille)."""
    result = braille_to_dots(' ')
    assert result == [0, 0, 0, 0, 0, 0], f'Expected empty cell for space, got {result}'


def test_braille_to_dots_empty_returns_empty():
    """Test that empty string returns empty cell."""
    result = braille_to_dots('')
    assert result == [0, 0, 0, 0, 0, 0], f'Expected empty cell for empty string, got {result}'

    result = braille_to_dots(None)
    assert result == [0, 0, 0, 0, 0, 0], f'Expected empty cell for None, got {result}'


def test_braille_to_dots_invalid_character_raises():
    """
    SAFETY-CRITICAL: Test that non-braille characters raise ValueError.

    This tests PR-8 defense-in-depth fix. Previously, non-braille characters
    silently returned empty dots [0,0,0,0,0,0], which could cause silent
    data loss if validation was bypassed. Now they must raise ValueError.
    """
    # ASCII letter should raise
    with pytest.raises(ValueError) as exc_info:
        braille_to_dots('X')
    assert 'Invalid braille character' in str(exc_info.value)
    assert 'U+0058' in str(exc_info.value)  # Unicode code point for 'X'

    # Number should raise
    with pytest.raises(ValueError) as exc_info:
        braille_to_dots('5')
    assert 'Invalid braille character' in str(exc_info.value)

    # Special character should raise
    with pytest.raises(ValueError) as exc_info:
        braille_to_dots('@')
    assert 'Invalid braille character' in str(exc_info.value)


def test_braille_to_dots_unicode_outside_braille_range_raises():
    """Test that Unicode characters outside braille range raise ValueError."""
    # Unicode character just before braille block
    with pytest.raises(ValueError):
        braille_to_dots('\u27ff')  # U+27FF is just before U+2800

    # Unicode character just after braille block
    with pytest.raises(ValueError):
        braille_to_dots('\u2900')  # U+2900 is just after U+28FF

    # Common Unicode character (emoji)
    with pytest.raises(ValueError):
        braille_to_dots('😀')


def test_braille_to_dots_braille_blank_pattern():
    """Test that braille blank pattern ⠀ (U+2800) returns empty cell."""
    # U+2800 is the "braille pattern blank" - a valid braille character with no dots
    result = braille_to_dots('⠀')
    assert result == [0, 0, 0, 0, 0, 0], f'Expected empty cell for ⠀ (U+2800), got {result}'
