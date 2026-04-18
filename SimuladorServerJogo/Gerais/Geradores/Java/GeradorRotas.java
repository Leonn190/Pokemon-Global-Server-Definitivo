import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.PriorityQueue;
import java.util.Set;

final class RouteRules {
    final int minCount;
    final int maxCount;
    final int minVillageLinks;
    final int maxVillageLinks;
    final int minDistance;
    final int maxDistance;
    final double shallowWaterPenalty;
    final double sameRegionBonus;
    final int routeBrushRadius;

    RouteRules(
        int minCount,
        int maxCount,
        int minVillageLinks,
        int maxVillageLinks,
        int minDistance,
        int maxDistance,
        double shallowWaterPenalty,
        double sameRegionBonus,
        int routeBrushRadius
    ) {
        this.minCount = minCount;
        this.maxCount = maxCount;
        this.minVillageLinks = minVillageLinks;
        this.maxVillageLinks = maxVillageLinks;
        this.minDistance = minDistance;
        this.maxDistance = maxDistance;
        this.shallowWaterPenalty = shallowWaterPenalty;
        this.sameRegionBonus = sameRegionBonus;
        this.routeBrushRadius = routeBrushRadius;
    }
}

final class RouteData {
    final int id;
    final String fromVillage;
    final String toVillage;
    final int fromX;
    final int fromY;
    final int toX;
    final int toY;
    final int fromRegionId;
    final int toRegionId;
    final List<int[]> points;

    RouteData(int id, Poi from, Poi to, List<int[]> points) {
        this.id = id;
        this.fromVillage = from.name == null ? "Vila " + id : from.name;
        this.toVillage = to.name == null ? "Vila " + (id + 1) : to.name;
        this.fromX = from.x;
        this.fromY = from.y;
        this.toX = to.x;
        this.toY = to.y;
        this.fromRegionId = from.regionId;
        this.toRegionId = to.regionId;
        this.points = points;
    }
}

final class GeradorRotas {
    private static final double INF = 1.0e18;

    private final GeneratorContext ctx;
    private final RouteRules rules;
    private final int step;
    private final int cellsX;
    private final int cellsY;
    private final double[] cellCost;

    GeradorRotas(GeneratorContext ctx) {
        this.ctx = ctx;
        this.rules = ctx.localityRules.routeConfig;
        this.step = Math.max(4, ctx.terrainRules.chunkSize);
        this.cellsX = Math.max(1, (int) Math.ceil(ctx.width / (double) step));
        this.cellsY = Math.max(1, (int) Math.ceil(ctx.height / (double) step));
        this.cellCost = new double[cellsX * cellsY];
    }

