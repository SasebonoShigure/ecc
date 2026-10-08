"""Reusable geometry workspace; only the pending buffers are movable."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import SimpleNamespace


class NoLegalBufferLocation(RuntimeError):
    pass


@dataclass(frozen=True)
class BufferLocation:
    x_dbu: int
    y_dbu: int
    orientation: str


def _integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("physical geometry must use integer DBU")
    return value


def _sequence(value: object) -> Sequence[object]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("physical geometry must use lists/tuples")
    return value


class PhysicalBufferLegalizer:
    def __init__(
        self, geometry: Mapping[str, object], *, batch_capacity: int, total_capacity: int,
    ):
        import torch

        if not 0 < batch_capacity <= total_capacity:
            raise ValueError("buffer capacities must be positive and ordered")
        self.generation = _integer(geometry["generation"])
        self.dbu_per_um = _integer(geometry["dbu_per_um"])
        bounds = tuple(_integer(x) for x in _sequence(geometry["bounds"]))
        if len(bounds) != 4 or self.dbu_per_um <= 0:
            raise ValueError("physical geometry bounds or DBU are invalid")
        self.floorplan = SimpleNamespace(
            xl=bounds[0], yl=bounds[1], xh=bounds[2], yh=bounds[3],
            site_width=_integer(geometry["site_width"]),
            row_height=_integer(geometry["row_height"]), scale_factor=1.0,
        )
        f = self.floorplan
        if f.site_width <= 0 or f.row_height <= 0 or f.xl >= f.xh or f.yl >= f.yh:
            raise ValueError("physical row grid is invalid")
        self.rows: dict[int, str] = {}
        for entry in _sequence(geometry["rows"]):
            y, orientation = _sequence(entry)
            if not isinstance(orientation, str) or orientation not in ("N", "FS", "FN", "S"):
                raise ValueError("invalid physical row orientation")
            self.rows[_integer(y)] = orientation
        cells = geometry["cells"]
        if not isinstance(cells, Mapping):
            raise ValueError("physical master sizes must be a mapping")
        self.cells: dict[str, tuple[int, int]] = {}
        for name, size in cells.items():
            if not isinstance(name, str):
                raise ValueError("physical master name must be a string")
            width, height = (_integer(x) for x in _sequence(size))
            self.cells[name] = (width, height)
        obstacles = [
            tuple(_integer(x) for x in _sequence(box))
            for box in _sequence(geometry["obstacles"])
        ]
        if any(len(box) != 4 or not (
            f.xl <= box[0] < box[2] <= f.xh and f.yl <= box[1] < box[3] <= f.yh
        ) for box in obstacles):
            raise ValueError("physical obstacle must be a rectangle")
        self.batch_capacity = batch_capacity
        self.total_capacity = total_capacity
        self._used = 0
        self._fixed_count = len(obstacles)
        self._pending = 0
        # Fixed geometry and active input arrays retain capacity across batches.
        self._fixed = torch.empty((len(obstacles) + total_capacity, 4), dtype=torch.float64)
        if obstacles:
            self._fixed[:len(obstacles)] = torch.tensor(obstacles, dtype=torch.float64)
        capacity = self._fixed.shape[0] + batch_capacity
        self._position = torch.empty(2 * capacity, dtype=torch.float64)
        self._width = torch.empty(capacity, dtype=torch.float64)
        self._height = torch.empty(capacity, dtype=torch.float64)
        self._weights = torch.ones(capacity, dtype=torch.float64)
        self._regions = torch.empty(0, dtype=torch.float64)
        self._region_start = torch.zeros(1, dtype=torch.int32)
        self._region_map = torch.full((capacity,), torch.iinfo(torch.int32).max, dtype=torch.int32)

    def prepare(
        self, cell_names: Sequence[str], targets_dbu: Sequence[tuple[int, int]],
    ) -> list[BufferLocation]:
        import torch
        from dreamplace.ops.greedy_legalize.greedy_legalize import GreedyLegalize
        from dreamplace.ops.legality_check.legality_check import LegalityCheck

        count = len(cell_names)
        if self._pending:
            raise RuntimeError("finish or abandon the pending placement first")
        if (not 0 < count <= self.batch_capacity or count != len(targets_dbu)
                or self._used + count > self.total_capacity):
            raise ValueError("physical batch exceeds its remaining buffer budget")
        sizes = [self.cells[name] for name in cell_names]
        f = self.floorplan
        if any(w <= 0 or w > f.xh - f.xl or w % f.site_width or h != f.row_height
               for w, h in sizes):
            raise ValueError("buffer does not fit a single standard-cell row")
        total = count + self._fixed_count
        pos = self._position[:2 * total]
        x, y = pos[:total], pos[total:]
        # The native operator requires a contiguous x/y layout with movable cells
        # first. Copying its fixed geometry is explicit O(fixed obstacles) work.
        clipped = []
        for target, (w, h) in zip(targets_dbu, sizes, strict=True):
            tx, ty = (_integer(value) for value in target)
            if not all(-(2**31) <= value < 2**31 for value in (tx, ty)):
                raise ValueError("buffer target exceeds int32 DBU")
            # DREAMPlace casts to integer bins before its own clamp. Bound the
            # rough target here, before entering that native conversion.
            clipped.append((min(max(tx, f.xl), f.xh - w), min(max(ty, f.yl), f.yh - h)))
        targets = torch.tensor(clipped, dtype=torch.float64)
        x[:count], y[:count] = targets[:, 0], targets[:, 1]
        fixed = self._fixed[:self._fixed_count]
        x[count:], y[count:] = fixed[:, 0], fixed[:, 1]
        self._width[:count] = torch.tensor([w for w, _ in sizes], dtype=torch.float64)
        self._height[:count] = torch.tensor([h for _, h in sizes], dtype=torch.float64)
        self._width[count:total] = fixed[:, 2] - fixed[:, 0]
        self._height[count:total] = fixed[:, 3] - fixed[:, 1]
        width, height = self._width[:total], self._height[:total]
        regions = self._region_map[:total]
        legalize = GreedyLegalize(
            width, height, self._weights[:total], self._regions, self._region_start,
            regions, f.xl, f.yl, f.xh, f.yh, f.site_width, f.row_height,
            1, min(64, max(1, len(self.rows))), count, 0, 0,
        )
        output = legalize(pos, pos)
        check = LegalityCheck(
            width, height, self._regions, self._region_start, regions, f,
            self._fixed_count, count,
        )
        if not check(output):
            raise NoLegalBufferLocation("no legal location for this buffer batch")
        if not (torch.equal(output[count:total], x[count:])
                and torch.equal(output[total + count:], y[count:])):
            raise RuntimeError("buffer legalization moved a fixed obstacle")
        locations = []
        for i in range(count):
            px, py = float(output[i]), float(output[total + i])
            ix, iy = round(px), round(py)
            if abs(px - ix) > 1e-6 or abs(py - iy) > 1e-6 or iy not in self.rows:
                raise NoLegalBufferLocation("legalizer returned an invalid DBU row")
            locations.append(BufferLocation(ix, iy, self.rows[iy]))
        # Populate inactive reserved slots before native apply; accepting a
        # successful generation later changes only scalar counters.
        for i, (location, (w, h)) in enumerate(zip(locations, sizes, strict=True)):
            self._fixed[self._fixed_count + i] = torch.tensor(
                [location.x_dbu, location.y_dbu, location.x_dbu + w, location.y_dbu + h],
                dtype=torch.float64,
            )
        self._pending = count
        return locations

    def committed(self, generation: int) -> None:
        if not self._pending or generation != self.generation + 1:
            raise RuntimeError("placement commit does not match the pending generation")
        self._fixed_count += self._pending
        self._used += self._pending
        self.generation = generation
        self._pending = 0

    def abandon(self) -> None:
        self._pending = 0
