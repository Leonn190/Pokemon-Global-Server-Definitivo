import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

final class LocalityPoiConfig {
    final int count;
    final int minDistance;
    final int margin;
    final int nearWaterRadius;
    final EnumSet<Biome> allowedBiomes;
    final int areaChunks;
    final int clearMarginTiles;

    LocalityPoiConfig(int count, int minDistance, int margin, int nearWaterRadius, EnumSet<Biome> allowedBiomes, int areaChunks, int clearMarginTiles) {
        this.count = count;
        this.minDistance = minDistance;
        this.margin = margin;
        this.nearWaterRadius = nearWaterRadius;
        this.allowedBiomes = allowedBiomes;
        this.areaChunks = areaChunks;
        this.clearMarginTiles = clearMarginTiles;
    }
}

final class LocalityRules {
    final int regionMinCount;
    final int regionMaxCount;
    final int regionMargin;
    final int regionMinCenterDistance;

    final int villageMinCount;
    final int villageMaxCount;
    final int villageMinDistance;
    final int villageMargin;
    final int villageNearWaterRadius;
    final EnumSet<Biome> villageAllowedBiomes;
    final int villageClearRadius;

    final int housesMinPerVillage;
    final int housesMaxPerVillage;
    final int houseRadius;
    final int houseMinDistanceFromCenter;

    final LocalityPoiConfig gymConfig;

    final List<String> regionNames;
    final List<String> villageNames;

    LocalityRules(
        int regionMinCount,
        int regionMaxCount,
        int regionMargin,
        int regionMinCenterDistance,
        int villageMinCount,
        int villageMaxCount,
        int villageMinDistance,
        int villageMargin,
        int villageNearWaterRadius,
        EnumSet<Biome> villageAllowedBiomes,
        int villageClearRadius,
        int housesMinPerVillage,
        int housesMaxPerVillage,
        int houseRadius,
        int houseMinDistanceFromCenter,
        LocalityPoiConfig gymConfig,
        List<String> regionNames,
        List<String> villageNames
    ) {
        this.regionMinCount = regionMinCount;
        this.regionMaxCount = regionMaxCount;
        this.regionMargin = regionMargin;
        this.regionMinCenterDistance = regionMinCenterDistance;
        this.villageMinCount = villageMinCount;
        this.villageMaxCount = villageMaxCount;
        this.villageMinDistance = villageMinDistance;
        this.villageMargin = villageMargin;
        this.villageNearWaterRadius = villageNearWaterRadius;
        this.villageAllowedBiomes = villageAllowedBiomes;
        this.villageClearRadius = villageClearRadius;
        this.housesMinPerVillage = housesMinPerVillage;
        this.housesMaxPerVillage = housesMaxPerVillage;
        this.houseRadius = houseRadius;
        this.houseMinDistanceFromCenter = houseMinDistanceFromCenter;
        this.gymConfig = gymConfig;
        this.regionNames = regionNames;
        this.villageNames = villageNames;
    }

    static LocalityRules load(Path path) throws IOException {
        if (!Files.exists(path)) {
            throw new IOException("Arquivo de regras de localidades nao encontrado: " + path);
        }
        TomlTable root = SimpleToml.parse(path);
        TomlTable regions = root.table("regions");
        TomlTable villages = root.table("villages");
        TomlTable houses = root.table("houses");
        TomlTable gyms = root.table("gyms");

        return new LocalityRules(
            regions.reqInt("min_count"),
            regions.reqInt("max_count"),
            regions.reqInt("margin"),
            regions.reqInt("min_center_distance"),
            villages.reqInt("min_count"),
            villages.reqInt("max_count"),
            villages.reqInt("min_distance"),
            villages.reqInt("margin"),
            villages.reqInt("near_water_radius"),
            SimpleToml.enumSet(Biome.class, villages.reqStringList("allowed_biomes")),
            villages.reqInt("clear_radius"),
            houses.reqInt("min_per_village"),
            houses.reqInt("max_per_village"),
            houses.reqInt("radius"),
            houses.reqInt("min_distance_from_center"),
            readPoiConfig(gyms),
            dedupeNames(regions.reqStringList("name_candidates")),
            dedupeNames(villages.reqStringList("name_candidates"))
        );
    }

