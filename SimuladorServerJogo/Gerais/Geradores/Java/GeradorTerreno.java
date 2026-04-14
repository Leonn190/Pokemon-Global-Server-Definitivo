import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

final class NoiseLayerConfig {
    final int octaves;
    final double persistence;
    final double lacunarity;
    final double scale;
    final long seedOffset;
    final double weight;
    final boolean ridge;

    NoiseLayerConfig(int octaves, double persistence, double lacunarity, double scale, long seedOffset, double weight, boolean ridge) {
        this.octaves = octaves;
        this.persistence = persistence;
        this.lacunarity = lacunarity;
        this.scale = scale;
        this.seedOffset = seedOffset;
        this.weight = weight;
        this.ridge = ridge;
    }
}

final class PoiConfig {
    final int count;
    final int minDistance;
    final int margin;
    final int nearWaterRadius;
    final EnumSet<Biome> allowedBiomes;
    final int areaChunks;
    final int clearMarginTiles;

    PoiConfig(int count, int minDistance, int margin, int nearWaterRadius, EnumSet<Biome> allowedBiomes, int areaChunks, int clearMarginTiles) {
        this.count = count;
        this.minDistance = minDistance;
        this.margin = margin;
        this.nearWaterRadius = nearWaterRadius;
        this.allowedBiomes = allowedBiomes;
        this.areaChunks = areaChunks;
        this.clearMarginTiles = clearMarginTiles;
    }
}

final class TerrainRules {
    final int width;
    final int height;
    final int chunkSize;
    final int chunksPerFile;

    final int hardOceanBorder;
    final int softOceanBorder;
    final double edgeWaterPenaltyStrength;
    final double seaLevel;
    final double deepWaterExtraDepth;
    final double shallowWaterBand;
    final int oceanDetectionRadius;
    final int waterDetectionRadiusForBeach;
    final int shallowWaterNearLandRadius;

    final double lakeElevationOffsetFromSeaLevel;
    final double lakeMinMoisture;
    final int lakeBorderBlockDistance;
    final double lakeNoiseThreshold;
    final NoiseLayerConfig lakeNoise;

    final int riverSources;
    final int riverMaxLength;
    final int riverWidth;
    final int riverMinWidth;
    final int riverMaxWidth;
    final int riverTerminalExtraWidth;
    final double riverSourceMinHeight;
    final int riverSourceMargin;
    final int riverSourceNearWaterRadius;
    final int riverSourceMinDistance;
    final int riverMaxAttemptsPerSource;
    final double riverMomentum;
    final double riverDownhillBias;
    final double riverMeanderStrength;
    final double riverUphillPenalty;
    final int riverSearchRadius;
    final int riverWidthGrowEvery;
    final int riverBankBlendRadius;
    final int riverMouthLength;

    final PoiConfig gymConfig;
    final PoiConfig dungeonConfig;
    final PoiConfig villageConfig;

    final Biome spawnRequiredBiome;
    final boolean spawnRequiresNoObjects;
    final boolean spawnRequiresNoPois;

    final NoiseLayerConfig elevationContinents;
    final NoiseLayerConfig elevationDetail;
    final NoiseLayerConfig elevationRidges;
    final NoiseLayerConfig moistureLarge;
    final NoiseLayerConfig moistureDetail;

