import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.EnumMap;

final class BiomeDefinition {
    final Biome biome;
    final Tile baseTile;
    final Tile coastTile;
    final double weight;
    final double minTemperature;
    final double maxTemperature;
    final double minMoisture;
    final double maxMoisture;
    final ClimateSource primarySource;
    final double minPrimaryNoise;
    final double maxPrimaryNoise;

    BiomeDefinition(
        Biome biome,
        Tile baseTile,
        Tile coastTile,
        double weight,
        double minTemperature,
        double maxTemperature,
        double minMoisture,
        double maxMoisture,
        ClimateSource primarySource,
        double minPrimaryNoise,
        double maxPrimaryNoise
    ) {
        this.biome = biome;
        this.baseTile = baseTile;
        this.coastTile = coastTile;
        this.weight = weight;
        this.minTemperature = minTemperature;
        this.maxTemperature = maxTemperature;
        this.minMoisture = minMoisture;
        this.maxMoisture = maxMoisture;
        this.primarySource = primarySource;
        this.minPrimaryNoise = minPrimaryNoise;
        this.maxPrimaryNoise = maxPrimaryNoise;
    }

    boolean matches(double temperature, double moisture, double primary) {
        return temperature >= minTemperature && temperature <= maxTemperature
            && moisture >= minMoisture && moisture <= maxMoisture
            && primary >= minPrimaryNoise && primary <= maxPrimaryNoise;
    }

    double score(double temperature, double moisture, double primary) {
        double tempCenter = (minTemperature + maxTemperature) * 0.5;
        double moistCenter = (minMoisture + maxMoisture) * 0.5;
        double primaryCenter = (minPrimaryNoise + maxPrimaryNoise) * 0.5;
        double tempFit = 1.0 - Math.abs(temperature - tempCenter);
        double moistFit = 1.0 - Math.abs(moisture - moistCenter);
        double primaryFit = primarySource == ClimateSource.NONE ? 0.5 : 1.0 - Math.abs(primary - primaryCenter);
        return weight + tempFit * 0.20 + moistFit * 0.20 + primaryFit * 0.15;
    }
}

final class BiomeRules {
    final int macroGridWidth;
    final int macroGridHeight;
    final int macroMajorityRadius;
    final int macroSmoothingPasses;
    final int macroMinRegionCells;
    final double macroLocalBlend;
    final double macroEdgeNoiseStrength;
    final double macroWarpScaleFactor;
    final double macroWarpStrength;
    final double macroEdgeNoiseScaleFactor;

    final NoiseLayerConfig macroTemperature;
    final double macroTemperatureNoiseWeight;
    final double macroTemperatureLatitudeWeight;
    final NoiseLayerConfig macroMoisture;
    final NoiseLayerConfig macroMagic;
    final NoiseLayerConfig macroVolcanic;
    final NoiseLayerConfig macroSwamp;

    final int objectBlockNearPoiRadius;
    final boolean objectAvoidBeachTiles;
    final double objectAquamarineDeepWaterRate;

    final EnumMap<Biome, BiomeDefinition> biomeDefinitions;
    final EnumMap<Biome, EnumMap<NaturalStructure, Double>> objectRates;