    private static LocalityPoiConfig readPoiConfig(TomlTable table) {
        return new LocalityPoiConfig(
            table.reqInt("count"),
            table.reqInt("min_distance"),
            table.reqInt("margin"),
            table.reqInt("near_water_radius"),
            SimpleToml.enumSet(Biome.class, table.reqStringList("allowed_biomes")),
            table.optInt("area_chunks", 0),
            table.optInt("clear_margin_tiles", 0)
        );
    }

    private static List<String> dedupeNames(List<String> names) {
        Set<String> seen = new LinkedHashSet<>();
        for (String raw : names) {
            String text = raw == null ? "" : raw.trim();
            if (!text.isEmpty()) {
                seen.add(text);
            }
        }
        return new ArrayList<>(seen);
    }
}

final class GeradorLocalidades {
    private static final int[] REGION_COLORS = {
        rgb(255, 99, 132),
        rgb(54, 162, 235),
        rgb(255, 206, 86),
        rgb(75, 192, 192),
        rgb(153, 102, 255),
        rgb(255, 159, 64),
        rgb(46, 204, 113),
        rgb(231, 76, 60)
    };

    private final GeneratorContext ctx;
    private final LocalityRules rules;

    GeradorLocalidades(GeneratorContext ctx) {
        this.ctx = ctx;
        this.rules = ctx.localityRules;
    }

    void generate() {
        ctx.regions.clear();
        ctx.pois.clear();
        generateRegions();
        generateVillages();
        generateGyms();
    }

    RegionData nearestRegion(int x, int y) {
        if (ctx.regions.isEmpty()) {
            return new RegionData(0, "Regiao Central", ctx.width / 2, ctx.height / 2, REGION_COLORS[0]);
        }
        RegionData best = ctx.regions.get(0);
        long bestDist = Long.MAX_VALUE;
        for (RegionData region : ctx.regions) {
            long dist = ctx.distanceSquared(x, y, region.centerX, region.centerY);
            if (dist < bestDist) {
                bestDist = dist;
                best = region;
            }
        }
        return best;
    }

    boolean isReservedForNaturalStructure(int x, int y) {
        for (Poi poi : ctx.pois) {
            if (poi.type == PoiType.VILLAGE) {
                long rr = (long) rules.villageClearRadius * rules.villageClearRadius;
                if (ctx.distanceSquared(x, y, poi.x, poi.y) <= rr) {
                    return true;
                }
            } else if (poi.type == PoiType.GYM && isInsideGymReservedArea(x, y, poi, rules.gymConfig)) {
                return true;
            }
        }
        return false;
    }

    private void generateRegions() {
        int target = rangedValue(rules.regionMinCount, rules.regionMaxCount, 101L);
        List<String> names = buildNames(rules.regionNames, target, "Regiao");
        int attempts = 0;
        int placed = 0;
        while (placed < target && attempts < target * 120_000L) {
            attempts++;
            int x = ctx.boundedRandomInt(rules.regionMargin, ctx.width - rules.regionMargin, ctx.seed + 17L * attempts);
            int y = ctx.boundedRandomInt(rules.regionMargin, ctx.height - rules.regionMargin, ctx.seed + 29L * attempts);
            if (!isLandCandidate(x, y)) {
                continue;
            }
            if (ctx.nearWater(x, y, 2)) {
                continue;
            }
            boolean nearOtherCenter = false;
            for (RegionData region : ctx.regions) {
                if (ctx.distanceSquared(x, y, region.centerX, region.centerY)
                    < (long) rules.regionMinCenterDistance * rules.regionMinCenterDistance) {
                    nearOtherCenter = true;
                    break;
                }
            }
            if (nearOtherCenter) {
                continue;
            }
            ctx.regions.add(new RegionData(placed, names.get(placed), x, y, REGION_COLORS[placed % REGION_COLORS.length]));
            placed++;
        }

        if (ctx.regions.isEmpty()) {
            int fallbackX = ctx.width / 2;
            int fallbackY = ctx.height / 2;
            ctx.regions.add(new RegionData(0, names.get(0), fallbackX, fallbackY, REGION_COLORS[0]));
        }
        System.out.println("  Regioes: " + ctx.regions.size() + " / " + target + " (tentativas: " + attempts + ")");
    }