    TerrainRules(
        int width,
        int height,
        int chunkSize,
        int chunksPerFile,
        int hardOceanBorder,
        int softOceanBorder,
        double edgeWaterPenaltyStrength,
        double seaLevel,
        double deepWaterExtraDepth,
        double shallowWaterBand,
        int oceanDetectionRadius,
        int waterDetectionRadiusForBeach,
        int shallowWaterNearLandRadius,
        double lakeElevationOffsetFromSeaLevel,
        double lakeMinMoisture,
        int lakeBorderBlockDistance,
        double lakeNoiseThreshold,
        NoiseLayerConfig lakeNoise,
        int riverSources,
        int riverMaxLength,
        int riverWidth,
        int riverMinWidth,
        int riverMaxWidth,
        int riverTerminalExtraWidth,
        double riverSourceMinHeight,
        int riverSourceMargin,
        int riverSourceNearWaterRadius,
        int riverSourceMinDistance,
        int riverMaxAttemptsPerSource,
        double riverMomentum,
        double riverDownhillBias,
        double riverMeanderStrength,
        double riverUphillPenalty,
        int riverSearchRadius,
        int riverWidthGrowEvery,
        int riverBankBlendRadius,
        int riverMouthLength,
        PoiConfig gymConfig,
        PoiConfig dungeonConfig,
        PoiConfig villageConfig,
        Biome spawnRequiredBiome,
        boolean spawnRequiresNoObjects,
        boolean spawnRequiresNoPois,
        NoiseLayerConfig elevationContinents,
        NoiseLayerConfig elevationDetail,
        NoiseLayerConfig elevationRidges,
        NoiseLayerConfig moistureLarge,
        NoiseLayerConfig moistureDetail
    ) {
        this.width = width;
        this.height = height;
        this.chunkSize = chunkSize;
        this.chunksPerFile = chunksPerFile;
        this.hardOceanBorder = hardOceanBorder;
        this.softOceanBorder = softOceanBorder;
        this.edgeWaterPenaltyStrength = edgeWaterPenaltyStrength;
        this.seaLevel = seaLevel;
        this.deepWaterExtraDepth = deepWaterExtraDepth;
        this.shallowWaterBand = shallowWaterBand;
        this.oceanDetectionRadius = oceanDetectionRadius;
        this.waterDetectionRadiusForBeach = waterDetectionRadiusForBeach;
        this.shallowWaterNearLandRadius = shallowWaterNearLandRadius;
        this.lakeElevationOffsetFromSeaLevel = lakeElevationOffsetFromSeaLevel;
        this.lakeMinMoisture = lakeMinMoisture;
        this.lakeBorderBlockDistance = lakeBorderBlockDistance;
        this.lakeNoiseThreshold = lakeNoiseThreshold;
        this.lakeNoise = lakeNoise;
        this.riverSources = riverSources;
        this.riverMaxLength = riverMaxLength;
        this.riverWidth = riverWidth;
        this.riverMinWidth = riverMinWidth;
        this.riverMaxWidth = riverMaxWidth;
        this.riverTerminalExtraWidth = riverTerminalExtraWidth;
        this.riverSourceMinHeight = riverSourceMinHeight;
        this.riverSourceMargin = riverSourceMargin;
        this.riverSourceNearWaterRadius = riverSourceNearWaterRadius;
        this.riverSourceMinDistance = riverSourceMinDistance;
        this.riverMaxAttemptsPerSource = riverMaxAttemptsPerSource;
        this.riverMomentum = riverMomentum;
        this.riverDownhillBias = riverDownhillBias;
        this.riverMeanderStrength = riverMeanderStrength;
        this.riverUphillPenalty = riverUphillPenalty;
        this.riverSearchRadius = riverSearchRadius;
        this.riverWidthGrowEvery = riverWidthGrowEvery;
        this.riverBankBlendRadius = riverBankBlendRadius;
        this.riverMouthLength = riverMouthLength;
        this.gymConfig = gymConfig;
        this.dungeonConfig = dungeonConfig;
        this.villageConfig = villageConfig;
        this.spawnRequiredBiome = spawnRequiredBiome;
        this.spawnRequiresNoObjects = spawnRequiresNoObjects;
        this.spawnRequiresNoPois = spawnRequiresNoPois;
        this.elevationContinents = elevationContinents;
        this.elevationDetail = elevationDetail;
        this.elevationRidges = elevationRidges;
        this.moistureLarge = moistureLarge;
        this.moistureDetail = moistureDetail;
    }