    BiomeRules(
        int macroGridWidth,
        int macroGridHeight,
        int macroMajorityRadius,
        int macroSmoothingPasses,
        int macroMinRegionCells,
        double macroLocalBlend,
        double macroEdgeNoiseStrength,
        double macroWarpScaleFactor,
        double macroWarpStrength,
        double macroEdgeNoiseScaleFactor,
        NoiseLayerConfig macroTemperature,
        double macroTemperatureNoiseWeight,
        double macroTemperatureLatitudeWeight,
        NoiseLayerConfig macroMoisture,
        NoiseLayerConfig macroMagic,
        NoiseLayerConfig macroVolcanic,
        NoiseLayerConfig macroSwamp,
        int objectBlockNearPoiRadius,
        boolean objectAvoidBeachTiles,
        double objectAquamarineDeepWaterRate,
        EnumMap<Biome, BiomeDefinition> biomeDefinitions,
        EnumMap<Biome, EnumMap<NaturalStructure, Double>> objectRates
    ) {
        this.macroGridWidth = macroGridWidth;
        this.macroGridHeight = macroGridHeight;
        this.macroMajorityRadius = macroMajorityRadius;
        this.macroSmoothingPasses = macroSmoothingPasses;
        this.macroMinRegionCells = macroMinRegionCells;
        this.macroLocalBlend = macroLocalBlend;
        this.macroEdgeNoiseStrength = macroEdgeNoiseStrength;
        this.macroWarpScaleFactor = macroWarpScaleFactor;
        this.macroWarpStrength = macroWarpStrength;
        this.macroEdgeNoiseScaleFactor = macroEdgeNoiseScaleFactor;
        this.macroTemperature = macroTemperature;
        this.macroTemperatureNoiseWeight = macroTemperatureNoiseWeight;
        this.macroTemperatureLatitudeWeight = macroTemperatureLatitudeWeight;
        this.macroMoisture = macroMoisture;
        this.macroMagic = macroMagic;
        this.macroVolcanic = macroVolcanic;
        this.macroSwamp = macroSwamp;
        this.objectBlockNearPoiRadius = objectBlockNearPoiRadius;
        this.objectAvoidBeachTiles = objectAvoidBeachTiles;
        this.objectAquamarineDeepWaterRate = objectAquamarineDeepWaterRate;
        this.biomeDefinitions = biomeDefinitions;
        this.objectRates = objectRates;
    }

    static BiomeRules load(Path path) throws IOException {
        if (!Files.exists(path)) {
            throw new IOException("Arquivo de regras de biomas nao encontrado: " + path);
        }
        TomlTable root = SimpleToml.parse(path);
        TomlTable macro = root.table("macro");
        TomlTable climate = root.table("climate");
        TomlTable objects = root.table("objects");
        TomlTable biomes = root.table("biomes");

        NoiseLayerConfig macroTemperature = readClimateLayer(climate.table("temperature"));
        NoiseLayerConfig macroMoisture = readClimateLayer(climate.table("moisture"));
        NoiseLayerConfig macroMagic = readClimateLayer(climate.table("magic"));
        NoiseLayerConfig macroVolcanic = readClimateLayer(climate.table("volcanic"));
        NoiseLayerConfig macroSwamp = readClimateLayer(climate.table("swamp"));

        EnumMap<Biome, BiomeDefinition> definitions = new EnumMap<>(Biome.class);
        EnumMap<Biome, EnumMap<NaturalStructure, Double>> objectRates = new EnumMap<>(Biome.class);

        for (Biome biome : Biome.values()) {
            if (biome == Biome.OCEAN || biome == Biome.SHALLOW_WATER) {
                continue;
            }
            TomlTable biomeTable = biomes.table(biome.name());
            BiomeDefinition definition = new BiomeDefinition(
                biome,
                SimpleToml.enumValue(Tile.class, biomeTable.reqString("base_tile")),
                SimpleToml.enumValue(Tile.class, biomeTable.reqString("coast_tile")),
                biomeTable.reqDouble("weight"),
                biomeTable.reqDouble("temperature_min"),
                biomeTable.reqDouble("temperature_max"),
                biomeTable.reqDouble("moisture_min"),
                biomeTable.reqDouble("moisture_max"),
                SimpleToml.enumValue(ClimateSource.class, biomeTable.reqString("primary_source")),
                biomeTable.reqDouble("primary_min"),
                biomeTable.reqDouble("primary_max")
            );
            definitions.put(biome, definition);

            TomlTable objectsTable = biomeTable.table("objects");
            EnumMap<NaturalStructure, Double> rates = new EnumMap<>(NaturalStructure.class);
            for (NaturalStructure structure : NaturalStructure.values()) {
                if (structure == NaturalStructure.NONE) {
                    continue;
                }
                rates.put(structure, objectsTable.optDouble(structure.name(), 0.0));
            }
            objectRates.put(biome, rates);
        }

        return new BiomeRules(
            macro.reqInt("grid_width"),
            macro.reqInt("grid_height"),
            macro.reqInt("majority_radius"),
            macro.reqInt("smoothing_passes"),
            macro.reqInt("min_region_cells"),
            macro.reqDouble("local_blend"),
            macro.reqDouble("edge_noise_strength"),
            macro.reqDouble("warp_scale_factor"),
            macro.reqDouble("warp_strength"),
            macro.reqDouble("edge_noise_scale_factor"),
            macroTemperature,
            climate.table("temperature").reqDouble("noise_weight"),
            climate.table("temperature").reqDouble("latitude_weight"),
            macroMoisture,
            macroMagic,
            macroVolcanic,
            macroSwamp,
            objects.reqInt("block_near_poi_radius"),
            objects.reqBoolean("avoid_beach_tiles"),
            objects.optDouble("aquamarine_deep_water_rate", 0.00012),
            definitions,
            objectRates
        );
    }

