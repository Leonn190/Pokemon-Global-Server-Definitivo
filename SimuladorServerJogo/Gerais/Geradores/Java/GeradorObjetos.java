
import java.util.Arrays;
import java.util.EnumMap;
import java.util.List;
import java.util.Locale;

final class GeradorObjetos {
    private final GeneratorContext ctx;
    private final TerrainRules terrainRules;
    private final BiomeRules biomeRules;

    GeradorObjetos(GeneratorContext ctx) {
        this.ctx = ctx;
        this.terrainRules = ctx.terrainRules;
        this.biomeRules = ctx.biomeRules;
    }

    void placeNaturalStructures() {
        Arrays.fill(ctx.naturalMap, (byte) NaturalStructure.NONE.ordinal());

        for (int y = 0; y < ctx.height; y++) {
            if (y % 800 == 0) {
                System.out.println("  estruturas na linha " + y + " / " + ctx.height);
            }
            for (int x = 0; x < ctx.width; x++) {
                int idx = ctx.index(x, y);
                Biome biome = Biome.values()[ctx.biomeMap[idx] & 0xFF];
                if (!ctx.isLandBiome(biome)) {
                    continue;
                }
                if (biomeRules.objectAvoidBeachTiles && Tile.values()[ctx.tileMap[idx] & 0xFF] == Tile.BEACH_SAND) {
                    continue;
                }
                if (ctx.nearPoi(x, y, biomeRules.objectBlockNearPoiRadius)) {
                    continue;
                }
                NaturalStructure structure = chooseNaturalStructure(biome, x, y);
                if (structure == NaturalStructure.NONE) {
                    continue;
                }
                ctx.naturalMap[idx] = (byte) structure.ordinal();
            }
        }
        ctx.recountNaturals();
    }

    void placePois() {
        ctx.pois.clear();
        placePoiType(PoiType.VILLAGE, terrainRules.villageConfig);
        placePoiType(PoiType.GYM, terrainRules.gymConfig);
        placePoiType(PoiType.DUNGEON, terrainRules.dungeonConfig);
    }

    private void placePoiType(PoiType type, PoiConfig config) {
        int placed = 0;
        int attempts = 0;
        while (placed < config.count && attempts < config.count * 80_000L) {
            attempts++;
            int x = ctx.boundedRandomInt(config.margin, ctx.width - config.margin, ctx.seed + type.ordinal() * 10_000_000L + attempts * 53L);
            int y = ctx.boundedRandomInt(config.margin, ctx.height - config.margin, ctx.seed + type.ordinal() * 10_000_000L + attempts * 67L);
            if (!canPlacePoi(type, config, x, y)) {
                continue;
            }
            Poi poi = new Poi(x, y, type);
            ctx.pois.add(poi);
            if (type == PoiType.GYM) {
                clearNaturalsNearGym(poi, config);
            }
            placed++;
        }
        System.out.println("  " + type + ": " + placed + " / " + config.count + " (tentativas: " + attempts + ")");
    }

    private boolean canPlacePoi(PoiType type, PoiConfig config, int x, int y) {
        int idx = ctx.index(x, y);
        Biome biome = Biome.values()[ctx.biomeMap[idx] & 0xFF];
        if (!ctx.isLandBiome(biome)) {
            return false;
        }
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
        if (type == PoiType.GYM && !isGymAreaValid(x, y, config)) {
            return false;
        }
        return true;
    }

    private boolean isGymAreaValid(int centerX, int centerY, PoiConfig config) {
        int half = (config.areaChunks * terrainRules.chunkSize) / 2;
        int x0 = centerX - half;
        int y0 = centerY - half;
        int x1 = x0 + (config.areaChunks * terrainRules.chunkSize) - 1;
        int y1 = y0 + (config.areaChunks * terrainRules.chunkSize) - 1;
        if (x0 < 2 || y0 < 2 || x1 >= ctx.width - 2 || y1 >= ctx.height - 2) {
            return false;
        }
        for (int y = y0; y <= y1; y++) {
            for (int x = x0; x <= x1; x++) {
                int idx = ctx.index(x, y);
                Biome biome = Biome.values()[ctx.biomeMap[idx] & 0xFF];
                if (!ctx.isLandBiome(biome) || ctx.nearWater(x, y, 2)) {
                    return false;
                }
            }
        }
        return true;
    }

    private void clearNaturalsNearGym(Poi gym, PoiConfig config) {
        int half = (config.areaChunks * terrainRules.chunkSize) / 2;
        int x0 = Math.max(0, gym.x - half - config.clearMarginTiles);
        int y0 = Math.max(0, gym.y - half - config.clearMarginTiles);
        int x1 = Math.min(ctx.width - 1, gym.x + half + config.clearMarginTiles);
        int y1 = Math.min(ctx.height - 1, gym.y + half + config.clearMarginTiles);
        for (int y = y0; y <= y1; y++) {
            for (int x = x0; x <= x1; x++) {
                ctx.naturalMap[ctx.index(x, y)] = (byte) NaturalStructure.NONE.ordinal();
            }
        }
        ctx.recountNaturals();
    }

    private NaturalStructure chooseNaturalStructure(Biome biome, int x, int y) {
        EnumMap<NaturalStructure, Double> rates = biomeRules.objectRates.get(biome);
        if (rates == null || rates.isEmpty()) {
            return NaturalStructure.NONE;
        }
        double total = 0.0;
        for (double rate : rates.values()) {
            if (rate > 0.0) {
                total += rate;
            }
        }
        if (total <= 0.0) {
            return NaturalStructure.NONE;
        }

        double roll = ctx.random01(ctx.tileSeed(x, y, 701L));
        if (roll >= total) {
            return NaturalStructure.NONE;
        }

        double acc = 0.0;
        for (NaturalStructure structure : NaturalStructure.values()) {
            if (structure == NaturalStructure.NONE) {
                continue;
            }
            double rate = rates.getOrDefault(structure, 0.0);
            if (rate <= 0.0) {
                continue;
            }
            acc += rate;
            if (roll < acc) {
                return structure;
            }
        }
        return NaturalStructure.NONE;
    }
}