    static TerrainRules load(Path path) throws IOException {
        if (!Files.exists(path)) {
            throw new IOException("Arquivo de regras de terreno nao encontrado: " + path);
        }
        TomlTable root = SimpleToml.parse(path);
        TomlTable world = root.table("world");
        TomlTable ocean = root.table("ocean");
        TomlTable lakes = root.table("lakes");
        TomlTable rivers = root.table("rivers");
        TomlTable pois = root.table("pois");
        TomlTable spawn = root.table("spawn");

        NoiseLayerConfig elevationContinents = readNoiseLayer(root.table("elevation").table("continents"), false, true);
        NoiseLayerConfig elevationDetail = readNoiseLayer(root.table("elevation").table("detail"), false, true);
        NoiseLayerConfig elevationRidges = readNoiseLayer(root.table("elevation").table("ridges"), true, true);
        NoiseLayerConfig moistureLarge = readNoiseLayer(root.table("moisture").table("large"), false, true);
        NoiseLayerConfig moistureDetail = readNoiseLayer(root.table("moisture").table("detail"), false, true);
        NoiseLayerConfig lakeNoise = readNoiseLayer(lakes.table("noise"), false, false);

        return new TerrainRules(
            world.reqInt("width"),
            world.reqInt("height"),
            world.reqInt("chunk_size"),
            world.reqInt("chunks_per_file"),
            ocean.reqInt("hard_border"),
            ocean.reqInt("soft_border"),
            ocean.reqDouble("edge_penalty_strength"),
            ocean.reqDouble("sea_level"),
            ocean.reqDouble("deep_water_extra_depth"),
            ocean.reqDouble("shallow_water_band"),
            ocean.reqInt("ocean_detection_radius"),
            ocean.reqInt("water_detection_radius_for_beach"),
            ocean.reqInt("shallow_water_near_land_radius"),
            lakes.reqDouble("elevation_offset_from_sea_level"),
            lakes.reqDouble("min_moisture"),
            lakes.reqInt("border_block_distance"),
            lakes.reqDouble("threshold"),
            lakeNoise,
            rivers.reqInt("sources"),
            rivers.reqInt("max_length"),
            rivers.reqInt("width"),
            rivers.reqInt("min_width"),
            rivers.reqInt("max_width"),
            rivers.reqInt("terminal_extra_width"),
            rivers.reqDouble("source_min_height"),
            rivers.reqInt("source_margin"),
            rivers.reqInt("source_near_water_radius"),
            rivers.reqInt("source_min_distance"),
            rivers.reqInt("max_attempts_per_source"),
            rivers.reqDouble("momentum"),
            rivers.reqDouble("downhill_bias"),
            rivers.reqDouble("meander_strength"),
            rivers.reqDouble("uphill_penalty"),
            rivers.reqInt("search_radius"),
            rivers.reqInt("width_grow_every"),
            rivers.reqInt("bank_blend_radius"),
            rivers.reqInt("mouth_length"),
            readPoiConfig(pois.table("gym"), false),
            readPoiConfig(pois.table("dungeon"), false),
            readPoiConfig(pois.table("village"), false),
            SimpleToml.enumValue(Biome.class, spawn.reqString("required_biome")),
            spawn.reqBoolean("require_no_objects"),
            spawn.reqBoolean("require_no_pois"),
            elevationContinents,
            elevationDetail,
            elevationRidges,
            moistureLarge,
            moistureDetail
        );
    }

    private static NoiseLayerConfig readNoiseLayer(TomlTable table, boolean ridge, boolean weighted) {
        double weight = weighted ? table.reqDouble("weight") : 1.0;
        return new NoiseLayerConfig(
            table.reqInt("octaves"),
            table.reqDouble("persistence"),
            table.reqDouble("lacunarity"),
            table.reqDouble("scale"),
            table.reqLong("seed_offset"),
            weight,
            ridge
        );
    }

    private static PoiConfig readPoiConfig(TomlTable table, boolean withArea) {
        int areaChunks = table.optInt("area_chunks", 0);
        int clearMarginTiles = table.optInt("clear_margin_tiles", 0);
        return new PoiConfig(
            table.reqInt("count"),
            table.reqInt("min_distance"),
            table.reqInt("margin"),
            table.reqInt("near_water_radius"),
            SimpleToml.enumSet(Biome.class, table.reqStringList("allowed_biomes")),
            areaChunks,
            clearMarginTiles
        );
    }
}

final class GeradorTerreno {
    private final GeneratorContext ctx;
    private final TerrainRules rules;

    GeradorTerreno(GeneratorContext ctx) {
        this.ctx = ctx;
        this.rules = ctx.terrainRules;
    }