    private static NoiseLayerConfig readClimateLayer(TomlTable table) {
        return new NoiseLayerConfig(
            table.reqInt("octaves"),
            table.reqDouble("persistence"),
            table.reqDouble("lacunarity"),
            table.reqDouble("scale"),
            table.reqLong("seed_offset"),
            1.0,
            table.optBoolean("ridge", false)
        );
    }
}

final class GeradorBiomas {
    private final GeneratorContext ctx;
    private final BiomeRules rules;
    private final int width;
    private final int height;
    private final int macroGridWidth;
    private final int macroGridHeight;
    private final int macroCellWidth;
    private final int macroCellHeight;
    private final byte[] macroBiomeGrid;

    GeradorBiomas(GeneratorContext ctx) {
        this.ctx = ctx;
        this.rules = ctx.biomeRules;
        this.width = ctx.width;
        this.height = ctx.height;
        this.macroGridWidth = ctx.macroGridWidth;
        this.macroGridHeight = ctx.macroGridHeight;
        this.macroCellWidth = ctx.macroCellWidth;
        this.macroCellHeight = ctx.macroCellHeight;
        this.macroBiomeGrid = ctx.macroBiomeGrid;
    }

    void buildMacroBiomeGrid() {
        for (int my = 0; my < macroGridHeight; my++) {
            for (int mx = 0; mx < macroGridWidth; mx++) {
                int sampleX = ctx.clamp(mx * macroCellWidth + macroCellWidth / 2, 0, width - 1);
                int sampleY = ctx.clamp(my * macroCellHeight + macroCellHeight / 2, 0, height - 1);
                macroBiomeGrid[ctx.macroIndex(mx, my)] = (byte) classifyMacroBiome(sampleX, sampleY).ordinal();
            }
        }
        for (int i = 0; i < rules.macroSmoothingPasses; i++) {
            smoothMacroBiomeGrid(rules.macroMajorityRadius);
        }
        removeSmallMacroRegions(rules.macroMinRegionCells);
        smoothMacroBiomeGrid(rules.macroMajorityRadius);
    }

    Tile baseTileFor(Biome biome) {
        if (!ctx.isLandBiome(biome)) {
            return biome == Biome.OCEAN ? Tile.WATER_DEEP : Tile.WATER_SHALLOW;
        }
        BiomeDefinition definition = rules.biomeDefinitions.get(biome);
        if (definition == null) {
            throw new IllegalStateException("Bioma sem definicao: " + biome);
        }
        return definition.baseTile;
    }

    Tile coastTileFor(Biome biome) {
        if (!ctx.isLandBiome(biome)) {
            return biome == Biome.OCEAN ? Tile.WATER_DEEP : Tile.WATER_SHALLOW;
        }
        BiomeDefinition definition = rules.biomeDefinitions.get(biome);
        if (definition == null) {
            throw new IllegalStateException("Bioma sem definicao: " + biome);
        }
        return definition.coastTile;
    }

    Biome classifyMacroBiome(int x, int y) {
        double temperature = climateTemperatureAt(x, y);
        double moisture = ctx.sampleNoise(rules.macroMoisture, x, y);
        double magic = ctx.sampleNoise(rules.macroMagic, x, y);
        double volcanic = ctx.sampleNoise(rules.macroVolcanic, x, y);
        double swamp = ctx.sampleNoise(rules.macroSwamp, x, y);

        Biome best = Biome.FIELD;
        double bestScore = Double.NEGATIVE_INFINITY;
        for (Biome biome : rules.biomeDefinitions.keySet()) {
            BiomeDefinition definition = rules.biomeDefinitions.get(biome);
            double primary = selectPrimary(definition.primarySource, temperature, moisture, magic, volcanic, swamp);
            if (!definition.matches(temperature, moisture, primary)) {
                continue;
            }
            double score = definition.score(temperature, moisture, primary)
                + biomeRegionalBonus(biome, x, y, temperature, moisture, magic, volcanic, swamp);
            if (score > bestScore) {
                bestScore = score;
                best = biome;
            }
        }
        return best;
    }