    void generate() {
        ctx.routes.clear();
        buildCellCostMap();
        List<Poi> villages = villages();
        if (villages.size() < 2) {
            System.out.println("  Rotas: 0 / 0 (vilas insuficientes)");
            return;
        }

        int target = rangedValue(rules.minCount, rules.maxCount, 340_001L);
        int maxPairs = (villages.size() * (villages.size() - 1)) / 2;
        int maxByDegree = (villages.size() * Math.max(0, rules.maxVillageLinks + 1)) / 2;
        target = Math.min(target, Math.min(maxPairs, maxByDegree));
        int[] degree = new int[villages.size()];
        Set<Long> attemptedPairs = new HashSet<>();
        int routeId = 0;
        int attempts = 0;

        Set<Integer> connected = new HashSet<>();
        connected.add(0);
        while (connected.size() < villages.size()) {
            RouteCandidate best = null;
            for (int from : connected) {
                for (int to = 0; to < villages.size(); to++) {
                    if (connected.contains(to) || from == to) {
                        continue;
                    }
                    RouteCandidate cand = buildCandidate(villages, from, to);
                    if (cand == null) {
                        continue;
                    }
                    if (best == null || cand.sortScore < best.sortScore) {
                        best = cand;
                    }
                }
            }
            if (best == null) {
                break;
            }
            attempts++;
            if (tryCreateRoute(best, villages, degree, attemptedPairs, routeId)) {
                routeId++;
                connected.add(best.a);
                connected.add(best.b);
            } else {
                connected.add(best.b);
            }
        }

        List<RouteCandidate> extras = new ArrayList<>();
        for (int a = 0; a < villages.size(); a++) {
            for (int b = a + 1; b < villages.size(); b++) {
                RouteCandidate cand = buildCandidate(villages, a, b);
                if (cand != null) {
                    extras.add(cand);
                }
            }
        }
        extras.sort((l, r) -> Double.compare(l.sortScore, r.sortScore));

        for (RouteCandidate cand : extras) {
            if (ctx.routes.size() >= target) {
                break;
            }
            if (degree[cand.a] >= rules.maxVillageLinks || degree[cand.b] >= rules.maxVillageLinks) {
                continue;
            }
            attempts++;
            if (tryCreateRoute(cand, villages, degree, attemptedPairs, routeId)) {
                routeId++;
            }
        }

        if (ctx.routes.size() < target) {
            for (RouteCandidate cand : extras) {
                if (ctx.routes.size() >= target) {
                    break;
                }
                if (degree[cand.a] >= rules.maxVillageLinks + 1 || degree[cand.b] >= rules.maxVillageLinks + 1) {
                    continue;
                }
                attempts++;
                if (tryCreateRoute(cand, villages, degree, attemptedPairs, routeId)) {
                    routeId++;
                }
            }
        }

        for (RouteData route : ctx.routes) {
            carveRoute(route);
        }

        int minDegree = Integer.MAX_VALUE;
        int maxDegree = 0;
        int sumDegree = 0;
        for (int value : degree) {
            minDegree = Math.min(minDegree, value);
            maxDegree = Math.max(maxDegree, value);
            sumDegree += value;
        }
        double avgDegree = villages.isEmpty() ? 0.0 : (sumDegree / (double) villages.size());
        System.out.println("  Rotas: " + ctx.routes.size() + " / " + target + " (tentativas: " + attempts + ")");
        System.out.printf(Locale.US, "    conectividade vilas: min=%d max=%d media=%.2f%n", minDegree, maxDegree, avgDegree);
    }

    private boolean tryCreateRoute(RouteCandidate cand, List<Poi> villages, int[] degree, Set<Long> attemptedPairs, int routeId) {
        long key = pairKey(cand.a, cand.b);
        if (attemptedPairs.contains(key)) {
            return false;
        }
        attemptedPairs.add(key);
        List<int[]> path = findPath(villages.get(cand.a), villages.get(cand.b));
        if (path == null || path.size() < 2) {
            return false;
        }
        degree[cand.a]++;
        degree[cand.b]++;
        ctx.routes.add(new RouteData(routeId, villages.get(cand.a), villages.get(cand.b), path));
        return true;
    }

    private List<Poi> villages() {
        List<Poi> out = new ArrayList<>();
        for (Poi poi : ctx.pois) {
            if (poi.type == PoiType.VILLAGE) {
                out.add(poi);
            }
        }
        return out;
    }

    private void buildCellCostMap() {
        for (int cy = 0; cy < cellsY; cy++) {
            int y0 = cy * step;
            int y1 = Math.min(ctx.height, y0 + step);
            for (int cx = 0; cx < cellsX; cx++) {
                int x0 = cx * step;
                int x1 = Math.min(ctx.width, x0 + step);
                int deep = 0;
                int shallow = 0;
                int land = 0;
                int total = 0;
                for (int y = y0; y < y1; y++) {
                    for (int x = x0; x < x1; x++) {
                        Tile tile = Tile.values()[ctx.tileMap[ctx.index(x, y)] & 0xFF];
                        total++;
                        if (tile == Tile.WATER_DEEP) {
                            deep++;
                        } else if (tile == Tile.WATER_SHALLOW) {
                            shallow++;
                        } else {
                            land++;
                        }
                    }
                }
                int centerX = Math.min(ctx.width - 1, x0 + Math.max(0, (x1 - x0) / 2));
                int centerY = Math.min(ctx.height - 1, y0 + Math.max(0, (y1 - y0) / 2));
                Tile centerTile = Tile.values()[ctx.tileMap[ctx.index(centerX, centerY)] & 0xFF];
                double cost;
                if (centerTile == Tile.WATER_DEEP || land == 0 && shallow == 0) {
                    cost = INF;
                } else {
                    cost = 1.0;
                    cost += (shallow / (double) Math.max(1, total)) * rules.shallowWaterPenalty;
                    cost += (deep / (double) Math.max(1, total)) * 60.0;
                    if (deep * 2 >= total && land * 3 < total * 2) {
                        cost = INF;
                    }
                }
                cellCost[cellIndex(cx, cy)] = cost;
            }
        }
    }