    void generateBaseTerrain() {
        Arrays.fill(ctx.naturalMap, (byte) NaturalStructure.NONE.ordinal());
        ctx.geradorBiomas.buildMacroBiomeGrid();

        for (int y = 0; y < ctx.height; y++) {
            if (y % 500 == 0) {
                System.out.println("  linha " + y + " / " + ctx.height);
            }
            for (int x = 0; x < ctx.width; x++) {
                int idx = ctx.index(x, y);
                if (hardBorder(x, y)) {
                    ctx.biomeMap[idx] = (byte) Biome.OCEAN.ordinal();
                    ctx.tileMap[idx] = (byte) Tile.WATER_DEEP.ordinal();
                    continue;
                }

                double elevation = ctx.elevation(x, y) - edgeWaterPenalty(x, y);
                double moisture = ctx.moisture(x, y);

                if (elevation < rules.seaLevel - rules.deepWaterExtraDepth) {
                    ctx.biomeMap[idx] = (byte) Biome.OCEAN.ordinal();
                    ctx.tileMap[idx] = (byte) Tile.WATER_DEEP.ordinal();
                    continue;
                }
                if (elevation < rules.seaLevel + rules.shallowWaterBand) {
                    ctx.biomeMap[idx] = (byte) Biome.SHALLOW_WATER.ordinal();
                    ctx.tileMap[idx] = (byte) Tile.WATER_SHALLOW.ordinal();
                    continue;
                }
                if (isLakeCandidate(elevation, moisture, x, y)) {
                    ctx.biomeMap[idx] = (byte) Biome.SHALLOW_WATER.ordinal();
                    ctx.tileMap[idx] = (byte) Tile.WATER_SHALLOW.ordinal();
                    continue;
                }

                Biome biome = ctx.geradorBiomas.resolveLandBiome(x, y);
                ctx.biomeMap[idx] = (byte) biome.ordinal();
                ctx.tileMap[idx] = (byte) ctx.geradorBiomas.baseTileFor(biome).ordinal();
            }
        }
        finalizeWaters();
    }

    void generateRivers() {
        int created = 0;
        int attempts = 0;
        List<int[]> acceptedSources = new ArrayList<>();
        while (created < rules.riverSources && attempts < rules.riverSources * rules.riverMaxAttemptsPerSource) {
            attempts++;
            int x = ctx.boundedRandomInt(rules.riverSourceMargin, ctx.width - rules.riverSourceMargin, ctx.seed + 91L * attempts);
            int y = ctx.boundedRandomInt(rules.riverSourceMargin, ctx.height - rules.riverSourceMargin, ctx.seed + 131L * attempts);
            if (!ctx.isLandBiome(Biome.values()[ctx.biomeMap[ctx.index(x, y)] & 0xFF])) {
                continue;
            }
            double height = ctx.elevation(x, y) - edgeWaterPenalty(x, y);
            if (height < rules.riverSourceMinHeight) {
                continue;
            }
            if (ctx.nearWater(x, y, rules.riverSourceNearWaterRadius)) {
                continue;
            }
            if (nearRiverSource(acceptedSources, x, y, rules.riverSourceMinDistance)) {
                continue;
            }
            if (carveRiverFrom(x, y)) {
                acceptedSources.add(new int[]{x, y});
                created++;
            }
        }
        System.out.println("  fontes de rio criadas: " + created + " / " + rules.riverSources);
    }

    void finalizeWaters() {
        updateShallowWaterNearLand();
        blendRiverBanks();
        updateCoastsAndBeaches();
        ctx.recountBiomes();
    }