    private void generateVillages() {
        int target = rangedValue(rules.villageMinCount, rules.villageMaxCount, 211L);
        List<String> names = buildNames(rules.villageNames, target, "Vila");
        int placed = 0;
        int nameIndex = 0;

        for (RegionData region : ctx.regions) {
            if (placed >= target) {
                break;
            }
            if (tryPlaceVillageForRegion(region, names.get(nameIndex), nameIndex)) {
                placed++;
                nameIndex++;
            }
        }

        int attempts = 0;
        while (placed < target && attempts < target * 140_000L) {
            attempts++;
            int x = ctx.boundedRandomInt(rules.villageMargin, ctx.width - rules.villageMargin, ctx.seed + 401L + attempts * 43L);
            int y = ctx.boundedRandomInt(rules.villageMargin, ctx.height - rules.villageMargin, ctx.seed + 607L + attempts * 59L);
            if (!canPlaceVillage(x, y)) {
                continue;
            }
            placeVillage(x, y, names.get(nameIndex));
            placed++;
            nameIndex++;
        }
        System.out.println("  Vilas: " + placed + " / " + target + " (tentativas livres: " + attempts + ")");
    }

    private boolean tryPlaceVillageForRegion(RegionData region, String name, int saltIndex) {
        int radius = Math.max(320, Math.min(ctx.width, ctx.height) / Math.max(6, ctx.regions.size() * 2));
        for (int attempt = 1; attempt <= 18_000; attempt++) {
            int x = ctx.clamp(region.centerX + signedRandom(radius, ctx.seed + 10_000L + saltIndex * 911L + attempt * 31L), rules.villageMargin, ctx.width - rules.villageMargin - 1);
            int y = ctx.clamp(region.centerY + signedRandom(radius, ctx.seed + 20_000L + saltIndex * 977L + attempt * 37L), rules.villageMargin, ctx.height - rules.villageMargin - 1);
            if (nearestRegion(x, y).id != region.id) {
                continue;
            }
            if (!canPlaceVillage(x, y)) {
                continue;
            }
            placeVillage(x, y, name);
            return true;
        }
        return false;
    }

    private boolean canPlaceVillage(int x, int y) {
        if (!isLandCandidate(x, y)) {
            return false;
        }
        Biome biome = Biome.values()[ctx.biomeMap[ctx.index(x, y)] & 0xFF];
        if (!rules.villageAllowedBiomes.contains(biome)) {
            return false;
        }
        if (rules.villageNearWaterRadius > 0 && ctx.nearWater(x, y, rules.villageNearWaterRadius)) {
            return false;
        }
        for (Poi poi : ctx.pois) {
            if (ctx.distanceSquared(x, y, poi.x, poi.y) < (long) rules.villageMinDistance * rules.villageMinDistance) {
                return false;
            }
        }
        return true;
    }

    private void placeVillage(int x, int y, String name) {
        RegionData region = nearestRegion(x, y);
        Poi village = new Poi(x, y, PoiType.VILLAGE, name, region.id);
        ctx.pois.add(village);
        clearVillageArea(village);
        placeVillageHouses(village);
    }