    private RouteCandidate buildCandidate(List<Poi> villages, int a, int b) {
        Poi va = villages.get(a);
        Poi vb = villages.get(b);
        double dist = Math.sqrt(ctx.distanceSquared(va.x, va.y, vb.x, vb.y));
        if (dist < rules.minDistance || dist > rules.maxDistance) {
            return null;
        }
        double sortScore = dist;
        if (va.regionId == vb.regionId) {
            sortScore *= Math.max(0.1, rules.sameRegionBonus);
        }
        sortScore += ctx.random01(ctx.seed + a * 941L + b * 1451L) * 0.001;
        return new RouteCandidate(Math.min(a, b), Math.max(a, b), dist, sortScore);
    }

    private List<int[]> findPath(Poi from, Poi to) {
        int sx = clampCell(from.x / step, cellsX);
        int sy = clampCell(from.y / step, cellsY);
        int tx = clampCell(to.x / step, cellsX);
        int ty = clampCell(to.y / step, cellsY);
        int start = cellIndex(sx, sy);
        int goal = cellIndex(tx, ty);

        double[] g = new double[cellsX * cellsY];
        int[] parent = new int[cellsX * cellsY];
        boolean[] closed = new boolean[cellsX * cellsY];
        for (int i = 0; i < g.length; i++) {
            g[i] = INF;
            parent[i] = -1;
        }
        PriorityQueue<RouteNode> open = new PriorityQueue<>((l, r) -> Double.compare(l.f, r.f));
        g[start] = 0.0;
        open.add(new RouteNode(start, heuristic(sx, sy, tx, ty), 0.0));

        final int[] ox = {-1, 0, 1, -1, 1, -1, 0, 1};
        final int[] oy = {-1, -1, -1, 0, 0, 1, 1, 1};

        while (!open.isEmpty()) {
            RouteNode node = open.poll();
            if (closed[node.index]) {
                continue;
            }
            if (node.index == goal) {
                return reconstructPath(parent, goal, from, to);
            }
            closed[node.index] = true;
            int cx = node.index % cellsX;
            int cy = node.index / cellsX;
            for (int dir = 0; dir < ox.length; dir++) {
                int nx = cx + ox[dir];
                int ny = cy + oy[dir];
                if (nx < 0 || ny < 0 || nx >= cellsX || ny >= cellsY) {
                    continue;
                }
                int next = cellIndex(nx, ny);
                double nextCost = cellCost[next];
                if (nextCost >= INF) {
                    continue;
                }
                double stepCost = (ox[dir] != 0 && oy[dir] != 0) ? 1.41421356237 : 1.0;
                double tentative = g[node.index] + stepCost * nextCost;
                if (tentative >= g[next]) {
                    continue;
                }
                g[next] = tentative;
                parent[next] = node.index;
                open.add(new RouteNode(next, tentative + heuristic(nx, ny, tx, ty), tentative));
            }
        }
        return null;
    }

    private List<int[]> reconstructPath(int[] parent, int goal, Poi from, Poi to) {
        ArrayList<int[]> reversed = new ArrayList<>();
        int cur = goal;
        while (cur >= 0) {
            reversed.add(cellCenterPoint(cur));
            cur = parent[cur];
        }
        ArrayList<int[]> points = new ArrayList<>();
        points.add(new int[] {from.x, from.y});
        for (int i = reversed.size() - 1; i >= 0; i--) {
            int[] p = reversed.get(i);
            if (!samePoint(points.get(points.size() - 1), p)) {
                points.add(p);
            }
        }
        if (!samePoint(points.get(points.size() - 1), new int[] {to.x, to.y})) {
            points.add(new int[] {to.x, to.y});
        }
        return simplify(points);
    }

