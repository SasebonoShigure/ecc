"""Runs the real DREAMPlace CPU operators; no placement-engine reconstruction."""

import pytest

from chipcompiler.tools.ecc.physical_placement import (
    NoLegalBufferLocation,
    PhysicalBufferLegalizer,
)

pytest.importorskip("torch", exc_type=ImportError)
pytest.importorskip("dreamplace.ops.greedy_legalize.greedy_legalize_cpp", exc_type=ImportError)
pytest.importorskip("dreamplace.ops.legality_check.legality_check_cpp", exc_type=ImportError)


def test_batch_legalization_respects_fixed_cells_and_committed_generations():
    geometry = {
        "generation": 0, "dbu_per_um": 1000, "bounds": (0, 0, 8, 4),
        "site_width": 1, "row_height": 2, "rows": [(0, "N"), (2, "FS")],
        "obstacles": [(0, 0, 2, 2)], "cells": {"BUF": (2, 2)},
    }
    workspace = PhysicalBufferLegalizer(geometry, batch_capacity=2, total_capacity=4)
    for target in [(10**100, 0), (1.5, 0), (float("inf"), 0), (True, 0)]:
        with pytest.raises(ValueError, match="DBU"):
            workspace.prepare(["BUF"], [target])
    # Rough targets outside the chip are safely clamped before integer binning.
    outside = workspace.prepare(["BUF"], [(-(2**31), 2**31 - 1)])
    assert 0 <= outside[0].x_dbu <= 6 and outside[0].y_dbu in (0, 2)
    workspace.abandon()
    first = workspace.prepare(["BUF", "BUF"], [(0, 0), (0, 0)])
    workspace.abandon()
    assert workspace.prepare(["BUF", "BUF"], [(0, 0), (0, 0)]) == first
    workspace.committed(1)
    second = workspace.prepare(["BUF", "BUF"], [(0, 0), (0, 0)])
    boxes = [(0, 0, 2, 2)] + [
        (p.x_dbu, p.y_dbu, p.x_dbu + 2, p.y_dbu + 2) for p in first + second
    ]
    for i, (xl, yl, xh, yh) in enumerate(boxes):
        assert 0 <= xl < xh <= 8 and 0 <= yl < yh <= 4
        for ax, ay, bx, by in boxes[:i]:
            assert xh <= ax or xl >= bx or yh <= ay or yl >= by
    for location in first + second:
        assert location.orientation == ("N" if location.y_dbu == 0 else "FS")
    workspace.committed(2)
    assert workspace.generation == 2
    with pytest.raises(ValueError, match="budget"):
        workspace.prepare(["BUF"], [(0, 0)])


def test_no_legal_location_does_not_reserve_or_advance_geometry():
    workspace = PhysicalBufferLegalizer({
        "generation": 7, "dbu_per_um": 1000, "bounds": (0, 0, 2, 2),
        "site_width": 1, "row_height": 2, "rows": [(0, "N")],
        "obstacles": [(0, 0, 2, 2)], "cells": {"BUF": (2, 2)},
    }, batch_capacity=1, total_capacity=1)
    for _ in range(2):
        with pytest.raises(NoLegalBufferLocation):
            workspace.prepare(["BUF"], [(0, 0)])
    assert workspace.generation == 7
