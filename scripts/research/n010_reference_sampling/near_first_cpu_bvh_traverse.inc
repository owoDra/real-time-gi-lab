    template <class Visit>
    void traverse(const Ray& ray, double tmin, Visit&& visit, double& tmax) const {
        if (nodes_.empty()) return;
        const WatertightRay wr(ray);
        const V3 inv{1.0 / ray.dir.x, 1.0 / ray.dir.y, 1.0 / ray.dir.z};
        std::uint32_t stack[128];
        double entries[128];
        int sp = 0;
        double root_entry{};
        if (!slab_entry(nodes_[0].box, ray.origin, inv, tmin, tmax, root_entry)) return;
        stack[sp] = 0; entries[sp++] = root_entry;
        while (sp > 0) {
            --sp;
            const auto ni = stack[sp];
            if (entries[sp] > tmax) continue;
            const Node& node = nodes_[ni];
            if (node.count > 0) {
                for (auto i = node.first; i < node.first + node.count; ++i) {
                    const auto id = order_[i];
                    const double t = wr.intersect(tris_[id]);
                    if (t < kInf && t <= tmax && visit(id, t)) return;
                }
            } else {
                const auto left = ni + 1, right = node.right;
                double left_entry{}, right_entry{};
                const bool has_left = slab_entry(nodes_[left].box, ray.origin, inv, tmin, tmax, left_entry);
                const bool has_right = slab_entry(nodes_[right].box, ray.origin, inv, tmin, tmax, right_entry);
                const auto push = [&](std::uint32_t id, double entry) {
                    if (sp == 128) throw std::runtime_error("BVH stack overflow");
                    stack[sp] = id; entries[sp++] = entry;
                };
                if (has_left && has_right) {
                    if (left_entry <= right_entry) {
                        push(right, right_entry); push(left, left_entry);
                    } else {
                        push(left, left_entry); push(right, right_entry);
                    }
                } else if (has_left) push(left, left_entry);
                else if (has_right) push(right, right_entry);
            }
        }
    }
