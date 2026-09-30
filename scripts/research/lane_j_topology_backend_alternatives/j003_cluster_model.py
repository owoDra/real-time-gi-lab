from __future__ import annotations

from dataclasses import dataclass
import math

from j002_geometry import centroid


@dataclass
class Cluster:
    cluster_id: int
    primitive_ids: list[int]


@dataclass
class UpdateStats:
    dirty_cluster_count: int = 0
    rebuilt_triangle_count: int = 0
    unaffected_cluster_rebuild_count: int = 0
    split_count: int = 0
    merge_count: int = 0
    retired_empty_cluster_count: int = 0
    cluster_set_changed: bool = False


class ClusterModel:
    def __init__(self, triangles, target=48, maximum=64, merge_below=24):
        if not (0 < merge_below < target <= maximum):
            raise ValueError("invalid thresholds")
        self.target = target
        self.maximum = maximum
        self.merge_below = merge_below
        self.triangles = {t.primitive_id: t for t in triangles}
        self.next_cluster_id = 0
        ordered = self._morton_order(list(self.triangles))
        self.clusters = [
            Cluster(self._new_id(), ordered[i : i + target])
            for i in range(0, len(ordered), target)
        ]
        self._validate()

    def _new_id(self):
        value = self.next_cluster_id
        self.next_cluster_id += 1
        return value

    def _bounds(self, ids):
        if not ids:
            raise ValueError("cluster bounds require at least one primitive")
        points = [
            point
            for primitive_id in ids
            for point in (
                self.triangles[primitive_id].v0,
                self.triangles[primitive_id].v1,
                self.triangles[primitive_id].v2,
            )
        ]
        return (
            tuple(min(point[axis] for point in points) for axis in range(3)),
            tuple(max(point[axis] for point in points) for axis in range(3)),
        )

    def _center(self, ids):
        bounds_min, bounds_max = self._bounds(ids)
        return tuple(
            (bounds_min[axis] + bounds_max[axis]) * 0.5
            for axis in range(3)
        )

    def _area(self, ids):
        if not ids:
            return 0.0
        bounds_min, bounds_max = self._bounds(ids)
        extent = [
            max(0.0, bounds_max[axis] - bounds_min[axis])
            for axis in range(3)
        ]
        return 2 * (
            extent[0] * extent[1]
            + extent[1] * extent[2]
            + extent[2] * extent[0]
        )

    def _morton_order(self, ids):
        if not ids:
            return []
        centroids = {
            primitive_id: centroid(self.triangles[primitive_id])
            for primitive_id in ids
        }
        bounds_min = tuple(
            min(point[axis] for point in centroids.values())
            for axis in range(3)
        )
        bounds_max = tuple(
            max(point[axis] for point in centroids.values())
            for axis in range(3)
        )

        def code(primitive_id):
            point = centroids[primitive_id]
            quantized = []
            for axis in range(3):
                quantized.append(
                    max(
                        0,
                        min(
                            1023,
                            int(
                                (point[axis] - bounds_min[axis])
                                / max(
                                    bounds_max[axis] - bounds_min[axis],
                                    1e-9,
                                )
                                * 1023
                                + 0.5
                            ),
                        ),
                    )
                )

            def spread(value):
                result = 0
                for bit in range(10):
                    result |= ((value >> bit) & 1) << (3 * bit)
                return result

            return (
                spread(quantized[0])
                | (spread(quantized[1]) << 1)
                | (spread(quantized[2]) << 2)
            )

        return sorted(ids, key=lambda primitive_id: (code(primitive_id), primitive_id))

    def _nearest(self, triangle):
        best = None
        for cluster in self.clusters:
            if not cluster.primitive_ids:
                raise AssertionError("empty cluster reached assignment")
            key = (
                self._area(cluster.primitive_ids + [triangle.primitive_id])
                - self._area(cluster.primitive_ids),
                cluster.cluster_id,
            )
            if best is None or key < best[0]:
                best = (key, cluster)
        return best[1] if best else None

    def _split(self, cluster):
        queue = [self._morton_order(cluster.primitive_ids)]
        pieces = []
        while queue:
            primitive_ids = queue.pop(0)
            if len(primitive_ids) <= self.maximum:
                pieces.append(primitive_ids)
                continue
            cut = len(primitive_ids) // 2
            queue.extend([primitive_ids[:cut], primitive_ids[cut:]])

        result = [Cluster(cluster.cluster_id, pieces[0])]
        result.extend(
            Cluster(self._new_id(), primitive_ids)
            for primitive_ids in pieces[1:]
        )
        return result

    def update(self, triangles):
        new_triangles = {t.primitive_id: t for t in triangles}
        old_ids = set(self.triangles)
        new_ids = set(new_triangles)
        deleted = old_ids - new_ids
        inserted = new_ids - old_ids
        changed = {
            primitive_id
            for primitive_id in old_ids & new_ids
            if self.triangles[primitive_id] != new_triangles[primitive_id]
        }

        original = {
            cluster.cluster_id: tuple(cluster.primitive_ids)
            for cluster in self.clusters
        }
        dirty = set()

        for cluster in self.clusters:
            before = list(cluster.primitive_ids)
            cluster.primitive_ids = [
                primitive_id
                for primitive_id in cluster.primitive_ids
                if primitive_id not in deleted and primitive_id not in changed
            ]
            if cluster.primitive_ids != before:
                dirty.add(cluster.cluster_id)

        # v1.2: retire empty clusters before reassignment. This prevents undefined
        # AABBs and forbids implicit reuse of an emptied cluster's payload identity.
        retired_empty_ids = {
            cluster.cluster_id
            for cluster in self.clusters
            if not cluster.primitive_ids
        }
        if retired_empty_ids:
            self.clusters = [
                cluster
                for cluster in self.clusters
                if cluster.cluster_id not in retired_empty_ids
            ]
            dirty.difference_update(retired_empty_ids)

        self.triangles = new_triangles

        for primitive_id in sorted(inserted | changed):
            cluster = self._nearest(new_triangles[primitive_id])
            if cluster is None:
                cluster = Cluster(self._new_id(), [])
                self.clusters.append(cluster)
            cluster.primitive_ids.append(primitive_id)
            dirty.add(cluster.cluster_id)

        split_count = 0
        rebuilt = []
        for cluster in sorted(self.clusters, key=lambda item: item.cluster_id):
            if (
                cluster.cluster_id in dirty
                and len(cluster.primitive_ids) > self.maximum
            ):
                parts = self._split(cluster)
                rebuilt.extend(parts)
                split_count += len(parts) - 1
            else:
                rebuilt.append(cluster)
        self.clusters = rebuilt

        if split_count:
            dirty.update(
                cluster.cluster_id
                for cluster in self.clusters
                if cluster.cluster_id not in original
            )

        merge_count = 0
        changed_loop = True
        while changed_loop:
            changed_loop = False
            for cluster in sorted(
                self.clusters,
                key=lambda item: item.cluster_id,
            ):
                if (
                    cluster.cluster_id not in dirty
                    or len(cluster.primitive_ids) >= self.merge_below
                ):
                    continue

                candidates = [
                    candidate
                    for candidate in self.clusters
                    if candidate.cluster_id != cluster.cluster_id
                    and candidate.primitive_ids
                    and len(candidate.primitive_ids)
                    + len(cluster.primitive_ids)
                    <= self.target
                ]
                if not candidates:
                    continue

                cluster_center = self._center(cluster.primitive_ids)

                def distance(candidate):
                    return (
                        math.dist(
                            cluster_center,
                            self._center(candidate.primitive_ids),
                        ),
                        candidate.cluster_id,
                    )

                target = min(candidates, key=distance)
                target.primitive_ids = self._morton_order(
                    target.primitive_ids + cluster.primitive_ids
                )
                dirty.add(target.cluster_id)
                self.clusters = [
                    item
                    for item in self.clusters
                    if item.cluster_id != cluster.cluster_id
                ]
                merge_count += 1
                changed_loop = True
                break

        self._validate()

        final_dirty = {
            cluster.cluster_id
            for cluster in self.clusters
            if cluster.cluster_id in dirty
        }
        unaffected = sum(
            1
            for cluster in self.clusters
            if cluster.cluster_id not in dirty
            and original.get(cluster.cluster_id)
            != tuple(cluster.primitive_ids)
        )
        return UpdateStats(
            dirty_cluster_count=len(final_dirty),
            rebuilt_triangle_count=sum(
                len(cluster.primitive_ids)
                for cluster in self.clusters
                if cluster.cluster_id in final_dirty
            ),
            unaffected_cluster_rebuild_count=unaffected,
            split_count=split_count,
            merge_count=merge_count,
            retired_empty_cluster_count=len(retired_empty_ids),
            cluster_set_changed=(
                split_count > 0
                or merge_count > 0
                or bool(retired_empty_ids)
            ),
        )

    def _validate(self):
        if any(not cluster.primitive_ids for cluster in self.clusters):
            raise AssertionError("empty cluster persisted")
        primitive_ids = [
            primitive_id
            for cluster in self.clusters
            for primitive_id in cluster.primitive_ids
        ]
        if (
            len(primitive_ids) != len(set(primitive_ids))
            or set(primitive_ids) != set(self.triangles)
        ):
            raise AssertionError("cluster ownership invalid")
        if any(
            len(cluster.primitive_ids) > self.maximum
            for cluster in self.clusters
        ):
            raise AssertionError("cluster maximum exceeded")