    private void clearVillageArea(Poi village) {
        int radius = Math.max(1, rules.villageClearRadius);
        for (int dy = -radius; dy <= radius; dy++) {
            int y = village.y + dy;
            if (y < 0 || y >= ctx.height) {
                continue;
            }
            for (int dx = -radius; dx <= radius; dx++) {
                int x = village.x + dx;
                if (x < 0 || x >= ctx.width) {
                    continue;
                }
                if (dx * dx + dy * dy > radius * radius) {
                    continue;
                }
                ctx.naturalMap[ctx.index(x, y)] = (byte) NaturalStructure.NONE.ordinal();
            }
        }
    }

    private void placeVillageHouses(Poi village) {
        int houseTarget = rangedValue(rules.housesMinPerVillage, rules.housesMaxPerVillage, 5_001L + village.x * 13L + village.y * 17L);
        int placed = 0;
        int attempts = 0;
        while (placed < houseTarget && attempts < houseTarget * 140) {
            attempts++;
            int dist = Math.max(rules.houseMinDistanceFromCenter,
                ctx.boundedRandomInt(rules.houseMinDistanceFromCenter, Math.max(rules.houseMinDistanceFromCenter + 1, rules.houseRadius + 1), ctx.seed + village.x * 71L + village.y * 89L + attempts * 23L));
            double angle = ctx.random01(ctx.seed + village.x * 101L + village.y * 131L + attempts * 41L) * (Math.PI * 2.0);
            int x = village.x + (int) Math.round(Math.cos(angle) * dist);
            int y = village.y + (int) Math.round(Math.sin(angle) * dist);
            if (x <= 1 || y <= 1 || x >= ctx.width - 1 || y >= ctx.height - 1) {
                continue;
            }
            if (!isLandCandidate(x, y) || ctx.nearWater(x, y, 1)) {
                continue;
            }
            if (ctx.distanceSquared(x, y, village.x, village.y) <= 1) {
                continue;
            }
            int idx = ctx.index(x, y);
            if (ctx.naturalMap[idx] != (byte) NaturalStructure.NONE.ordinal()) {
                continue;
            }
            boolean overlapsPoi = false;
            for (Poi poi : ctx.pois) {
                if (poi.x == x && poi.y == y) {
                    overlapsPoi = true;
                    break;
                }
            }
            if (overlapsPoi) {
                continue;
            }
            ctx.naturalMap[idx] = (byte) NaturalStructure.HOUSE.ordinal();
            placed++;
        }
    }

    private void generateGyms() {
        int placed = 0;
        int attempts = 0;
        while (placed < rules.gymConfig.count && attempts < rules.gymConfig.count * 120_000L) {
            attempts++;
            int x = ctx.boundedRandomInt(rules.gymConfig.margin, ctx.width - rules.gymConfig.margin, ctx.seed + 90_001L + attempts * 53L);
            int y = ctx.boundedRandomInt(rules.gymConfig.margin, ctx.height - rules.gymConfig.margin, ctx.seed + 91_003L + attempts * 67L);
            if (!canPlaceGym(x, y, rules.gymConfig)) {
                continue;
            }
            RegionData region = nearestRegion(x, y);
            ctx.pois.add(new Poi(x, y, PoiType.GYM, null, region.id));
            placed++;
        }

        if (placed < rules.gymConfig.count) {
            int relaxedMinDistance = Math.max(ctx.terrainRules.chunkSize * 6, (int) Math.round(rules.gymConfig.minDistance * 0.72));
            LocalityPoiConfig relaxed = new LocalityPoiConfig(
                rules.gymConfig.count,
                relaxedMinDistance,
                Math.max(8, rules.gymConfig.margin / 2),
                Math.max(2, rules.gymConfig.nearWaterRadius - 1),
                rules.gymConfig.allowedBiomes,
                rules.gymConfig.areaChunks,
                rules.gymConfig.clearMarginTiles
            );
            int relaxedAttempts = 0;
            while (placed < rules.gymConfig.count && relaxedAttempts < rules.gymConfig.count * 90_000L) {
                relaxedAttempts++;
                int x = ctx.boundedRandomInt(relaxed.margin, ctx.width - relaxed.margin, ctx.seed + 190_001L + relaxedAttempts * 79L);
                int y = ctx.boundedRandomInt(relaxed.margin, ctx.height - relaxed.margin, ctx.seed + 191_003L + relaxedAttempts * 97L);
                if (!canPlaceGym(x, y, relaxed)) {
                    continue;
                }
                RegionData region = nearestRegion(x, y);
                ctx.pois.add(new Poi(x, y, PoiType.GYM, null, region.id));
                placed++;
            }
            attempts += relaxedAttempts;
        }
        System.out.println("  Ginasios: " + placed + " / " + rules.gymConfig.count + " (tentativas: " + attempts + ")");
    }

