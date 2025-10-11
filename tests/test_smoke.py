"""
Smoke tests for braille STL generator.

These tests verify that:
1. Basic endpoints are responsive
2. All 4 STL types can be generated (card positive, card counter, cylinder positive, cylinder counter)
3. Generated STLs are non-empty, loadable, and have valid geometry
"""

import io

import trimesh


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


def test_generate_card_positive(client):
    """Test generating a positive card plate with braille text."""
    payload = {
        'lines': ['⠁', '⠃', '⠉', '⠙'],  # Braille characters A, B, C, D
        'plate_type': 'positive',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {
            'card_width': 85.0,
            'card_height': 55.0,
            'card_thickness': 2.0,
            'dot_height': 0.5,
            'dot_base_diameter': 1.5,
        },
    }

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    # Check response
    assert response.status_code == 200, f'Expected 200, got {response.status_code}: {response.data}'
    assert len(response.data) > 0, 'STL data is empty'

    # Verify STL is loadable and has valid geometry
    mesh = trimesh.load(io.BytesIO(response.data), file_type='stl')
    assert mesh is not None, 'Failed to load STL mesh'
    assert len(mesh.faces) > 0, 'Mesh has no faces'
    assert mesh.is_watertight or len(mesh.faces) > 100, 'Mesh should be watertight or have substantial geometry'


def test_generate_card_counter(client):
    """Test generating a counter (negative) card plate."""
    payload = {
        'lines': ['⠁', '⠃', '⠉', '⠙'],  # Braille characters A, B, C, D
        'plate_type': 'negative',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {
            'card_width': 85.0,
            'card_height': 55.0,
            'card_thickness': 2.0,
            'dot_height': 0.5,
            'dot_base_diameter': 1.5,
            'recess_shape': 1,  # bowl/spherical cap
        },
    }

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    # Check response
    assert response.status_code == 200, f'Expected 200, got {response.status_code}: {response.data}'
    assert len(response.data) > 0, 'STL data is empty'

    # Verify STL is loadable and has valid geometry
    mesh = trimesh.load(io.BytesIO(response.data), file_type='stl')
    assert mesh is not None, 'Failed to load STL mesh'
    assert len(mesh.faces) > 0, 'Mesh has no faces'


def test_generate_cylinder_positive(client):
    """Test generating a positive cylinder with braille text."""
    payload = {
        'lines': ['⠁⠃⠉', '⠙⠑⠋', '⠛⠓⠊', '⠚⠅⠇'],
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'dot_height': 0.5, 'dot_base_diameter': 1.5},
        'cylinder_params': {'diameter': 60.0, 'wall_thickness': 2.0, 'seam_offset_degrees': 0.0},
    }

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    # Check response
    assert response.status_code == 200, f'Expected 200, got {response.status_code}: {response.data}'
    assert len(response.data) > 0, 'STL data is empty'

    # Verify STL is loadable and has valid geometry
    mesh = trimesh.load(io.BytesIO(response.data), file_type='stl')
    assert mesh is not None, 'Failed to load STL mesh'
    assert len(mesh.faces) > 0, 'Mesh has no faces'


def test_generate_cylinder_counter(client):
    """Test generating a counter (negative) cylinder plate."""
    payload = {
        'lines': ['⠁⠃⠉', '⠙⠑⠋', '⠛⠓⠊', '⠚⠅⠇'],
        'plate_type': 'negative',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {
            'dot_height': 0.5,
            'dot_base_diameter': 1.5,
            'recess_shape': 1,  # bowl/spherical cap
        },
        'cylinder_params': {'diameter': 60.0, 'wall_thickness': 2.0, 'seam_offset_degrees': 0.0},
    }

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    # Check response
    assert response.status_code == 200, f'Expected 200, got {response.status_code}: {response.data}'
    assert len(response.data) > 0, 'STL data is empty'

    # Verify STL is loadable and has valid geometry
    mesh = trimesh.load(io.BytesIO(response.data), file_type='stl')
    assert mesh is not None, 'Failed to load STL mesh'
    assert len(mesh.faces) > 0, 'Mesh has no faces'


def test_generate_counter_plate_endpoint(client):
    """Test the dedicated counter plate generation endpoint."""
    payload = {
        'settings': {
            'card_width': 85.0,
            'card_height': 55.0,
            'card_thickness': 2.0,
            'dot_height': 0.5,
            'dot_base_diameter': 1.5,
            'recess_shape': 1,
        }
    }

    response = client.post('/generate_counter_plate_stl', json=payload, headers={'Content-Type': 'application/json'})

    # Check response
    assert response.status_code == 200, f'Expected 200, got {response.status_code}: {response.data}'
    assert len(response.data) > 0, 'STL data is empty'

    # Verify STL is loadable and has valid geometry
    mesh = trimesh.load(io.BytesIO(response.data), file_type='stl')
    assert mesh is not None, 'Failed to load STL mesh'
    assert len(mesh.faces) > 0, 'Mesh has no faces'


def test_validation_empty_input(client):
    """Test that empty input for positive plates returns 400."""
    payload = {'lines': ['', '', '', ''], 'plate_type': 'positive', 'shape_type': 'card', 'grade': 'g1', 'settings': {}}

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_validation_invalid_shape_type(client):
    """Test that invalid shape_type returns 400."""
    payload = {'lines': ['⠁'], 'plate_type': 'positive', 'shape_type': 'invalid', 'grade': 'g1', 'settings': {}}

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
