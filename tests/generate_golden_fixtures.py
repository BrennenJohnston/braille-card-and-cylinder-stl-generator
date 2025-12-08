"""
Generate golden STL fixtures for regression testing.

This script creates small reference STL files for each geometry type.
Run this script manually when you need to update the golden fixtures.
"""

import io
import json
import sys
from pathlib import Path

import trimesh

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import backend  # noqa: E402


def save_fixture_with_metadata(stl_bytes, fixture_name, description, request_payload):
    """Save STL fixture and its metadata."""
    fixtures_dir = Path(__file__).parent / 'fixtures'
    fixtures_dir.mkdir(exist_ok=True)

    # Save STL file
    stl_path = fixtures_dir / f'{fixture_name}.stl'
    stl_path.write_bytes(stl_bytes)

    # Load mesh to extract metadata
    mesh = trimesh.load(io.BytesIO(stl_bytes), file_type='stl', force='mesh')

    # Calculate bounds
    bbox_min = mesh.vertices.min(axis=0).tolist() if len(mesh.vertices) > 0 else [0, 0, 0]
    bbox_max = mesh.vertices.max(axis=0).tolist() if len(mesh.vertices) > 0 else [0, 0, 0]

    # Save metadata
    metadata = {
        'description': description,
        'fixture_name': fixture_name,
        'request_payload': request_payload,
        'expected_properties': {
            'face_count': len(mesh.faces),
            'vertex_count': len(mesh.vertices),
            'is_watertight': bool(mesh.is_watertight),
            'bbox_min': bbox_min,
            'bbox_max': bbox_max,
            'volume': float(mesh.volume) if mesh.is_watertight else None,
            'surface_area': float(mesh.area),
        },
    }

    metadata_path = fixtures_dir / f'{fixture_name}.json'
    metadata_path.write_text(json.dumps(metadata, indent=2))

    print(f'✓ Generated {fixture_name}:')
    print(f'  - Faces: {len(mesh.faces)}')
    print(f'  - Vertices: {len(mesh.vertices)}')
    print(f'  - Watertight: {mesh.is_watertight}')
    print(f'  - Bounds: {mesh.bounds}')
    print()


def generate_fixtures():
    """Generate all golden fixtures."""
    print('Generating golden fixtures...\n')

    backend.limiter.enabled = False
    client = backend.app.test_client()

    # 1. Card positive (small, 2 characters)
    payload_card_positive = {
        'lines': ['⠁⠃', '', '', ''],  # Just AB
        'plate_type': 'positive',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {
            'card_width': 60.0,
            'card_height': 40.0,
            'card_thickness': 2.0,
            'dot_height': 0.5,
            'dot_base_diameter': 1.5,
        },
    }
    response = client.post(
        '/generate_braille_stl', json=payload_card_positive, headers={'Content-Type': 'application/json'}
    )
    if response.status_code == 200 and len(response.data) > 0:
        save_fixture_with_metadata(
            response.data, 'card_positive_small', 'Small card with 2 braille characters (AB)', payload_card_positive
        )
    else:
        print(f'✗ Failed to generate card_positive_small: {response.status_code}')
        print(f'  Response: {response.data[:200] if response.data else "empty"}')

    # 2. Card counter (small, same size)
    payload_card_counter = {
        'lines': ['⠁⠃', '', '', ''],
        'plate_type': 'negative',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {
            'card_width': 60.0,
            'card_height': 40.0,
            'card_thickness': 2.0,
            'dot_height': 0.5,
            'dot_base_diameter': 1.5,
            'recess_shape': 1,
        },
    }
    response = client.post(
        '/generate_braille_stl', json=payload_card_counter, headers={'Content-Type': 'application/json'}
    )
    if response.status_code == 200 and len(response.data) > 0:
        save_fixture_with_metadata(
            response.data, 'card_counter_small', 'Small counter plate with bowl recesses', payload_card_counter
        )
    else:
        print(f'✗ Failed to generate card_counter_small: {response.status_code}')
        print(f'  Response: {response.data[:200] if response.data else "empty"}')

    # 3. Cylinder positive (small, 3 characters)
    payload_cylinder_positive = {
        'lines': ['⠁⠃⠉', '', '', ''],  # Just ABC
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'dot_height': 0.5, 'dot_base_diameter': 1.5},
        'cylinder_params': {'diameter': 40.0, 'wall_thickness': 2.0, 'seam_offset_degrees': 0.0},
    }
    response = client.post(
        '/generate_braille_stl', json=payload_cylinder_positive, headers={'Content-Type': 'application/json'}
    )
    save_fixture_with_metadata(
        response.data,
        'cylinder_positive_small',
        'Small cylinder with 3 braille characters (ABC)',
        payload_cylinder_positive,
    )

    # 4. Cylinder counter (small, same size)
    payload_cylinder_counter = {
        'lines': ['⠁⠃⠉', '', '', ''],
        'plate_type': 'negative',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'dot_height': 0.5, 'dot_base_diameter': 1.5, 'recess_shape': 1},
        'cylinder_params': {'diameter': 40.0, 'wall_thickness': 2.0, 'seam_offset_degrees': 0.0},
    }
    response = client.post(
        '/generate_braille_stl', json=payload_cylinder_counter, headers={'Content-Type': 'application/json'}
    )
    save_fixture_with_metadata(
        response.data, 'cylinder_counter_small', 'Small cylinder counter with bowl recesses', payload_cylinder_counter
    )

    print('✓ All golden fixtures generated successfully!')


if __name__ == '__main__':
    generate_fixtures()