    private boolean carveRiverFrom(int startX, int startY) {
        int x = startX;
        int y = startY;
        int prevDx = 0;
        int prevDy = 1;
        int stagnation = 0;
        boolean touchedOcean = false;
        int riverSteps = 0;

        for (int step = 0; step < rules.riverMaxLength; step++) {
            int radius = riverRadiusForStep(step, x, y);
            carveRiverDisk(x, y, radius);

            if (ctx.nearOcean(x, y, rules.oceanDetectionRadius)) {
                carveRiverMouth(x, y, radius);
                touchedOcean = true;
                break;
            }

            int[] next = chooseNextRiverStep(x, y, prevDx, prevDy, step);
            int nextX = next[0];
            int nextY = next[1];
            int nextDx = next[2];
            int nextDy = next[3];

            if (nextX == x && nextY == y) {
                stagnation++;
                int[] escape = searchLowerPoint(x, y, rules.riverSearchRadius);
                if (escape == null) {
                    carveTerminalBasin(x, y, radius);
                    break;
                }
                nextX = escape[0];
                nextY = escape[1];
                nextDx = Integer.compare(nextX, x);
                nextDy = Integer.compare(nextY, y);
            } else {
                stagnation = 0;
            }

            carveRiverSegment(x, y, nextX, nextY, radius, step);
            prevDx = nextDx;
            prevDy = nextDy;
            x = nextX;
            y = nextY;
            riverSteps++;

            if (stagnation >= 2) {
                carveTerminalBasin(x, y, radius + 1);
                break;
            }
        }
        return touchedOcean || riverSteps > Math.max(12, rules.riverMaxLength / 14);
    }


    private boolean nearRiverSource(List<int[]> sources, int x, int y, int minDistance) {
        long rr = (long) minDistance * minDistance;
        for (int[] source : sources) {
            long dx = x - source[0];
            long dy = y - source[1];
            if (dx * dx + dy * dy <= rr) {
                return true;
            }
        }
        return false;
    }