    private ArrayList<int[]> simplify(ArrayList<int[]> points) {
        if (points.size() <= 2) {
            return points;
        }
        ArrayList<int[]> out = new ArrayList<>();
        out.add(points.get(0));
        for (int i = 1; i < points.size() - 1; i++) {
            int[] a = out.get(out.size() - 1);
            int[] b = points.get(i);
            int[] c = points.get(i + 1);
            int abx = Integer.compare(b[0], a[0]);
            int aby = Integer.compare(b[1], a[1]);
            int bcx = Integer.compare(c[0], b[0]);
            int bcy = Integer.compare(c[1], b[1]);
            if (abx == bcx && aby == bcy) {
                continue;
            }
            out.add(b);
        }
        out.add(points.get(points.size() - 1));
        return out;
    }

    private void carveRoute(RouteData route) {
        for (int i = 1; i < route.points.size(); i++) {
            int[] a = route.points.get(i - 1);
            int[] b = route.points.get(i);
            carveSegment(a[0], a[1], b[0], b[1], rules.routeBrushRadius);
        }
    }

    private void carveSegment(int x0, int y0, int x1, int y1, int radius) {
        int dx = Math.abs(x1 - x0);
        int dy = Math.abs(y1 - y0);
        int sx = x0 < x1 ? 1 : -1;
        int sy = y0 < y1 ? 1 : -1;
        int err = dx - dy;
        int x = x0;
        int y = y0;
        while (true) {
            clearCircle(x, y, radius);
            if (x == x1 && y == y1) {
                break;
            }
            int e2 = err * 2;
            if (e2 > -dy) {
                err -= dy;
                x += sx;
            }
            if (e2 < dx) {
                err += dx;
                y += sy;
            }
        }
    }

    private void clearCircle(int cx, int cy, int radius) {
        int rr = radius * radius;
        for (int dy = -radius; dy <= radius; dy++) {
            int y = cy + dy;
            if (y < 0 || y >= ctx.height) {
                continue;
            }
            for (int dx = -radius; dx <= radius; dx++) {
                int x = cx + dx;
                if (x < 0 || x >= ctx.width) {
                    continue;
                }
                if (dx * dx + dy * dy > rr) {
                    continue;
                }
                Tile tile = Tile.values()[ctx.tileMap[ctx.index(x, y)] & 0xFF];
                if (tile == Tile.WATER_DEEP) {
                    continue;
                }
                ctx.naturalMap[ctx.index(x, y)] = (byte) NaturalStructure.NONE.ordinal();
            }
        }
    }

    private int[] cellCenterPoint(int index) {
        int cx = index % cellsX;
        int cy = index / cellsX;
        int x0 = cx * step;
        int y0 = cy * step;
        int x = Math.min(ctx.width - 1, x0 + step / 2);
        int y = Math.min(ctx.height - 1, y0 + step / 2);
        return new int[] {x, y};
    }

    private int cellIndex(int x, int y) {
        return y * cellsX + x;
    }

    private int clampCell(int value, int limit) {
        return Math.max(0, Math.min(limit - 1, value));
    }

    private double heuristic(int x, int y, int tx, int ty) {
        double dx = tx - x;
        double dy = ty - y;
        return Math.sqrt(dx * dx + dy * dy);
    }

    private int rangedValue(int min, int max, long salt) {
        if (max <= min) {
            return min;
        }
        return ctx.boundedRandomInt(min, max + 1, ctx.seed + salt);
    }

    private long pairKey(int a, int b) {
        int min = Math.min(a, b);
        int max = Math.max(a, b);
        return (((long) min) << 32) | (max & 0xFFFFFFFFL);
    }

    private boolean samePoint(int[] a, int[] b) {
        return a[0] == b[0] && a[1] == b[1];
    }

    private static final class RouteCandidate {
        final int a;
        final int b;
        final double dist;
        final double sortScore;

        RouteCandidate(int a, int b, double dist, double sortScore) {
            this.a = a;
            this.b = b;
            this.dist = dist;
            this.sortScore = sortScore;
        }
    }

    private static final class RouteNode {
        final int index;
        final double f;
        final double g;

        RouteNode(int index, double f, double g) {
            this.index = index;
            this.f = f;
            this.g = g;
        }
    }
}
