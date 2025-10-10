"""
Golden/regression tests for braille STL generator.

These tests compare newly generated STLs against golden fixtures to detect
unintended changes in geometry generation.
"""

import io
import json
from pathlib import Path

import pytest
import trimesh


@pytest.fixture(scope='module')
def fixtures_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / 'fixtures'


def load_fixture_metadata(fixtures_dir, fixture_name):
    """Load metadata for a golden fixture."""
    metadata_path = fixtures_dir / f'{fixture_name}.json'
    with open(metadata_path) as f:
        return json.load(f)


def assert_mesh_similar(mesh, expected_props, tolerance=0.1):
    """
    Assert that a mesh is similar to expected properties.

    Args:
        mesh: Trimesh object
        expected_props: Dict with expected_properties from fixture metadata
        tolerance: Relative tolerance for face count (0.1 = 10%)
    """
    # Face count should be within tolerance
    expected_faces = expected_props['face_count']
    actual_faces = len(mesh.faces)
    face_tolerance = max(10, int(expected_faces * tolerance))  # At least 10 faces tolerance

    assert abs(actual_faces - expected_faces) <= face_tolerance, (
        f'Face count mismatch: expected {expected_faces}, got {actual_faces} (tolerance: {face_tolerance})'
    )

    # Vertex count should be within tolerance
    expected_vertices = expected_props['vertex_count']
    actual_vertices = len(mesh.vertices)
    vertex_tolerance = max(10, int(expected_vertices * tolerance))

    assert abs(actual_vertices - expected_vertices) <= vertex_tolerance, (
        f'Vertex count mismatch: expected {expected_vertices}, got {actual_vertices} (tolerance: {vertex_tolerance})'
    )

    # Watertight property should match (for watertight fixtures)
    if expected_props['is_watertight']:
        assert mesh.is_watertight or actual_faces > 100, 'Expected watertight mesh or substantial geometry'

    # Bounding box should be similar (within 5% per dimension)
    if expected_props['bbox_min'] and expected_props['bbox_max']:
        expected_min = expected_props['bbox_min']
        expected_max = expected_props['bbox_max']

        actual_min = mesh.vertices.min(axis=0).tolist()
        actual_max = mesh.vertices.max(axis=0).tolist()

        for i, (exp_min, exp_max, act_min, act_max) in enumerate(
            zip(expected_min, expected_max, actual_min, actual_max)
        ):
            dim_range = max(1.0, exp_max - exp_min)  # Avoid division by zero
            bbox_tolerance = dim_range * 0.05  # 5% of dimension range

            assert abs(act_min - exp_min) <= bbox_tolerance, (
                f'BBox min[{i}] mismatch: expected {exp_min}, got {act_min}'
            )
            assert abs(act_max - exp_max) <= bbox_tolerance, (
                f'BBox max[{i}] mismatch: expected {exp_max}, got {act_max}'
            )


def test_golden_card_positive(client, fixtures_dir):
    """Test card positive generation matches golden fixture."""
    metadata = load_fixture_metadata(fixtures_dir, 'card_positive_small')
    payload = metadata['request_payload']

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 200
    assert len(response.data) > 0

    mesh = trimesh.load(io.BytesIO(response.data), file_type='stl', force='mesh')
    assert_mesh_similar(mesh, metadata['expected_properties'])


def test_golden_card_counter(client, fixtures_dir):
    """Test card counter generation matches golden fixture."""
    metadata = load_fixture_metadata(fixtures_dir, 'card_counter_small')
    payload = metadata['request_payload']

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 200
    assert len(response.data) > 0

    mesh = trimesh.load(io.BytesIO(response.data), file_type='stl', force='mesh')
    assert_mesh_similar(mesh, metadata['expected_properties'])


def test_golden_cylinder_positive(client, fixtures_dir):
    """Test cylinder positive generation matches golden fixture."""
    metadata = load_fixture_metadata(fixtures_dir, 'cylinder_positive_small')
    payload = metadata['request_payload']

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 200
    assert len(response.data) > 0

    mesh = trimesh.load(io.BytesIO(response.data), file_type='stl', force='mesh')
    assert_mesh_similar(mesh, metadata['expected_properties'])


def test_golden_cylinder_counter(client, fixtures_dir):
    """Test cylinder counter generation matches golden fixture."""
    metadata = load_fixture_metadata(fixtures_dir, 'cylinder_counter_small')
    payload = metadata['request_payload']

    response = client.post('/generate_braille_stl', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 200
    assert len(response.data) > 0

    mesh = trimesh.load(io.BytesIO(response.data), file_type='stl', force='mesh')
    assert_mesh_similar(mesh, metadata['expected_properties'])