    private int[] chooseNextRiverStep(int x, int y, int prevDx, int prevDy, int step) {
        double currentHeight = ctx.elevation(x, y) - edgeWaterPenalty(x, y);
        int bestX = x;
        int bestY = y;
        int bestDx = 0;
        int bestDy = 0;
        double bestScore = Double.NEGATIVE_INFINITY;

        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                if (dx == 0 && dy == 0) {
                    continue;
                }
                int nx = ctx.clamp(x + dx, 1, ctx.width - 2);
                int ny = ctx.clamp(y + dy, 1, ctx.height - 2);
                double neighborHeight = ctx.elevation(nx, ny) - edgeWaterPenalty(nx, ny);
                double downhill = currentHeight - neighborHeight;
                double flowAlignment = (dx * prevDx + dy * prevDy) / Math.sqrt((dx * dx + dy * dy) * Math.max(1.0, prevDx * prevDx + prevDy * prevDy));
                double meander = ctx.random01(ctx.tileSeed(nx, ny, 5000L + step * 13L)) - 0.5;
                double waterBias = ctx.nearWater(nx, ny, 1) ? -0.35 : 0.0;
                double score = downhill * rules.riverDownhillBias
                    + flowAlignment * rules.riverMomentum
                    + meander * rules.riverMeanderStrength
                    + waterBias;
                if (downhill < 0.0) {
                    score += downhill * rules.riverUphillPenalty;
                }
                if (score > bestScore) {
                    bestScore = score;
                    bestX = nx;
                    bestY = ny;
                    bestDx = dx;
                    bestDy = dy;
                }
            }
        }
        return new int[]{bestX, bestY, bestDx, bestDy};
    }

    private int[] searchLowerPoint(int x, int y, int radius) {
        double currentHeight = ctx.elevation(x, y) - edgeWaterPenalty(x, y);
        int bestX = -1;
        int bestY = -1;
        double bestDrop = 0.0;
        for (int dy = -radius; dy <= radius; dy++) {
            int ny = y + dy;
            if (ny <= 0 || ny >= ctx.height - 1) {
                continue;
            }
            for (int dx = -radius; dx <= radius; dx++) {
                int nx = x + dx;
                if (nx <= 0 || nx >= ctx.width - 1 || (dx == 0 && dy == 0)) {
                    continue;
                }
                if (dx * dx + dy * dy > radius * radius) {
                    continue;
                }
                double neighborHeight = ctx.elevation(nx, ny) - edgeWaterPenalty(nx, ny);
                double drop = currentHeight - neighborHeight;
                if (drop > bestDrop) {
                    bestDrop = drop;
                    bestX = nx;
                    bestY = ny;
                }
            }
        }
        return bestX < 0 ? null : new int[]{bestX, bestY};
    }

    private int riverRadiusForStep(int step, int x, int y) {
        int radius = Math.max(1, rules.riverWidth);
        radius = Math.max(radius, rules.riverMinWidth);
        radius += step / Math.max(1, rules.riverWidthGrowEvery);
        double lowlandFactor = 1.0 - ctx.clamp01((ctx.elevation(x, y) - rules.seaLevel) / Math.max(0.0001, 1.0 - rules.seaLevel));
        radius += (int) Math.round(lowlandFactor * 1.5);
        return Math.min(rules.riverMaxWidth, radius);
    }

    private void carveRiverSegment(int x0, int y0, int x1, int y1, int radius, int step) {
        int dx = x1 - x0;
        int dy = y1 - y0;
        int samples = Math.max(Math.abs(dx), Math.abs(dy)) + 1;
        for (int i = 0; i <= samples; i++) {
            double t = samples == 0 ? 1.0 : i / (double) samples;
            int x = (int) Math.round(x0 + dx * t);
            int y = (int) Math.round(y0 + dy * t);
            int localRadius = Math.min(rules.riverMaxWidth, radius + (step / Math.max(1, rules.riverWidthGrowEvery * 3)));
            carveRiverDisk(x, y, localRadius);
        }
    }

    private void carveRiverMouth(int x, int y, int radius) {
        for (int i = 0; i < Math.max(1, rules.riverMouthLength); i++) {
            carveRiverDisk(x, y, Math.min(rules.riverMaxWidth + rules.riverTerminalExtraWidth, radius + rules.riverTerminalExtraWidth + i));
        }
    }

    private void carveTerminalBasin(int x, int y, int radius) {
        for (int r = radius; r <= radius + rules.riverTerminalExtraWidth + 1; r++) {
            carveRiverDisk(x, y, r);
        }
    }

    private void carveRiverDisk(int cx, int cy, int radius) {
        for (int dy = -radius; dy <= radius; dy++) {
            int y = cy + dy;
            if (y <= 0 || y >= ctx.height - 1) {
                continue;
            }
            for (int dx = -radius; dx <= radius; dx++) {
                int x = cx + dx;
                if (x <= 0 || x >= ctx.width - 1) {
                    continue;
                }
                if (dx * dx + dy * dy > radius * radius) {
                    continue;
                }
                int idx = ctx.index(x, y);
                ctx.biomeMap[idx] = (byte) Biome.SHALLOW_WATER.ordinal();
                ctx.tileMap[idx] = (byte) Tile.WATER_SHALLOW.ordinal();
                ctx.naturalMap[idx] = (byte) NaturalStructure.NONE.ordinal();
            }
        }
    }

    private void blendRiverBanks() {
        if (rules.riverBankBlendRadius <= 0) {
            return;
        }
        for (int y = 1; y < ctx.height - 1; y++) {
            for (int x = 1; x < ctx.width - 1; x++) {
                int idx = ctx.index(x, y);
                if (!ctx.isLandBiome(Biome.values()[ctx.biomeMap[idx] & 0xFF])) {
                    continue;
                }
                if (!ctx.nearWater(x, y, rules.riverBankBlendRadius)) {
                    continue;
                }
                ctx.tileMap[idx] = (byte) ctx.geradorBiomas.coastTileFor(Biome.values()[ctx.biomeMap[idx] & 0xFF]).ordinal();
            }
        }
    }

    private boolean isLakeCandidate(double elevation, double moisture, int x, int y) {
        if (elevation >= rules.seaLevel + rules.lakeElevationOffsetFromSeaLevel) {
            return false;
        }
        if (moisture <= rules.lakeMinMoisture) {
            return false;
        }
        if (nearBorder(x, y, rules.lakeBorderBlockDistance)) {
            return false;
        }
        return ctx.sampleNoise(rules.lakeNoise, x, y) > rules.lakeNoiseThreshold;
    }

    private void updateCoastsAndBeaches() {
        for (int y = 1; y < ctx.height - 1; y++) {
            for (int x = 1; x < ctx.width - 1; x++) {
                int idx = ctx.index(x, y);
                Biome biome = Biome.values()[ctx.biomeMap[idx] & 0xFF];
                if (!ctx.isLandBiome(biome)) {
                    continue;
                }
                Tile tile = ctx.nearWater(x, y, rules.waterDetectionRadiusForBeach)
                    ? ctx.geradorBiomas.coastTileFor(biome)
                    : ctx.geradorBiomas.baseTileFor(biome);
                ctx.tileMap[idx] = (byte) tile.ordinal();
            }
        }
    }

    private void updateShallowWaterNearLand() {
        for (int y = 1; y < ctx.height - 1; y++) {
            for (int x = 1; x < ctx.width - 1; x++) {
                int idx = ctx.index(x, y);
                Tile tile = Tile.values()[ctx.tileMap[idx] & 0xFF];
                if (tile == Tile.WATER_DEEP && ctx.nearLand(x, y, rules.shallowWaterNearLandRadius)) {
                    ctx.tileMap[idx] = (byte) Tile.WATER_SHALLOW.ordinal();
                    ctx.biomeMap[idx] = (byte) Biome.SHALLOW_WATER.ordinal();
                }
            }
        }
    }


    private boolean nearBorder(int x, int y, int dist) {
        return x < dist || y < dist || x >= ctx.width - dist || y >= ctx.height - dist;
    }

    private boolean hardBorder(int x, int y) {
        return x < rules.hardOceanBorder
            || y < rules.hardOceanBorder
            || x >= ctx.width - rules.hardOceanBorder
            || y >= ctx.height - rules.hardOceanBorder;
    }

    private double edgeWaterPenalty(int x, int y) {
        int min = Math.min(Math.min(x, ctx.width - 1 - x), Math.min(y, ctx.height - 1 - y));
        if (min >= rules.softOceanBorder) {
            return 0.0;
        }
        double t = 1.0 - (double) min / rules.softOceanBorder;
        return t * t * rules.edgeWaterPenaltyStrength;
    }
}


