import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except Exception:
    print('requests is required: pip install requests')
    raise


def target_base_url() -> str:
    base = os.environ.get('TARGET_BASE_URL')
    if not base and len(sys.argv) > 1:
        base = sys.argv[1]
    if not base:
        print('Usage: python scripts/pregenerate.py https://your-app.vercel.app')
        sys.exit(1)
    return base.rstrip('/')


def post_json(url: str, payload: dict) -> dict:
    start = time.time()
    try:
        r = requests.post(url, json=payload, timeout=60)
        latency = time.time() - start
        # Follow redirects disabled by default; capture Location
        location = r.headers.get('Location')
        return {
            'status': r.status_code,
            'latency_s': round(latency, 3),
            'location': location,
            'error': None if r.ok or r.status_code in (302, 304) else r.text[:300],
        }
    except Exception as e:
        latency = time.time() - start
        return {'status': 0, 'latency_s': round(latency, 3), 'location': None, 'error': str(e)}


def build_payload_positive(lines, grade='g2', shape_type='card'):
    return {
        'lines': lines,
        'original_lines': None,
        'placement_mode': 'manual',
        'plate_type': 'positive',
        'grade': grade,
        'shape_type': shape_type,
        'settings': {
            'card_width': 100.0,
            'card_height': 60.0,
            'card_thickness': 2.0,
            'grid_columns': 18,
            'grid_rows': 6,
            'cell_spacing': 6.0,
            'line_spacing': 10.0,
            'dot_spacing': 2.5,
            'emboss_dot_base_diameter': 1.4,
            'emboss_dot_height': 0.6,
            'emboss_dot_flat_hat': 0.2,
            'braille_x_adjust': 0.0,
            'braille_y_adjust': 0.0,
        },
        'cylinder_params': {'radius_mm': 30.0, 'height_mm': 60.0} if shape_type == 'cylinder' else {},
    }


def build_payload_counter(shape_type='card'):
    return {
        'plate_type': 'negative',
        'settings': {
            'card_width': 100.0,
            'card_height': 60.0,
            'card_thickness': 2.0,
            'grid_columns': 18,
            'grid_rows': 6,
            'cell_spacing': 6.0,
            'line_spacing': 10.0,
            'dot_spacing': 2.5,
            'emboss_dot_base_diameter': 1.4,
            'counter_plate_dot_size_offset': 0.2,
            'hemi_counter_dot_base_diameter': 1.6,
            'bowl_counter_dot_base_diameter': 1.6,
            'hemisphere_subdivisions': 2,
            'cone_segments': 16,
            'recess_shape': 1,
            'counter_dot_depth': 0.6,
        },
        'shape_type': shape_type,
    }


def main():
    base = target_base_url()
    endpoints = []

    # Positive card (g1/g2)
    endpoints.append(
        (f'{base}/generate_braille_stl', build_payload_positive(['⠠⠃⠗⠁⠊⠇⠇⠑', '⠉⠁⠗⠙'], grade='g1', shape_type='card'))
    )
    endpoints.append(
        (
            f'{base}/generate_braille_stl',
            build_payload_positive(['⠠⠃⠗⠁⠊⠇⠇⠑', '⠉⠽⠇⠊⠝⠙⠑⠗'], grade='g2', shape_type='card'),
        )
    )

    # Positive cylinder (g2)
    endpoints.append(
        (f'{base}/generate_braille_stl', build_payload_positive(['⠉⠽⠇⠊⠝⠙⠑⠗'], grade='g2', shape_type='cylinder'))
    )

    # Counter plates (card)
    endpoints.append((f'{base}/generate_counter_plate_stl', build_payload_counter('card')))

    # Fan out with modest concurrency
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(post_json, url, payload) for url, payload in endpoints]
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            print(json.dumps({'task': i, **res}, ensure_ascii=False))

    print('Done. If Blob is configured, repeated requests should redirect (302) quickly.')


if __name__ == '__main__':
    main()