    private double climateTemperatureAt(int x, int y) {
        double northSouthPolar = Math.abs((y / (double) (height - 1)) * 2.0 - 1.0);
        return ctx.clamp01(
            ctx.sampleNoise(rules.macroTemperature, x, y) * rules.macroTemperatureNoiseWeight
                + northSouthPolar * rules.macroTemperatureLatitudeWeight
        );
    }

    private double biomeRegionalBonus(Biome biome, int x, int y, double temperature, double moisture, double magic, double volcanic, double swamp) {
        double polar = polarBandFactor(y);
        double central = centralBandFactor(y);
        double mildTemperature = 1.0 - Math.abs(temperature - 0.54);
        double mildMoisture = 1.0 - Math.abs(moisture - 0.48);
        return switch (biome) {
            case DESERT -> central * 0.52 + Math.max(0.0, temperature - 0.62) * 0.28 - moisture * 0.10;
            case SNOW -> polar * 0.92 + Math.max(0.0, 0.34 - temperature) * 0.22;
            case MAGIC -> Math.max(0.0, magic - 0.78) * 0.42;
            case VOLCANIC -> Math.max(0.0, volcanic - 0.68) * 0.85 + Math.max(0.0, temperature - 0.66) * 0.16;
            case SWAMP -> Math.max(0.0, swamp - 0.72) * 0.56 + Math.max(0.0, moisture - 0.78) * 0.20;
            case FOREST -> Math.max(0.0, moisture - 0.58) * 0.07;
            case FIELD -> Math.max(0.0, mildTemperature - 0.70) * 0.10
                + Math.max(0.0, mildMoisture - 0.66) * 0.12
                + Math.max(0.0, 0.78 - magic) * 0.08
                + Math.max(0.0, 0.78 - swamp) * 0.06
                + Math.max(0.0, 0.74 - volcanic) * 0.04;
            default -> 0.0;
        };
    }

    private double polarBandFactor(int y) {
        double t = Math.abs((y / (double) (height - 1)) * 2.0 - 1.0);
        return ctx.clamp01((t - 0.30) / 0.70);
    }

    private double centralBandFactor(int y) {
        double t = Math.abs((y / (double) (height - 1)) * 2.0 - 1.0);
        return ctx.clamp01(1.0 - t / 0.72);
    }

    private double selectPrimary(ClimateSource source, double temperature, double moisture, double magic, double volcanic, double swamp) {
        return switch (source) {
            case NONE -> 0.5;
            case TEMPERATURE -> temperature;
            case MOISTURE -> moisture;
            case MAGIC -> magic;
            case VOLCANIC -> volcanic;
            case SWAMP -> swamp;
        };
    }

    void smoothMacroBiomeGrid(int radius) {
        byte[] smoothed = Arrays.copyOf(macroBiomeGrid, macroBiomeGrid.length);
        int[] counts = new int[Biome.values().length];
        for (int my = 0; my < macroGridHeight; my++) {
            for (int mx = 0; mx < macroGridWidth; mx++) {
                Arrays.fill(counts, 0);
                for (int dy = -radius; dy <= radius; dy++) {
                    int ny = my + dy;
                    if (ny < 0 || ny >= macroGridHeight) {
                        continue;
                    }
                    for (int dx = -radius; dx <= radius; dx++) {
                        int nx = mx + dx;
                        if (nx < 0 || nx >= macroGridWidth) {
                            continue;
                        }
                        Biome neighbor = Biome.values()[macroBiomeGrid[ctx.macroIndex(nx, ny)] & 0xFF];
                        if (ctx.isLandBiome(neighbor)) {
                            counts[neighbor.ordinal()]++;
                        }
                    }
                }

                Biome current = Biome.values()[macroBiomeGrid[ctx.macroIndex(mx, my)] & 0xFF];
                int bestCount = counts[current.ordinal()];
                Biome best = current;
                for (Biome biome : rules.biomeDefinitions.keySet()) {
                    if (counts[biome.ordinal()] > bestCount) {
                        best = biome;
                        bestCount = counts[biome.ordinal()];
                    }
                }
                smoothed[ctx.macroIndex(mx, my)] = (byte) best.ordinal();
            }
        }
        System.arraycopy(smoothed, 0, macroBiomeGrid, 0, macroBiomeGrid.length);
    }