    private boolean canPlaceGym(int x, int y, LocalityPoiConfig config) {
        if (!isLandCandidate(x, y)) {
            return false;
        }
        Biome biome = Biome.values()[ctx.biomeMap[ctx.index(x, y)] & 0xFF];
        if (!config.allowedBiomes.contains(biome)) {
            return false;
        }
        if (config.nearWaterRadius > 0 && ctx.nearWater(x, y, config.nearWaterRadius)) {
            return false;
        }
        for (Poi poi : ctx.pois) {
            if (ctx.distanceSquared(x, y, poi.x, poi.y) < (long) config.minDistance * config.minDistance) {
                return false;
            }
        }
        return isGymAreaValid(x, y, config);
    }

    private boolean isGymAreaValid(int centerX, int centerY, LocalityPoiConfig config) {
        int half = (config.areaChunks * ctx.terrainRules.chunkSize) / 2;
        int x0 = centerX - half;
        int y0 = centerY - half;
        int x1 = x0 + (config.areaChunks * ctx.terrainRules.chunkSize) - 1;
        int y1 = y0 + (config.areaChunks * ctx.terrainRules.chunkSize) - 1;
        if (x0 < 2 || y0 < 2 || x1 >= ctx.width - 2 || y1 >= ctx.height - 2) {
            return false;
        }
        for (int y = y0; y <= y1; y++) {
            for (int x = x0; x <= x1; x++) {
                if (!isLandCandidate(x, y) || ctx.nearWater(x, y, 2)) {
                    return false;
                }
            }
        }
        return true;
    }

    private boolean isInsideGymReservedArea(int x, int y, Poi gym, LocalityPoiConfig config) {
        int half = (config.areaChunks * ctx.terrainRules.chunkSize) / 2;
        int margin = config.clearMarginTiles;
        return x >= gym.x - half - margin
            && x <= gym.x + half + margin
            && y >= gym.y - half - margin
            && y <= gym.y + half + margin;
    }

    private boolean isLandCandidate(int x, int y) {
        int idx = ctx.index(x, y);
        return ctx.isLandBiome(Biome.values()[ctx.biomeMap[idx] & 0xFF]);
    }

    private int rangedValue(int min, int max, long salt) {
        if (max <= min) {
            return min;
        }
        return ctx.boundedRandomInt(min, max + 1, ctx.seed + salt);
    }

    private int signedRandom(int amplitude, long seedValue) {
        if (amplitude <= 0) {
            return 0;
        }
        return ctx.boundedRandomInt(-amplitude, amplitude + 1, seedValue);
    }

    private List<String> buildNames(List<String> candidates, int count, String prefix) {
        List<String> out = new ArrayList<>(count);
        if (candidates.isEmpty()) {
            for (int i = 0; i < count; i++) {
                out.add(prefix + " " + (i + 1));
            }
            return out;
        }
        int start = ctx.boundedRandomInt(0, candidates.size(), ctx.seed + prefix.hashCode() * 17L);
        for (int i = 0; i < count; i++) {
            if (i < candidates.size()) {
                out.add(candidates.get((start + i) % candidates.size()));
            } else {
                out.add(candidates.get((start + (i % candidates.size())) % candidates.size()) + " " + (i + 1));
            }
        }
        return out;
    }

    private static int rgb(int r, int g, int b) {
        return (r << 16) | (g << 8) | b;
    }
}