final class SimpleToml {
    static TomlTable parse(Path path) throws IOException {
        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        Map<String, Object> root = new LinkedHashMap<>();
        Map<String, Object> current = root;

        for (String rawLine : lines) {
            String line = stripComment(rawLine).trim();
            if (line.isEmpty()) {
                continue;
            }
            if (line.startsWith("[") && line.endsWith("]")) {
                String section = line.substring(1, line.length() - 1).trim();
                current = getOrCreateTable(root, section);
                continue;
            }
            int eq = findEquals(line);
            if (eq < 0) {
                throw new IllegalArgumentException("Linha TOML invalida: " + rawLine);
            }
            String key = line.substring(0, eq).trim();
            String valueText = line.substring(eq + 1).trim();
            current.put(key, parseValue(valueText));
        }

        return new TomlTable(root, path.toString());
    }

    private static int findEquals(String line) {
        boolean inString = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"' && (i == 0 || line.charAt(i - 1) != '\\')) {
                inString = !inString;
            } else if (c == '=' && !inString) {
                return i;
            }
        }
        return -1;
    }

    private static String stripComment(String raw) {
        boolean inString = false;
        StringBuilder out = new StringBuilder(raw.length());
        for (int i = 0; i < raw.length(); i++) {
            char c = raw.charAt(i);
            if (c == '"' && (i == 0 || raw.charAt(i - 1) != '\\')) {
                inString = !inString;
            }
            if (c == '#' && !inString) {
                break;
            }
            out.append(c);
        }
        return out.toString();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> getOrCreateTable(Map<String, Object> root, String section) {
        String[] parts = section.split("\\.");
        Map<String, Object> current = root;
        for (String part : parts) {
            Object value = current.get(part);
            if (!(value instanceof Map<?, ?>)) {
                Map<String, Object> child = new LinkedHashMap<>();
                current.put(part, child);
                current = child;
            } else {
                current = (Map<String, Object>) value;
            }
        }
        return current;
    }

    private static Object parseValue(String text) {
        if (text.startsWith("\"") && text.endsWith("\"")) {
            return unescape(text.substring(1, text.length() - 1));
        }
        if (text.startsWith("[") && text.endsWith("]")) {
            return parseArray(text.substring(1, text.length() - 1));
        }
        if ("true".equalsIgnoreCase(text) || "false".equalsIgnoreCase(text)) {
            return Boolean.parseBoolean(text);
        }
        try {
            if (text.contains(".") || text.contains("e") || text.contains("E")) {
                return Double.parseDouble(text);
            }
            return Long.parseLong(text);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Valor TOML invalido: " + text, e);
        }
    }

    private static List<Object> parseArray(String text) {
        List<Object> items = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean inString = false;
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c == '"' && (i == 0 || text.charAt(i - 1) != '\\')) {
                inString = !inString;
                current.append(c);
                continue;
            }
            if (c == ',' && !inString) {
                String item = current.toString().trim();
                if (!item.isEmpty()) {
                    items.add(parseValue(item));
                }
                current.setLength(0);
                continue;
            }
            current.append(c);
        }
        String item = current.toString().trim();
        if (!item.isEmpty()) {
            items.add(parseValue(item));
        }
        return items;
    }

    private static String unescape(String text) {
        return text
            .replace("\\\"", "\"")
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\\t", "\t")
            .replace("\\\\", "\\");
    }

    static <E extends Enum<E>> E enumValue(Class<E> type, String value) {
        try {
            return Enum.valueOf(type, value.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Valor invalido para enum " + type.getSimpleName() + ": " + value, e);
        }
    }

    static <E extends Enum<E>> EnumSet<E> enumSet(Class<E> type, List<String> values) {
        EnumSet<E> out = EnumSet.noneOf(type);
        for (String value : values) {
            out.add(enumValue(type, value));
        }
        return out;
    }
}