    void removeSmallMacroRegions(int minCells) {
        boolean[] visited = new boolean[macroBiomeGrid.length];
        ArrayDeque<Integer> queue = new ArrayDeque<>();
        int[] region = new int[macroBiomeGrid.length];

        for (int my = 0; my < macroGridHeight; my++) {
            for (int mx = 0; mx < macroGridWidth; mx++) {
                int start = ctx.macroIndex(mx, my);
                if (visited[start]) {
                    continue;
                }

                Biome biome = Biome.values()[macroBiomeGrid[start] & 0xFF];
                visited[start] = true;
                if (!ctx.isLandBiome(biome)) {
                    continue;
                }

                queue.clear();
                queue.add(start);
                int regionSize = 0;

                while (!queue.isEmpty()) {
                    int cell = queue.removeFirst();
                    region[regionSize++] = cell;
                    int cx = cell % macroGridWidth;
                    int cy = cell / macroGridWidth;

                    if (cx > 0) visitNeighbor(cx - 1, cy, biome, visited, queue);
                    if (cx < macroGridWidth - 1) visitNeighbor(cx + 1, cy, biome, visited, queue);
                    if (cy > 0) visitNeighbor(cx, cy - 1, biome, visited, queue);
                    if (cy < macroGridHeight - 1) visitNeighbor(cx, cy + 1, biome, visited, queue);
                }

                if (regionSize >= minCellsForBiome(biome, minCells)) {
                    continue;
                }

                Biome replacement = dominantNeighborMacroBiome(region, regionSize, biome);
                for (int i = 0; i < regionSize; i++) {
                    macroBiomeGrid[region[i]] = (byte) replacement.ordinal();
                }
            }
        }
    }


    private int minCellsForBiome(Biome biome, int defaultMinCells) {
        return switch (biome) {
            case MAGIC, VOLCANIC, SWAMP, SNOW -> Math.max(2, defaultMinCells / 2);
            case DESERT -> Math.max(3, defaultMinCells - 1);
            default -> defaultMinCells;
        };
    }

    private void visitNeighbor(int mx, int my, Biome biome, boolean[] visited, ArrayDeque<Integer> queue) {
        int idx = ctx.macroIndex(mx, my);
        if (visited[idx]) {
            return;
        }
        if ((macroBiomeGrid[idx] & 0xFF) != biome.ordinal()) {
            return;
        }
        visited[idx] = true;
        queue.add(idx);
    }

    Biome dominantNeighborMacroBiome(int[] regionCells, int regionSize, Biome currentBiome) {
        int[] counts = new int[Biome.values().length];
        for (int i = 0; i < regionSize; i++) {
            int cell = regionCells[i];
            int cx = cell % macroGridWidth;
            int cy = cell / macroGridWidth;
            for (int dy = -1; dy <= 1; dy++) {
                int ny = cy + dy;
                if (ny < 0 || ny >= macroGridHeight) {
                    continue;
                }
                for (int dx = -1; dx <= 1; dx++) {
                    int nx = cx + dx;
                    if (nx < 0 || nx >= macroGridWidth || (dx == 0 && dy == 0)) {
                        continue;
                    }
                    Biome neighbor = Biome.values()[macroBiomeGrid[ctx.macroIndex(nx, ny)] & 0xFF];
                    if (ctx.isLandBiome(neighbor) && neighbor != currentBiome) {
                        counts[neighbor.ordinal()]++;
                    }
                }
            }
        }

        Biome best = Biome.FIELD;
        int bestCount = 0;
        for (Biome biome : rules.biomeDefinitions.keySet()) {
            if (counts[biome.ordinal()] > bestCount) {
                bestCount = counts[biome.ordinal()];
                best = biome;
            }
        }
        return best;
    }

