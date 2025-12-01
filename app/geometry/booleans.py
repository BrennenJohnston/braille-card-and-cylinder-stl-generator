"""
Boolean operations and mesh operations.

Unified API for robust 3D boolean operations with automatic batching and
engine fallback. Prefer the builtin trimesh engine, then fall back to
`manifold` when available. Includes helpers for watertight healing.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable

import trimesh

from app.utils import get_logger

logger = get_logger(__name__)


def _candidate_engines(preferred: str | None = None) -> list[str | None]:
    """
    Return a list of candidate engines to try for boolean ops.

    Order of preference:
    - preferred (if provided)
    - 'manifold' (if manifold3d is installed) - preferred for reliability
    - trimesh default (None)
    """
    engines: list[str | None] = []
    if preferred not in (None, ''):
        engines.append(preferred)

    # Try manifold first - it's most reliable when available
    try:
        import manifold3d  # noqa: F401

        if 'manifold' not in engines:
            engines.append('manifold')
            logger.debug('manifold3d available - added to boolean engines')
    except ImportError as e:
        logger.warning(f'manifold3d not available (ImportError): {e}')
    except Exception as e:
        logger.warning(f'manifold3d not available ({type(e).__name__}): {e}')

    # Trimesh default auto-selects an available backend as fallback
    if None not in engines:
        engines.append(None)

    # De-duplicate while preserving order
    deduped: list[str | None] = []
    for e in engines:
        if e not in deduped:
            deduped.append(e)

    logger.debug(f'Boolean engine candidates: {[e or "trimesh-default" for e in deduped]}')
    return deduped


def _heal_watertight(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Attempt simple healing to improve watertightness."""
    try:
        if not mesh.is_watertight:
            mesh.fill_holes()
        if not mesh.is_winding_consistent:
            try:
                mesh.fix_normals()
            except Exception:
                mesh.unify_normals()
    except Exception:
        # Healing is best-effort; ignore errors
        pass
    return mesh


def mesh_union(meshes: Iterable[trimesh.Trimesh], engine_preference: str | None = None) -> trimesh.Trimesh:
    """Robust union with fallback engines and pairwise batching."""
    mesh_list = [m for m in meshes if m is not None]
    if not mesh_list:
        raise ValueError('mesh_union() requires at least one mesh')
    if len(mesh_list) == 1:
        return mesh_list[0]

    for engine in _candidate_engines(engine_preference):
        try:
            logger.debug(f'mesh_union trying engine={engine or "trimesh-default"} for {len(mesh_list)} meshes')
            return trimesh.boolean.union(mesh_list, engine=engine)
        except Exception as e:
            logger.warning(f'mesh_union engine {engine or "trimesh-default"} failed: {e}')

    # Pairwise union fallback (binary tree) using trimesh default
    try:
        work: list[trimesh.Trimesh] = mesh_list[:]
        while len(work) > 1:
            next_level: list[trimesh.Trimesh] = []
            it = iter(work)
            for a, b in itertools.zip_longest(it, it):
                if b is None:
                    next_level.append(a)
                else:
                    try:
                        next_level.append(trimesh.boolean.union([a, b]))
                    except Exception as e_pair:
                        logger.error(f'pairwise union failed: {e_pair}')
                        # Best-effort: concatenate as non-boolean fallback
                        next_level.append(trimesh.util.concatenate([a, b]))
            work = next_level
        return work[0]
    except Exception as e:
        logger.error(f'mesh_union pairwise fallback failed: {e}')
        # Last resort: concatenate (non-boolean)
        return trimesh.util.concatenate(mesh_list)


def mesh_difference(meshes: Iterable[trimesh.Trimesh], engine_preference: str | None = None) -> trimesh.Trimesh:
    """Robust difference [base, tool] or [base, union(tool...)] with fallbacks."""
    mesh_list = [m for m in meshes if m is not None]
    if len(mesh_list) < 2:
        raise ValueError('mesh_difference() requires at least two meshes: base and at least one cutter')
    base = mesh_list[0]
    cutters = mesh_list[1:]

    # Try engines in order
    for engine in _candidate_engines(engine_preference):
        try:
            logger.debug(f'mesh_difference trying engine={engine or "trimesh-default"} with {1 + len(cutters)} meshes')
            result = trimesh.boolean.difference([base] + cutters, engine=engine)
            return _heal_watertight(result)
        except Exception as e:
            logger.warning(f'mesh_difference engine {engine or "trimesh-default"} failed: {e}')

    # Fallback: subtract individually using trimesh default, best-effort
    try:
        result = base.copy()
        for i, cutter in enumerate(cutters):
            try:
                result = trimesh.boolean.difference([result, cutter])
            except Exception as e_single:
                logger.warning(f'individual difference failed on cutter {i + 1}/{len(cutters)}: {e_single}')
                continue
        return _heal_watertight(result)
    except Exception as e:
        logger.error(f'mesh_difference fallback failed: {e}')
        # As a very last resort, return the base unmodified to avoid crashes
        return base


def batch_union(
    meshes: Iterable[trimesh.Trimesh],
    batch_size: int = 32,
    engine_preference: str | None = None,
) -> trimesh.Trimesh:
    """Union meshes in batches to reduce complexity and improve robustness."""
    mesh_list = [m for m in meshes if m is not None]
    if not mesh_list:
        raise ValueError('batch_union() requires at least one mesh')
    if len(mesh_list) == 1:
        return mesh_list[0]

    if batch_size <= 1:
        return mesh_union(mesh_list, engine_preference)

    buckets: list[trimesh.Trimesh] = []
    for i in range(0, len(mesh_list), batch_size):
        bucket = mesh_union(mesh_list[i : i + batch_size], engine_preference)
        buckets.append(bucket)
    return mesh_union(buckets, engine_preference)


def batch_subtract(
    base: trimesh.Trimesh,
    cutters: Iterable[trimesh.Trimesh],
    engine_preference: str | None = None,
    union_first: bool = True,
    union_batch_size: int = 64,
) -> trimesh.Trimesh:
    """Subtract many cutters from base with optional pre-union for robustness."""
    cutter_list = [c for c in cutters if c is not None]
    if not cutter_list:
        return base

    if union_first:
        try:
            union_cutters = batch_union(cutter_list, batch_size=union_batch_size, engine_preference=engine_preference)
            return mesh_difference([base, union_cutters], engine_preference)
        except Exception as e:
            logger.warning(f'batch_subtract union-first path failed: {e}')

    # Fallback: subtract individually
    try:
        result = base.copy()
        for i, cutter in enumerate(cutter_list):
            try:
                result = mesh_difference([result, cutter], engine_preference)
            except Exception as e_single:
                logger.warning(
                    f'batch_subtract individual difference failed on cutter {i + 1}/{len(cutter_list)}: {e_single}'
                )
                continue
        return result
    except Exception as e:
        logger.error(f'batch_subtract fallback failed: {e}')
        return base