final class TomlTable {
    private final Map<String, Object> map;
    private final String path;

    TomlTable(Map<String, Object> map, String path) {
        this.map = map;
        this.path = path;
    }

    TomlTable table(String key) {
        Object value = map.get(key);
        if (!(value instanceof Map<?, ?> child)) {
            throw new IllegalArgumentException("Tabela TOML obrigatoria ausente: " + path + "." + key);
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> casted = (Map<String, Object>) child;
        return new TomlTable(casted, path + "." + key);
    }

    int reqInt(String key) {
        Object value = require(key);
        if (value instanceof Number number) {
            return number.intValue();
        }
        throw invalid(key, "int");
    }

    int optInt(String key, int defaultValue) {
        Object value = map.get(key);
        if (value == null) {
            return defaultValue;
        }
        if (value instanceof Number number) {
            return number.intValue();
        }
        throw invalid(key, "int");
    }

    long reqLong(String key) {
        Object value = require(key);
        if (value instanceof Number number) {
            return number.longValue();
        }
        throw invalid(key, "long");
    }

    double reqDouble(String key) {
        Object value = require(key);
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        throw invalid(key, "double");
    }

    boolean reqBoolean(String key) {
        Object value = require(key);
        if (value instanceof Boolean bool) {
            return bool;
        }
        throw invalid(key, "boolean");
    }

    boolean optBoolean(String key, boolean defaultValue) {
        Object value = map.get(key);
        if (value == null) {
            return defaultValue;
        }
        if (value instanceof Boolean bool) {
            return bool;
        }
        throw invalid(key, "boolean");
    }

    String reqString(String key) {
        Object value = require(key);
        if (value instanceof String text) {
            return text;
        }
        throw invalid(key, "string");
    }

    List<String> reqStringList(String key) {
        Object value = require(key);
        if (!(value instanceof List<?> list)) {
            throw invalid(key, "array");
        }
        List<String> out = new ArrayList<>(list.size());
        for (Object item : list) {
            if (!(item instanceof String text)) {
                throw invalid(key, "array<string>");
            }
            out.add(text);
        }
        return out;
    }

    private Object require(String key) {
        if (!map.containsKey(key)) {
            throw new IllegalArgumentException("Chave TOML obrigatoria ausente: " + path + "." + key);
        }
        return map.get(key);
    }

    private IllegalArgumentException invalid(String key, String expected) {
        return new IllegalArgumentException("Valor TOML invalido em " + path + "." + key + " (esperado " + expected + ")");
    }
}