    Biome resolveLandBiome(int x, int y) {
        double warpScale = macroCellWidth * rules.macroWarpScaleFactor;
        double warpX = ctx.sampleNoise(new NoiseLayerConfig(3, 0.55, 2.0, warpScale, 777L, 1.0, false), x, y);
        double warpY = ctx.sampleNoise(new NoiseLayerConfig(3, 0.55, 2.0, warpScale, 888L, 1.0, false), x + 2000, y + 2000);

        double warpedX = x + (warpX - 0.5) * macroCellWidth * rules.macroWarpStrength;
        double warpedY = y + (warpY - 0.5) * macroCellHeight * rules.macroWarpStrength;

        double gx = (warpedX + 0.5) / macroCellWidth - 0.5;
        double gy = (warpedY + 0.5) / macroCellHeight - 0.5;

        int mx0 = ctx.clamp(ctx.fastFloor(gx), 0, macroGridWidth - 1);
        int my0 = ctx.clamp(ctx.fastFloor(gy), 0, macroGridHeight - 1);
        int mx1 = ctx.clamp(mx0 + 1, 0, macroGridWidth - 1);
        int my1 = ctx.clamp(my0 + 1, 0, macroGridHeight - 1);

        double tx = ctx.smoothstep(ctx.clamp01(gx - mx0));
        double ty = ctx.smoothstep(ctx.clamp01(gy - my0));

        double[] scores = new double[Biome.values().length];
        addMacroScore(scores, mx0, my0, (1.0 - tx) * (1.0 - ty));
        addMacroScore(scores, mx1, my0, tx * (1.0 - ty));
        addMacroScore(scores, mx0, my1, (1.0 - tx) * ty);
        addMacroScore(scores, mx1, my1, tx * ty);

        int currentMx = ctx.clamp(ctx.fastFloor(warpedX / macroCellWidth), 0, macroGridWidth - 1);
        int currentMy = ctx.clamp(ctx.fastFloor(warpedY / macroCellHeight), 0, macroGridHeight - 1);
        Biome current = Biome.values()[macroBiomeGrid[ctx.macroIndex(currentMx, currentMy)] & 0xFF];
        if (ctx.isLandBiome(current)) {
            scores[current.ordinal()] += rules.macroLocalBlend;
        }

        double edgeNoise = (ctx.sampleNoise(new NoiseLayerConfig(2, 0.55, 2.0, macroCellWidth * rules.macroEdgeNoiseScaleFactor, 913L, 1.0, false), x, y) - 0.5)
            * rules.macroEdgeNoiseStrength;
        applyEdgeJitter(scores, edgeNoise, x, y, mx0, my0);
        applyEdgeJitter(scores, edgeNoise, x, y, mx1, my0);
        applyEdgeJitter(scores, edgeNoise, x, y, mx0, my1);
        applyEdgeJitter(scores, edgeNoise, x, y, mx1, my1);

        Biome best = Biome.FIELD;
        double bestScore = Double.NEGATIVE_INFINITY;
        for (Biome biome : rules.biomeDefinitions.keySet()) {
            double score = scores[biome.ordinal()];
            if (score > bestScore) {
                bestScore = score;
                best = biome;
            }
        }
        return best;
    }

    private void addMacroScore(double[] scores, int mx, int my, double weight) {
        if (weight <= 0.0) {
            return;
        }
        Biome biome = Biome.values()[macroBiomeGrid[ctx.macroIndex(mx, my)] & 0xFF];
        if (ctx.isLandBiome(biome)) {
            scores[biome.ordinal()] += weight;
        }
    }

    private void applyEdgeJitter(double[] scores, double edgeNoise, int x, int y, int mx, int my) {
        Biome biome = Biome.values()[macroBiomeGrid[ctx.macroIndex(mx, my)] & 0xFF];
        if (!ctx.isLandBiome(biome) || edgeNoise == 0.0) {
            return;
        }
        long h = ctx.tileSeed(x + mx * 31, y + my * 17, 991L + biome.ordinal() * 131L);
        double tie = ctx.random01(h) - 0.5;
        scores[biome.ordinal()] += edgeNoise * tie;
    }
}
