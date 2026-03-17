import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;
import java.io.File;
import java.io.IOException;
import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class WorldGenerator {

    public static void main(String[] args) throws Exception {
        String rulesFilePath = args.length >= 3 ? args[2] : Rules.DEFAULT_RULES_FILE;
        Rules rules = Rules.loadOrCreate(rulesFilePath);
        if (args.length >= 1) {
            try {
                rules.seed = Long.parseLong(args[0]);
            } catch (NumberFormatException ignored) {
            }
        }
        if (args.length >= 2) {
            rules.outputDirectory = args[1];
        }

        Generator generator = new Generator(rules);
        generator.generate();
    }

    enum Biome {
        OCEAN,
        SHALLOW_WATER,
        FIELD,
        FOREST,
        DESERT,
        SNOW,
        MAGIC,
        VOLCANIC,
        SWAMP
    }

    enum Tile {
        WATER_DEEP,
        WATER_SHALLOW,
        FIELD_GRASS,
        FOREST_GRASS,
        BEACH_SAND,
        DESERT_SAND,
        SNOW,
        MAGIC_SOIL,
        VOLCANIC_ROCK,
        DEAD_SOIL
    }

    enum NaturalStructure {
        NONE,
        TREE,
        ROCK,
        BUSH,
        GOLD,
        AMETHYST,
        DIAMOND,
        RUBY,
        EMERALD,
        PALM,
        PINE,
        COPPER,
        LAVA_POOL
    }

    enum PoiType {
        GYM,
        DUNGEON,
        VILLAGE
    }

    static final class Poi {
        final int x;
        final int y;
        final PoiType type;

        Poi(int x, int y, PoiType type) {
            this.x = x;
            this.y = y;
            this.type = type;
        }
    }

    static final class StructureRule {
        final NaturalStructure structure;
        final double chancePerTile;
        final int minimum;
        final EnumSet<Biome> allowedBiomes;

        StructureRule(NaturalStructure structure, double chancePerTile, int minimum, EnumSet<Biome> allowedBiomes) {
            this.structure = structure;
            this.chancePerTile = chancePerTile;
            this.minimum = minimum;
            this.allowedBiomes = allowedBiomes;
        }

        boolean allows(Biome biome) {
            return allowedBiomes.contains(biome);
        }
    }

    static final class BiomeRule {
        final Biome biome;
        final double macroWeight;
        final double minimumLandPercent;
        final double minTemperature;
        final double maxTemperature;
        final double minMoisture;
        final double maxMoisture;
        final double minPrimaryNoise;
        final double maxPrimaryNoise;

        BiomeRule(
                Biome biome,
                double macroWeight,
                double minimumLandPercent,
                double minTemperature,
                double maxTemperature,
                double minMoisture,
                double maxMoisture,
                double minPrimaryNoise,
                double maxPrimaryNoise
        ) {
            this.biome = biome;
            this.macroWeight = macroWeight;
            this.minimumLandPercent = minimumLandPercent;
            this.minTemperature = minTemperature;
            this.maxTemperature = maxTemperature;
            this.minMoisture = minMoisture;
            this.maxMoisture = maxMoisture;
            this.minPrimaryNoise = minPrimaryNoise;
            this.maxPrimaryNoise = maxPrimaryNoise;
        }

        boolean matchesTemperature(double value) {
            return value >= minTemperature && value <= maxTemperature;
        }

        boolean matchesMoisture(double value) {
            return value >= minMoisture && value <= maxMoisture;
        }

        boolean matchesPrimaryNoise(double value) {
            return value >= minPrimaryNoise && value <= maxPrimaryNoise;
        }
    }

static final class Rules {
    static final String DEFAULT_RULES_FILE = "Regras/Geracao.json";

    int width = 10_000;
    int height = 10_000;
    long seed = 20260307L;
    String outputDirectory = "output_world";
    int diskChunkBlocos = 10;

    // ===== Ocean / water borders =====
    int hardOceanBorder = 120;
    int softOceanBorder = 500;
    double edgeWaterPenaltyStrength = 0.55;
    double seaLevel = 0.505;
    double deepWaterExtraDepth = 0.04;
    double shallowWaterBand = 0.020;
    int oceanDetectionRadius = 2;
    int waterDetectionRadiusForBeach = 2;
    int shallowWaterNearLandRadius = 1;

    // ===== Lakes =====
    double lakeElevationOffsetFromSeaLevel = 0.085;
    double lakeMinMoisture = 0.68;
    int lakeNoiseOctaves = 4;
    double lakeNoisePersistence = 0.55;
    double lakeNoiseLacunarity = 2.0;
    double lakeNoiseScale = 130.0;
    long lakeNoiseSeedOffset = 7777L;
    double lakeNoiseThreshold = 0.76;
    int lakeBorderBlockDistance = 420;

    // ===== Rivers =====
    int riverSources = 420;
    int riverMaxLength = 1100;
    int riverWidth = 2;
    int riverTerminalExtraWidth = 2;
    double riverSourceMinHeight = 0.66;
    int riverSourceMargin = 200;
    int riverSourceNearWaterRadius = 10;
    int riverMaxAttemptsPerSource = 50;

    // ===== POIs =====
    int gymCount = 30;
    int dungeonCount = 30;
    int villageCount = 10;
    int gymDistance = 230;
    int dungeonDistance = 220;
    int villageDistance = 300;

    // ===== Natural structures =====
    int naturalBlockNearPoiRadius = 3;
    int naturalBlockNearWaterRadius = 1;
    int naturalBoostPalmNearWaterRadius = 3;

    // ===== Macro-biomes and region size =====
    BiomeRule[] biomeRules;
    StructureRule[] structureRules;
    Map<Biome, Map<NaturalStructure, BiomeStructureOverride>> biomeStructureOverrides = new EnumMap<>(Biome.class);

    int macroGridWidth = 250;
    int macroGridHeight = 250;
    int macroMajorityRadius = 2;
    int macroSmoothingPasses = 3;
    int macroMinRegionCells = 8;
    double macroLocalBlend = 0.08;
    double macroEdgeNoiseStrength = 0.04;
    double macroWarpScaleFactor = 0.7;
    double macroWarpStrength = 1.2;
    double macroEdgeNoiseScaleFactor = 2.4;

    int macroTemperatureOctaves = 4;
    double macroTemperaturePersistence = 0.56;
    double macroTemperatureLacunarity = 2.0;
    double macroTemperatureScale = 3400.0;
    long macroTemperatureSeedOffset = 811L;
    double macroTemperatureNoiseWeight = 0.58;
    double macroTemperatureLatitudeWeight = 0.42;

    int macroMoistureOctaves = 4;
    double macroMoisturePersistence = 0.56;
    double macroMoistureLacunarity = 2.0;
    double macroMoistureScale = 3200.0;
    long macroMoistureSeedOffset = 821L;

    int macroMagicOctaves = 3;
    double macroMagicPersistence = 0.58;
    double macroMagicLacunarity = 2.0;
    double macroMagicScale = 3600.0;
    long macroMagicSeedOffset = 831L;

    int macroVolcanicOctaves = 3;
    double macroVolcanicPersistence = 0.58;
    double macroVolcanicLacunarity = 2.0;
    double macroVolcanicScale = 3000.0;
    long macroVolcanicSeedOffset = 841L;

    int macroSwampOctaves = 3;
    double macroSwampPersistence = 0.58;
    double macroSwampLacunarity = 2.0;
    double macroSwampScale = 2800.0;
    long macroSwampSeedOffset = 851L;

    String rulesFileUsed = DEFAULT_RULES_FILE;

    static final class BiomeStructureOverride {
        final Double chancePerTile;
        final Integer minimumAbsolute;
        final Double minimumRelative;
        final Double chanceMultiplier;
        final Integer requireNearWaterRadius;
        final Integer blockNearWaterRadius;
        final Integer blockNearPoiRadius;
        final Double minHeight;
        final Double maxHeight;
        final Double minMoisture;
        final Double maxMoisture;

        BiomeStructureOverride(Double chancePerTile,
                               Integer minimumAbsolute,
                               Double minimumRelative,
                               Double chanceMultiplier,
                               Integer requireNearWaterRadius,
                               Integer blockNearWaterRadius,
                               Integer blockNearPoiRadius,
                               Double minHeight,
                               Double maxHeight,
                               Double minMoisture,
                               Double maxMoisture) {
            this.chancePerTile = chancePerTile;
            this.minimumAbsolute = minimumAbsolute;
            this.minimumRelative = minimumRelative;
            this.chanceMultiplier = chanceMultiplier;
            this.requireNearWaterRadius = requireNearWaterRadius;
            this.blockNearWaterRadius = blockNearWaterRadius;
            this.blockNearPoiRadius = blockNearPoiRadius;
            this.minHeight = minHeight;
            this.maxHeight = maxHeight;
            this.minMoisture = minMoisture;
            this.maxMoisture = maxMoisture;
        }
    }

    static Rules defaultRules() {
        Rules rules = new Rules();
        rules.biomeRules = defaultBiomeRules();
        rules.structureRules = defaultStructureRules();
        rules.biomeStructureOverrides = rules.defaultBiomeStructureOverrides();
        rules.lakeBorderBlockDistance = rules.softOceanBorder;
        return rules;
    }

    static Rules loadOrCreate(String rulesFilePath) throws IOException {
        Rules defaults = defaultRules();
        File rulesFile = new File(rulesFilePath);
        if (!rulesFile.exists()) {
            File parent = rulesFile.getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) {
                throw new IOException("Nao foi possivel criar pasta de regras: " + parent.getAbsolutePath());
            }
            defaults.saveToJson(rulesFile);
            System.out.println("Arquivo de regras default criado: " + rulesFile.getAbsolutePath());
        }
        String json = Files.readString(rulesFile.toPath(), StandardCharsets.UTF_8);
        Rules loaded = defaults.copy();
        loaded.rulesFileUsed = rulesFilePath;
        Object parsed = SimpleJson.parse(json);
        if (parsed instanceof Map<?, ?> root) {
            loaded.readFromJsonMap(castStringObjectMap(root));
        } else {
            loaded.ensureBiomeStructureOverridesCompleto();
        }
        return loaded;
    }

    private Rules copy() {
        Rules r = new Rules();
        r.width = width;
        r.height = height;
        r.seed = seed;
        r.outputDirectory = outputDirectory;
        r.diskChunkBlocos = diskChunkBlocos;

        r.hardOceanBorder = hardOceanBorder;
        r.softOceanBorder = softOceanBorder;
        r.edgeWaterPenaltyStrength = edgeWaterPenaltyStrength;
        r.seaLevel = seaLevel;
        r.deepWaterExtraDepth = deepWaterExtraDepth;
        r.shallowWaterBand = shallowWaterBand;
        r.oceanDetectionRadius = oceanDetectionRadius;
        r.waterDetectionRadiusForBeach = waterDetectionRadiusForBeach;
        r.shallowWaterNearLandRadius = shallowWaterNearLandRadius;

        r.lakeElevationOffsetFromSeaLevel = lakeElevationOffsetFromSeaLevel;
        r.lakeMinMoisture = lakeMinMoisture;
        r.lakeNoiseOctaves = lakeNoiseOctaves;
        r.lakeNoisePersistence = lakeNoisePersistence;
        r.lakeNoiseLacunarity = lakeNoiseLacunarity;
        r.lakeNoiseScale = lakeNoiseScale;
        r.lakeNoiseSeedOffset = lakeNoiseSeedOffset;
        r.lakeNoiseThreshold = lakeNoiseThreshold;
        r.lakeBorderBlockDistance = lakeBorderBlockDistance;

        r.riverSources = riverSources;
        r.riverMaxLength = riverMaxLength;
        r.riverWidth = riverWidth;
        r.riverTerminalExtraWidth = riverTerminalExtraWidth;
        r.riverSourceMinHeight = riverSourceMinHeight;
        r.riverSourceMargin = riverSourceMargin;
        r.riverSourceNearWaterRadius = riverSourceNearWaterRadius;
        r.riverMaxAttemptsPerSource = riverMaxAttemptsPerSource;

        r.gymCount = gymCount;
        r.dungeonCount = dungeonCount;
        r.villageCount = villageCount;
        r.gymDistance = gymDistance;
        r.dungeonDistance = dungeonDistance;
        r.villageDistance = villageDistance;

        r.naturalBlockNearPoiRadius = naturalBlockNearPoiRadius;
        r.naturalBlockNearWaterRadius = naturalBlockNearWaterRadius;
        r.naturalBoostPalmNearWaterRadius = naturalBoostPalmNearWaterRadius;

        r.macroGridWidth = macroGridWidth;
        r.macroGridHeight = macroGridHeight;
        r.macroMajorityRadius = macroMajorityRadius;
        r.macroSmoothingPasses = macroSmoothingPasses;
        r.macroMinRegionCells = macroMinRegionCells;
        r.macroLocalBlend = macroLocalBlend;
        r.macroEdgeNoiseStrength = macroEdgeNoiseStrength;
        r.macroWarpScaleFactor = macroWarpScaleFactor;
        r.macroWarpStrength = macroWarpStrength;
        r.macroEdgeNoiseScaleFactor = macroEdgeNoiseScaleFactor;

        r.macroTemperatureOctaves = macroTemperatureOctaves;
        r.macroTemperaturePersistence = macroTemperaturePersistence;
        r.macroTemperatureLacunarity = macroTemperatureLacunarity;
        r.macroTemperatureScale = macroTemperatureScale;
        r.macroTemperatureSeedOffset = macroTemperatureSeedOffset;
        r.macroTemperatureNoiseWeight = macroTemperatureNoiseWeight;
        r.macroTemperatureLatitudeWeight = macroTemperatureLatitudeWeight;

        r.macroMoistureOctaves = macroMoistureOctaves;
        r.macroMoisturePersistence = macroMoisturePersistence;
        r.macroMoistureLacunarity = macroMoistureLacunarity;
        r.macroMoistureScale = macroMoistureScale;
        r.macroMoistureSeedOffset = macroMoistureSeedOffset;

        r.macroMagicOctaves = macroMagicOctaves;
        r.macroMagicPersistence = macroMagicPersistence;
        r.macroMagicLacunarity = macroMagicLacunarity;
        r.macroMagicScale = macroMagicScale;
        r.macroMagicSeedOffset = macroMagicSeedOffset;

        r.macroVolcanicOctaves = macroVolcanicOctaves;
        r.macroVolcanicPersistence = macroVolcanicPersistence;
        r.macroVolcanicLacunarity = macroVolcanicLacunarity;
        r.macroVolcanicScale = macroVolcanicScale;
        r.macroVolcanicSeedOffset = macroVolcanicSeedOffset;

        r.macroSwampOctaves = macroSwampOctaves;
        r.macroSwampPersistence = macroSwampPersistence;
        r.macroSwampLacunarity = macroSwampLacunarity;
        r.macroSwampScale = macroSwampScale;
        r.macroSwampSeedOffset = macroSwampSeedOffset;

        r.biomeRules = Arrays.copyOf(biomeRules, biomeRules.length);
        r.structureRules = Arrays.copyOf(structureRules, structureRules.length);
        for (Map.Entry<Biome, Map<NaturalStructure, BiomeStructureOverride>> e : biomeStructureOverrides.entrySet()) {
            r.biomeStructureOverrides.put(e.getKey(), new EnumMap<>(e.getValue()));
        }
        r.rulesFileUsed = rulesFileUsed;
        return r;
    }

    private void saveToJson(File file) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(file.toPath(), StandardCharsets.UTF_8)) {
            writer.write(toJsonString());
        }
    }

    private String toJsonString() {
        Map<String, Object> root = new LinkedHashMap<>();

        Map<String, Object> mapa = new LinkedHashMap<>();
        mapa.put("seed", seed);
        mapa.put("width", width);
        mapa.put("height", height);
        mapa.put("diskChunkBlocos", diskChunkBlocos);
        root.put("mapa", mapa);
        root.put("seed", seed);
        root.put("width", width);
        root.put("height", height);
        root.put("diskChunkBlocos", diskChunkBlocos);

        Map<String, Object> oceans = new LinkedHashMap<>();
        oceans.put("hardOceanBorder", hardOceanBorder);
        oceans.put("softOceanBorder", softOceanBorder);
        oceans.put("edgeWaterPenaltyStrength", edgeWaterPenaltyStrength);
        oceans.put("seaLevel", seaLevel);
        oceans.put("deepWaterExtraDepth", deepWaterExtraDepth);
        oceans.put("shallowWaterBand", shallowWaterBand);
        oceans.put("oceanDetectionRadius", oceanDetectionRadius);
        oceans.put("waterDetectionRadiusForBeach", waterDetectionRadiusForBeach);
        oceans.put("shallowWaterNearLandRadius", shallowWaterNearLandRadius);
        root.put("oceano", oceans);
        root.put("oceans", oceans);

        Map<String, Object> lakes = new LinkedHashMap<>();
        lakes.put("lakeElevationOffsetFromSeaLevel", lakeElevationOffsetFromSeaLevel);
        lakes.put("lakeMinMoisture", lakeMinMoisture);
        lakes.put("lakeNoiseOctaves", lakeNoiseOctaves);
        lakes.put("lakeNoisePersistence", lakeNoisePersistence);
        lakes.put("lakeNoiseLacunarity", lakeNoiseLacunarity);
        lakes.put("lakeNoiseScale", lakeNoiseScale);
        lakes.put("lakeNoiseSeedOffset", lakeNoiseSeedOffset);
        lakes.put("lakeNoiseThreshold", lakeNoiseThreshold);
        lakes.put("lakeBorderBlockDistance", lakeBorderBlockDistance);
        root.put("lagos", lakes);
        root.put("lakes", lakes);

        Map<String, Object> rivers = new LinkedHashMap<>();
        rivers.put("riverSources", riverSources);
        rivers.put("riverMaxLength", riverMaxLength);
        rivers.put("riverWidth", riverWidth);
        rivers.put("riverTerminalExtraWidth", riverTerminalExtraWidth);
        rivers.put("riverSourceMinHeight", riverSourceMinHeight);
        rivers.put("riverSourceMargin", riverSourceMargin);
        rivers.put("riverSourceNearWaterRadius", riverSourceNearWaterRadius);
        rivers.put("riverMaxAttemptsPerSource", riverMaxAttemptsPerSource);
        root.put("rios", rivers);
        root.put("rivers", rivers);

        Map<String, Object> pois = new LinkedHashMap<>();
        pois.put("gymCount", gymCount);
        pois.put("dungeonCount", dungeonCount);
        pois.put("villageCount", villageCount);
        pois.put("gymDistance", gymDistance);
        pois.put("dungeonDistance", dungeonDistance);
        pois.put("villageDistance", villageDistance);
        root.put("pois", pois);

        Map<String, Object> structures = new LinkedHashMap<>();
        structures.put("naturalBlockNearPoiRadius", naturalBlockNearPoiRadius);
        structures.put("naturalBlockNearWaterRadius", naturalBlockNearWaterRadius);
        structures.put("naturalBoostPalmNearWaterRadius", naturalBoostPalmNearWaterRadius);

        Map<String, Object> macroBiomes = new LinkedHashMap<>();
        macroBiomes.put("macroGridWidth", macroGridWidth);
        macroBiomes.put("macroGridHeight", macroGridHeight);
        macroBiomes.put("macroMajorityRadius", macroMajorityRadius);
        macroBiomes.put("macroSmoothingPasses", macroSmoothingPasses);
        macroBiomes.put("macroMinRegionCells", macroMinRegionCells);
        macroBiomes.put("macroLocalBlend", macroLocalBlend);
        macroBiomes.put("macroEdgeNoiseStrength", macroEdgeNoiseStrength);
        macroBiomes.put("macroWarpScaleFactor", macroWarpScaleFactor);
        macroBiomes.put("macroWarpStrength", macroWarpStrength);
        macroBiomes.put("macroEdgeNoiseScaleFactor", macroEdgeNoiseScaleFactor);
        macroBiomes.put("macroTemperatureOctaves", macroTemperatureOctaves);
        macroBiomes.put("macroTemperaturePersistence", macroTemperaturePersistence);
        macroBiomes.put("macroTemperatureLacunarity", macroTemperatureLacunarity);
        macroBiomes.put("macroTemperatureScale", macroTemperatureScale);
        macroBiomes.put("macroTemperatureSeedOffset", macroTemperatureSeedOffset);
        macroBiomes.put("macroTemperatureNoiseWeight", macroTemperatureNoiseWeight);
        macroBiomes.put("macroTemperatureLatitudeWeight", macroTemperatureLatitudeWeight);
        macroBiomes.put("macroMoistureOctaves", macroMoistureOctaves);
        macroBiomes.put("macroMoisturePersistence", macroMoisturePersistence);
        macroBiomes.put("macroMoistureLacunarity", macroMoistureLacunarity);
        macroBiomes.put("macroMoistureScale", macroMoistureScale);
        macroBiomes.put("macroMoistureSeedOffset", macroMoistureSeedOffset);
        macroBiomes.put("macroMagicOctaves", macroMagicOctaves);
        macroBiomes.put("macroMagicPersistence", macroMagicPersistence);
        macroBiomes.put("macroMagicLacunarity", macroMagicLacunarity);
        macroBiomes.put("macroMagicScale", macroMagicScale);
        macroBiomes.put("macroMagicSeedOffset", macroMagicSeedOffset);
        macroBiomes.put("macroVolcanicOctaves", macroVolcanicOctaves);
        macroBiomes.put("macroVolcanicPersistence", macroVolcanicPersistence);
        macroBiomes.put("macroVolcanicLacunarity", macroVolcanicLacunarity);
        macroBiomes.put("macroVolcanicScale", macroVolcanicScale);
        macroBiomes.put("macroVolcanicSeedOffset", macroVolcanicSeedOffset);
        macroBiomes.put("macroSwampOctaves", macroSwampOctaves);
        macroBiomes.put("macroSwampPersistence", macroSwampPersistence);
        macroBiomes.put("macroSwampLacunarity", macroSwampLacunarity);
        macroBiomes.put("macroSwampScale", macroSwampScale);
        macroBiomes.put("macroSwampSeedOffset", macroSwampSeedOffset);
        root.put("macroBiomas", macroBiomes);
        root.put("macroBiomes", macroBiomes);

        List<Object> biomeRulesList = new ArrayList<>();
        for (BiomeRule rule : biomeRules) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("biome", rule.biome.name());
            item.put("macroWeight", rule.macroWeight);
            item.put("minimumLandPercent", rule.minimumLandPercent);
            item.put("minTemperature", rule.minTemperature);
            item.put("maxTemperature", rule.maxTemperature);
            item.put("minMoisture", rule.minMoisture);
            item.put("maxMoisture", rule.maxMoisture);
            item.put("minPrimaryNoise", rule.minPrimaryNoise);
            item.put("maxPrimaryNoise", rule.maxPrimaryNoise);
            biomeRulesList.add(item);
        }
        root.put("biomeRules", biomeRulesList);

        List<Object> structureRulesList = new ArrayList<>();
        for (StructureRule rule : structureRules) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("structure", rule.structure.name());
            item.put("chancePerTile", rule.chancePerTile);
            item.put("minimum", rule.minimum);
            List<Object> allowed = new ArrayList<>();
            for (Biome biome : rule.allowedBiomes) {
                allowed.add(biome.name());
            }
            item.put("allowedBiomes", allowed);
            structureRulesList.add(item);
        }
        root.put("structureRules", structureRulesList);

        Map<String, Object> overrides = new LinkedHashMap<>();
        for (Map.Entry<Biome, Map<NaturalStructure, BiomeStructureOverride>> e : biomeStructureOverrides.entrySet()) {
            Map<String, Object> byBiome = new LinkedHashMap<>();
            for (Map.Entry<NaturalStructure, BiomeStructureOverride> se : e.getValue().entrySet()) {
                BiomeStructureOverride o = se.getValue();
                Map<String, Object> item = new LinkedHashMap<>();
                if (o.chancePerTile != null) { item.put("chancePerTile", o.chancePerTile); item.put("spawnRate", o.chancePerTile); }
                if (o.minimumAbsolute != null) { item.put("minimumAbsolute", o.minimumAbsolute); item.put("minimum", o.minimumAbsolute); }
                if (o.minimumRelative != null) item.put("minimumRelative", o.minimumRelative);
                if (o.chanceMultiplier != null) item.put("chanceMultiplier", o.chanceMultiplier);
                if (o.requireNearWaterRadius != null) item.put("requireNearWaterRadius", o.requireNearWaterRadius);
                if (o.blockNearWaterRadius != null) item.put("blockNearWaterRadius", o.blockNearWaterRadius);
                if (o.blockNearPoiRadius != null) item.put("blockNearPoiRadius", o.blockNearPoiRadius);
                if (o.minHeight != null) item.put("minHeight", o.minHeight);
                if (o.maxHeight != null) item.put("maxHeight", o.maxHeight);
                if (o.minMoisture != null) item.put("minMoisture", o.minMoisture);
                if (o.maxMoisture != null) item.put("maxMoisture", o.maxMoisture);
                byBiome.put(se.getKey().name(), item);
            }
            overrides.put(e.getKey().name(), byBiome);
        }
        root.put("biomeStructureOverrides", overrides);

        Map<String, Object> estruturasNaturais = new LinkedHashMap<>(structures);
        estruturasNaturais.put("regrasGlobais", structureRulesList);
        estruturasNaturais.put("porBioma", overrides);
        root.put("estruturasNaturais", estruturasNaturais);
        root.put("structures", structures);

        root.put("spawn", Collections.singletonMap("requirePureFieldChunk", true));
        root.put("exportacao", Collections.singletonMap("rulesFile", rulesFileUsed));
        root.put("export", Collections.singletonMap("rulesFile", rulesFileUsed));
        root.put("debug", Collections.singletonMap("enabled", false));
        return SimpleJson.stringify(root);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castStringObjectMap(Map<?, ?> map) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> e : map.entrySet()) {
            if (e.getKey() != null) {
                out.put(String.valueOf(e.getKey()), e.getValue());
            }
        }
        return out;
    }

    private void readFromJsonMap(Map<String, Object> root) {
        Map<String, Object> mapa = section(root, "mapa");
        width = getInt(mapa, "width", getInt(root, "width", width));
        height = getInt(mapa, "height", getInt(root, "height", height));
        seed = getLong(mapa, "seed", getLong(root, "seed", seed));
        diskChunkBlocos = 10;

        Map<String, Object> oceans = section(root, "oceano", "oceans");
        hardOceanBorder = getInt(oceans, "hardOceanBorder", hardOceanBorder);
        softOceanBorder = getInt(oceans, "softOceanBorder", softOceanBorder);
        edgeWaterPenaltyStrength = getDouble(oceans, "edgeWaterPenaltyStrength", edgeWaterPenaltyStrength);
        seaLevel = getDouble(oceans, "seaLevel", seaLevel);
        deepWaterExtraDepth = getDouble(oceans, "deepWaterExtraDepth", deepWaterExtraDepth);
        shallowWaterBand = getDouble(oceans, "shallowWaterBand", shallowWaterBand);
        oceanDetectionRadius = getInt(oceans, "oceanDetectionRadius", oceanDetectionRadius);
        waterDetectionRadiusForBeach = getInt(oceans, "waterDetectionRadiusForBeach", waterDetectionRadiusForBeach);
        shallowWaterNearLandRadius = getInt(oceans, "shallowWaterNearLandRadius", shallowWaterNearLandRadius);

        Map<String, Object> lakes = section(root, "lagos", "lakes");
        lakeElevationOffsetFromSeaLevel = getDouble(lakes, "lakeElevationOffsetFromSeaLevel", lakeElevationOffsetFromSeaLevel);
        lakeMinMoisture = getDouble(lakes, "lakeMinMoisture", lakeMinMoisture);
        lakeNoiseOctaves = getInt(lakes, "lakeNoiseOctaves", lakeNoiseOctaves);
        lakeNoisePersistence = getDouble(lakes, "lakeNoisePersistence", lakeNoisePersistence);
        lakeNoiseLacunarity = getDouble(lakes, "lakeNoiseLacunarity", lakeNoiseLacunarity);
        lakeNoiseScale = getDouble(lakes, "lakeNoiseScale", lakeNoiseScale);
        lakeNoiseSeedOffset = getLong(lakes, "lakeNoiseSeedOffset", lakeNoiseSeedOffset);
        lakeNoiseThreshold = getDouble(lakes, "lakeNoiseThreshold", lakeNoiseThreshold);
        lakeBorderBlockDistance = getInt(lakes, "lakeBorderBlockDistance", lakeBorderBlockDistance);

        Map<String, Object> rivers = section(root, "rios", "rivers");
        riverSources = getInt(rivers, "riverSources", riverSources);
        riverMaxLength = getInt(rivers, "riverMaxLength", riverMaxLength);
        riverWidth = getInt(rivers, "riverWidth", riverWidth);
        riverTerminalExtraWidth = getInt(rivers, "riverTerminalExtraWidth", riverTerminalExtraWidth);
        riverSourceMinHeight = getDouble(rivers, "riverSourceMinHeight", riverSourceMinHeight);
        riverSourceMargin = getInt(rivers, "riverSourceMargin", riverSourceMargin);
        riverSourceNearWaterRadius = getInt(rivers, "riverSourceNearWaterRadius", riverSourceNearWaterRadius);
        riverMaxAttemptsPerSource = getInt(rivers, "riverMaxAttemptsPerSource", riverMaxAttemptsPerSource);

        Map<String, Object> pois = section(root, "pois");
        gymCount = getInt(pois, "gymCount", gymCount);
        dungeonCount = getInt(pois, "dungeonCount", dungeonCount);
        villageCount = getInt(pois, "villageCount", villageCount);
        gymDistance = getInt(pois, "gymDistance", gymDistance);
        dungeonDistance = getInt(pois, "dungeonDistance", dungeonDistance);
        villageDistance = getInt(pois, "villageDistance", villageDistance);

        Map<String, Object> structures = section(root, "estruturasNaturais", "structures");
        naturalBlockNearPoiRadius = getInt(structures, "naturalBlockNearPoiRadius", naturalBlockNearPoiRadius);
        naturalBlockNearWaterRadius = getInt(structures, "naturalBlockNearWaterRadius", naturalBlockNearWaterRadius);
        naturalBoostPalmNearWaterRadius = getInt(structures, "naturalBoostPalmNearWaterRadius", naturalBoostPalmNearWaterRadius);

        Map<String, Object> macroBiomes = section(root, "macroBiomas", "macroBiomes");
        macroGridWidth = getInt(macroBiomes, "macroGridWidth", macroGridWidth);
        macroGridHeight = getInt(macroBiomes, "macroGridHeight", macroGridHeight);
        macroMajorityRadius = getInt(macroBiomes, "macroMajorityRadius", macroMajorityRadius);
        macroSmoothingPasses = getInt(macroBiomes, "macroSmoothingPasses", macroSmoothingPasses);
        macroMinRegionCells = getInt(macroBiomes, "macroMinRegionCells", macroMinRegionCells);
        macroLocalBlend = getDouble(macroBiomes, "macroLocalBlend", macroLocalBlend);
        macroEdgeNoiseStrength = getDouble(macroBiomes, "macroEdgeNoiseStrength", macroEdgeNoiseStrength);
        macroWarpScaleFactor = getDouble(macroBiomes, "macroWarpScaleFactor", macroWarpScaleFactor);
        macroWarpStrength = getDouble(macroBiomes, "macroWarpStrength", macroWarpStrength);
        macroEdgeNoiseScaleFactor = getDouble(macroBiomes, "macroEdgeNoiseScaleFactor", macroEdgeNoiseScaleFactor);

        macroTemperatureOctaves = getInt(macroBiomes, "macroTemperatureOctaves", macroTemperatureOctaves);
        macroTemperaturePersistence = getDouble(macroBiomes, "macroTemperaturePersistence", macroTemperaturePersistence);
        macroTemperatureLacunarity = getDouble(macroBiomes, "macroTemperatureLacunarity", macroTemperatureLacunarity);
        macroTemperatureScale = getDouble(macroBiomes, "macroTemperatureScale", macroTemperatureScale);
        macroTemperatureSeedOffset = getLong(macroBiomes, "macroTemperatureSeedOffset", macroTemperatureSeedOffset);
        macroTemperatureNoiseWeight = getDouble(macroBiomes, "macroTemperatureNoiseWeight", macroTemperatureNoiseWeight);
        macroTemperatureLatitudeWeight = getDouble(macroBiomes, "macroTemperatureLatitudeWeight", macroTemperatureLatitudeWeight);

        macroMoistureOctaves = getInt(macroBiomes, "macroMoistureOctaves", macroMoistureOctaves);
        macroMoisturePersistence = getDouble(macroBiomes, "macroMoisturePersistence", macroMoisturePersistence);
        macroMoistureLacunarity = getDouble(macroBiomes, "macroMoistureLacunarity", macroMoistureLacunarity);
        macroMoistureScale = getDouble(macroBiomes, "macroMoistureScale", macroMoistureScale);
        macroMoistureSeedOffset = getLong(macroBiomes, "macroMoistureSeedOffset", macroMoistureSeedOffset);

        macroMagicOctaves = getInt(macroBiomes, "macroMagicOctaves", macroMagicOctaves);
        macroMagicPersistence = getDouble(macroBiomes, "macroMagicPersistence", macroMagicPersistence);
        macroMagicLacunarity = getDouble(macroBiomes, "macroMagicLacunarity", macroMagicLacunarity);
        macroMagicScale = getDouble(macroBiomes, "macroMagicScale", macroMagicScale);
        macroMagicSeedOffset = getLong(macroBiomes, "macroMagicSeedOffset", macroMagicSeedOffset);

        macroVolcanicOctaves = getInt(macroBiomes, "macroVolcanicOctaves", macroVolcanicOctaves);
        macroVolcanicPersistence = getDouble(macroBiomes, "macroVolcanicPersistence", macroVolcanicPersistence);
        macroVolcanicLacunarity = getDouble(macroBiomes, "macroVolcanicLacunarity", macroVolcanicLacunarity);
        macroVolcanicScale = getDouble(macroBiomes, "macroVolcanicScale", macroVolcanicScale);
        macroVolcanicSeedOffset = getLong(macroBiomes, "macroVolcanicSeedOffset", macroVolcanicSeedOffset);

        macroSwampOctaves = getInt(macroBiomes, "macroSwampOctaves", macroSwampOctaves);
        macroSwampPersistence = getDouble(macroBiomes, "macroSwampPersistence", macroSwampPersistence);
        macroSwampLacunarity = getDouble(macroBiomes, "macroSwampLacunarity", macroSwampLacunarity);
        macroSwampScale = getDouble(macroBiomes, "macroSwampScale", macroSwampScale);
        macroSwampSeedOffset = getLong(macroBiomes, "macroSwampSeedOffset", macroSwampSeedOffset);

        parseBiomeRules(root.get("biomeRules"));
        Map<String, Object> estruturasNaturais = section(root, "estruturasNaturais");
        Object regrasEstruturas = firstPresent(root, "structureRules", "estruturasRegras");
        if (regrasEstruturas == null) {
            regrasEstruturas = estruturasNaturais.get("regrasGlobais");
        }
        parseStructureRules(regrasEstruturas);
        Object porBioma = firstPresent(root, "biomeStructureOverrides", "estruturasPorBioma");
        if (porBioma == null) {
            porBioma = estruturasNaturais.get("porBioma");
        }
        parseBiomeStructureOverrides(porBioma);
        ensureBiomeStructureOverridesCompleto();
    }

    private void parseBiomeRules(Object value) {
        if (!(value instanceof List<?> list) || list.isEmpty()) {
            return;
        }
        List<BiomeRule> out = new ArrayList<>();
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> raw)) continue;
            Map<String, Object> map = castStringObjectMap(raw);
            Biome biome = readEnum(Biome.class, map.get("biome"));
            if (biome == null) continue;
            out.add(new BiomeRule(
                    biome,
                    getDouble(map, "macroWeight", 1.0),
                    getDouble(map, "minimumLandPercent", 0.0),
                    getDouble(map, "minTemperature", 0.0),
                    getDouble(map, "maxTemperature", 1.0),
                    getDouble(map, "minMoisture", 0.0),
                    getDouble(map, "maxMoisture", 1.0),
                    getDouble(map, "minPrimaryNoise", 0.0),
                    getDouble(map, "maxPrimaryNoise", 1.0)
            ));
        }
        if (!out.isEmpty()) {
            biomeRules = out.toArray(new BiomeRule[0]);
        }
    }

    private void parseStructureRules(Object value) {
        if (!(value instanceof List<?> list) || list.isEmpty()) {
            return;
        }
        List<StructureRule> out = new ArrayList<>();
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> raw)) continue;
            Map<String, Object> map = castStringObjectMap(raw);
            NaturalStructure structure = readEnum(NaturalStructure.class, map.get("structure"));
            if (structure == null || structure == NaturalStructure.NONE) continue;
            EnumSet<Biome> allowed = EnumSet.noneOf(Biome.class);
            Object allowedObj = map.get("allowedBiomes");
            if (allowedObj instanceof List<?> biomes) {
                for (Object b : biomes) {
                    Biome biome = readEnum(Biome.class, b);
                    if (biome != null && isLandBiomeStatic(biome)) {
                        allowed.add(biome);
                    }
                }
            }
            if (allowed.isEmpty()) {
                allowed = EnumSet.of(Biome.FIELD);
            }
            out.add(new StructureRule(
                    structure,
                    getDouble(map, "chancePerTile", 0.0),
                    getInt(map, "minimum", 0),
                    allowed
            ));
        }
        if (!out.isEmpty()) {
            structureRules = out.toArray(new StructureRule[0]);
        }
    }

    private void parseBiomeStructureOverrides(Object value) {
        biomeStructureOverrides.clear();
        if (!(value instanceof Map<?, ?> rawBiomes)) {
            return;
        }
        for (Map.Entry<?, ?> biomeEntry : rawBiomes.entrySet()) {
            Biome biome = readEnum(Biome.class, biomeEntry.getKey());
            if (biome == null) continue;
            if (!(biomeEntry.getValue() instanceof Map<?, ?> rawStructures)) continue;
            Map<NaturalStructure, BiomeStructureOverride> perStructure = new EnumMap<>(NaturalStructure.class);
            for (Map.Entry<?, ?> structureEntry : rawStructures.entrySet()) {
                NaturalStructure structure = readEnum(NaturalStructure.class, structureEntry.getKey());
                if (structure == null || structure == NaturalStructure.NONE) continue;
                if (!(structureEntry.getValue() instanceof Map<?, ?> rawOverride)) continue;
                Map<String, Object> map = castStringObjectMap(rawOverride);
                BiomeStructureOverride override = new BiomeStructureOverride(
                        coalesceDouble(getDoubleObj(map, "chancePerTile"), getDoubleObj(map, "spawnRate")),
                        coalesceInt(getIntObj(map, "minimumAbsolute"), getIntObj(map, "minimum")),
                        getDoubleObj(map, "minimumRelative"),
                        getDoubleObj(map, "chanceMultiplier"),
                        getIntObj(map, "requireNearWaterRadius"),
                        getIntObj(map, "blockNearWaterRadius"),
                        getIntObj(map, "blockNearPoiRadius"),
                        getDoubleObj(map, "minHeight"),
                        getDoubleObj(map, "maxHeight"),
                        getDoubleObj(map, "minMoisture"),
                        getDoubleObj(map, "maxMoisture")
                );
                perStructure.put(structure, override);
            }
            if (!perStructure.isEmpty()) {
                biomeStructureOverrides.put(biome, perStructure);
            }
        }
    }

    private void ensureBiomeStructureOverridesCompleto() {
        Map<Biome, Map<NaturalStructure, BiomeStructureOverride>> defaults = defaultBiomeStructureOverrides();
        for (Map.Entry<Biome, Map<NaturalStructure, BiomeStructureOverride>> entry : defaults.entrySet()) {
            Map<NaturalStructure, BiomeStructureOverride> atual = biomeStructureOverrides.computeIfAbsent(entry.getKey(), k -> new EnumMap<>(NaturalStructure.class));
            for (Map.Entry<NaturalStructure, BiomeStructureOverride> item : entry.getValue().entrySet()) {
                atual.putIfAbsent(item.getKey(), item.getValue());
            }
        }
    }

    BiomeStructureOverride structureOverride(Biome biome, NaturalStructure structure) {
        Map<NaturalStructure, BiomeStructureOverride> map = biomeStructureOverrides.get(biome);
        if (map == null) {
            return null;
        }
        return map.get(structure);
    }

    int resolveMinimum(StructureRule rule, Biome biome, int area) {
        return rule.minimum;
    }

    private Map<Biome, Map<NaturalStructure, BiomeStructureOverride>> defaultBiomeStructureOverrides() {
        Map<Biome, Map<NaturalStructure, BiomeStructureOverride>> out = new EnumMap<>(Biome.class);
        for (Biome biome : Biome.values()) {
            if (!isLandBiomeStatic(biome)) {
                continue;
            }
            Map<NaturalStructure, BiomeStructureOverride> perStructure = new EnumMap<>(NaturalStructure.class);
            for (StructureRule rule : structureRules) {
                double chance = rule.allows(biome) ? rule.chancePerTile : 0.0;
                perStructure.put(rule.structure, new BiomeStructureOverride(
                        chance,
                        0,
                        null,
                        1.0,
                        null,
                        null,
                        null,
                        null,
                        null,
                        null,
                        null
                ));
            }
            out.put(biome, perStructure);
        }
        return out;
    }

    private static BiomeRule[] defaultBiomeRules() {
        return new BiomeRule[]{
                new BiomeRule(Biome.FIELD,    0.82, 0.11, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0),
                new BiomeRule(Biome.FOREST,   1.35, 0.22, 0.0, 1.0, 0.52, 1.0, 0.0, 1.0),
                new BiomeRule(Biome.DESERT,   1.18, 0.13, 0.68, 1.0, 0.0, 0.42, 0.0, 1.0),
                new BiomeRule(Biome.SNOW,     0.65, 0.07, 0.0, 0.30, 0.0, 1.0, 0.0, 1.0),
                new BiomeRule(Biome.MAGIC,    0.10, 0.015, 0.0, 1.0, 0.0, 1.0, 0.88, 1.0),
                new BiomeRule(Biome.VOLCANIC, 0.08, 0.01, 0.52, 1.0, 0.0, 1.0, 0.83, 1.0),
                new BiomeRule(Biome.SWAMP,    0.65, 0.06, 0.0, 1.0, 0.62, 1.0, 0.60, 1.0)
        };
    }

    private static StructureRule[] defaultStructureRules() {
        EnumSet<Biome> land = EnumSet.of(Biome.FIELD, Biome.FOREST, Biome.DESERT, Biome.SNOW, Biome.MAGIC, Biome.VOLCANIC, Biome.SWAMP);
        return new StructureRule[]{
                new StructureRule(NaturalStructure.TREE,      0.0080,  60_000, EnumSet.of(Biome.FIELD, Biome.FOREST, Biome.SWAMP, Biome.MAGIC)),
                new StructureRule(NaturalStructure.ROCK,      0.0030,  25_000, land),
                new StructureRule(NaturalStructure.BUSH,      0.0035,  25_000, EnumSet.of(Biome.FIELD, Biome.FOREST, Biome.SWAMP, Biome.MAGIC)),
                new StructureRule(NaturalStructure.GOLD,      0.0006,   5_000, land),
                new StructureRule(NaturalStructure.AMETHYST,  0.0013,   6_000, EnumSet.of(Biome.MAGIC)),
                new StructureRule(NaturalStructure.DIAMOND,   0.0011,   5_000, EnumSet.of(Biome.SNOW)),
                new StructureRule(NaturalStructure.RUBY,      0.0012,   5_000, EnumSet.of(Biome.VOLCANIC)),
                new StructureRule(NaturalStructure.EMERALD,   0.0011,   5_000, EnumSet.of(Biome.DESERT)),
                new StructureRule(NaturalStructure.PALM,      0.0022,   7_000, EnumSet.of(Biome.DESERT)),
                new StructureRule(NaturalStructure.PINE,      0.0028,   8_000, EnumSet.of(Biome.SNOW)),
                new StructureRule(NaturalStructure.COPPER,    0.0012,   8_000, land),
                new StructureRule(NaturalStructure.LAVA_POOL, 0.0018,   1_000, EnumSet.of(Biome.VOLCANIC))
        };
    }

    private static Object firstPresent(Map<String, Object> root, String... keys) {
        for (String key : keys) {
            if (root.containsKey(key)) {
                return root.get(key);
            }
        }
        return null;
    }

    private static Map<String, Object> section(Map<String, Object> root, String... keys) {
        for (String key : keys) {
            Object value = root.get(key);
            if (value instanceof Map<?, ?> map) {
                return castStringObjectMap(map);
            }
        }
        return Collections.emptyMap();
    }

    private static int getInt(Map<String, Object> map, String key, int defaultValue) {
        Object value = map.get(key);
        if (value instanceof Number n) {
            return n.intValue();
        }
        if (value instanceof String s) {
            try {
                return Integer.parseInt(s.trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return defaultValue;
    }

    private static Integer getIntObj(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value instanceof Number n) return n.intValue();
        if (value instanceof String s) {
            try {
                return Integer.parseInt(s.trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return null;
    }

    private static long getLong(Map<String, Object> map, String key, long defaultValue) {
        Object value = map.get(key);
        if (value instanceof Number n) {
            return n.longValue();
        }
        if (value instanceof String s) {
            try {
                return Long.parseLong(s.trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return defaultValue;
    }

    private static double getDouble(Map<String, Object> map, String key, double defaultValue) {
        Object value = map.get(key);
        if (value instanceof Number n) {
            return n.doubleValue();
        }
        if (value instanceof String s) {
            try {
                return Double.parseDouble(s.trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return defaultValue;
    }

    private static Integer coalesceInt(Integer a, Integer b) {
        return a != null ? a : b;
    }

    private static Double coalesceDouble(Double a, Double b) {
        return a != null ? a : b;
    }

    private static Double getDoubleObj(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value instanceof Number n) return n.doubleValue();
        if (value instanceof String s) {
            try {
                return Double.parseDouble(s.trim());
            } catch (NumberFormatException ignored) {
            }
        }
        return null;
    }

    private static <E extends Enum<E>> E readEnum(Class<E> type, Object value) {
        if (value == null) return null;
        try {
            return Enum.valueOf(type, String.valueOf(value).trim().toUpperCase());
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private static boolean isLandBiomeStatic(Biome biome) {
        return biome != Biome.OCEAN && biome != Biome.SHALLOW_WATER;
    }
}

    static final class SimpleJson {
        static Object parse(String text) {
            return new Parser(text).parseValue();
        }

        static String stringify(Object value) {
            StringBuilder sb = new StringBuilder(32768);
            writeValue(sb, value, 0);
            return sb.toString();
        }

        private static void writeValue(StringBuilder sb, Object value, int indent) {
            if (value == null) {
                sb.append("null");
                return;
            }
            if (value instanceof String s) {
                sb.append('"').append(escape(s)).append('"');
                return;
            }
            if (value instanceof Number || value instanceof Boolean) {
                sb.append(value);
                return;
            }
            if (value instanceof Map<?, ?> map) {
                sb.append("{\n");
                int size = map.size();
                int i = 0;
                for (Map.Entry<?, ?> e : map.entrySet()) {
                    indent(sb, indent + 2);
                    sb.append('"').append(escape(String.valueOf(e.getKey()))).append("\": ");
                    writeValue(sb, e.getValue(), indent + 2);
                    if (++i < size) sb.append(',');
                    sb.append('\n');
                }
                indent(sb, indent);
                sb.append('}');
                return;
            }
            if (value instanceof List<?> list) {
                sb.append("[\n");
                for (int i = 0; i < list.size(); i++) {
                    indent(sb, indent + 2);
                    writeValue(sb, list.get(i), indent + 2);
                    if (i < list.size() - 1) sb.append(',');
                    sb.append('\n');
                }
                indent(sb, indent);
                sb.append(']');
                return;
            }
            sb.append('"').append(escape(String.valueOf(value))).append('"');
        }

        private static void indent(StringBuilder sb, int n) {
            for (int i = 0; i < n; i++) sb.append(' ');
        }

        private static String escape(String s) {
            return s
                    .replace("\\", "\\\\")
                    .replace("\"", "\\\"")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t");
        }

        static final class Parser {
            private final String s;
            private int i;

            Parser(String s) {
                this.s = s == null ? "" : s;
            }

            Object parseValue() {
                skipWs();
                if (i >= s.length()) return null;
                char c = s.charAt(i);
                if (c == '{') return parseObject();
                if (c == '[') return parseArray();
                if (c == '"') return parseString();
                if (c == 't' || c == 'f') return parseBoolean();
                if (c == 'n') return parseNull();
                return parseNumber();
            }

            private Map<String, Object> parseObject() {
                Map<String, Object> map = new LinkedHashMap<>();
                i++;
                skipWs();
                if (peek('}')) {
                    i++;
                    return map;
                }
                while (i < s.length()) {
                    skipWs();
                    String key = parseString();
                    skipWs();
                    expect(':');
                    Object value = parseValue();
                    map.put(key, value);
                    skipWs();
                    if (peek(',')) {
                        i++;
                        continue;
                    }
                    expect('}');
                    break;
                }
                return map;
            }

            private List<Object> parseArray() {
                List<Object> list = new ArrayList<>();
                i++;
                skipWs();
                if (peek(']')) {
                    i++;
                    return list;
                }
                while (i < s.length()) {
                    list.add(parseValue());
                    skipWs();
                    if (peek(',')) {
                        i++;
                        continue;
                    }
                    expect(']');
                    break;
                }
                return list;
            }

            private String parseString() {
                expect('"');
                StringBuilder out = new StringBuilder();
                while (i < s.length()) {
                    char c = s.charAt(i++);
                    if (c == '"') break;
                    if (c == '\\' && i < s.length()) {
                        char esc = s.charAt(i++);
                        switch (esc) {
                            case '"' -> out.append('"');
                            case '\\' -> out.append('\\');
                            case '/' -> out.append('/');
                            case 'b' -> out.append('\b');
                            case 'f' -> out.append('\f');
                            case 'n' -> out.append('\n');
                            case 'r' -> out.append('\r');
                            case 't' -> out.append('\t');
                            case 'u' -> {
                                if (i + 4 <= s.length()) {
                                    String hex = s.substring(i, i + 4);
                                    i += 4;
                                    try {
                                        out.append((char) Integer.parseInt(hex, 16));
                                    } catch (NumberFormatException ignored) {
                                    }
                                }
                            }
                            default -> out.append(esc);
                        }
                    } else {
                        out.append(c);
                    }
                }
                return out.toString();
            }

            private Object parseBoolean() {
                if (s.startsWith("true", i)) {
                    i += 4;
                    return Boolean.TRUE;
                }
                if (s.startsWith("false", i)) {
                    i += 5;
                    return Boolean.FALSE;
                }
                throw new IllegalArgumentException("JSON invalido na posicao " + i);
            }

            private Object parseNull() {
                if (s.startsWith("null", i)) {
                    i += 4;
                    return null;
                }
                throw new IllegalArgumentException("JSON invalido na posicao " + i);
            }

            private Number parseNumber() {
                int start = i;
                if (peek('-')) i++;
                while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
                if (peek('.')) {
                    i++;
                    while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
                }
                if (peek('e') || peek('E')) {
                    i++;
                    if (peek('+') || peek('-')) i++;
                    while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
                }
                String token = s.substring(start, i);
                if (token.isEmpty() || token.equals("-")) {
                    throw new IllegalArgumentException("Numero JSON invalido na posicao " + start);
                }
                if (token.contains(".") || token.contains("e") || token.contains("E")) {
                    return Double.parseDouble(token);
                }
                long v = Long.parseLong(token);
                if (v >= Integer.MIN_VALUE && v <= Integer.MAX_VALUE) {
                    return (int) v;
                }
                return v;
            }

            private void skipWs() {
                while (i < s.length()) {
                    char c = s.charAt(i);
                    if (c == ' ' || c == '\n' || c == '\r' || c == '\t') {
                        i++;
                    } else {
                        break;
                    }
                }
            }

            private boolean peek(char c) {
                return i < s.length() && s.charAt(i) == c;
            }

            private void expect(char c) {
                if (!peek(c)) {
                    throw new IllegalArgumentException("JSON invalido na posicao " + i + ", esperado '" + c + "'");
                }
                i++;
            }
        }
    }

    static final class Generator {
        private final Rules rules;
        private final int width;
        private final int height;
        private final int area;

        private final byte[] biomeMap;
        private final byte[] macroBiomeGrid;
        private final int macroGridWidth;
        private final int macroGridHeight;
        private final int macroCellWidth;
        private final int macroCellHeight;
        private final byte[] tileMap;
        private final byte[] naturalMap;
        private final List<Poi> pois = new ArrayList<>();
        private final int[] biomeCounts = new int[Biome.values().length];
        private final int[] naturalCounts = new int[NaturalStructure.values().length];
        private int spawnChunkX = -1;
        private int spawnChunkY = -1;
        private int spawnX = -1;
        private int spawnY = -1;

        Generator(Rules rules) {
            this.rules = rules;
            this.width = rules.width;
            this.height = rules.height;
            this.area = width * height;
            this.macroGridWidth = Math.max(1, rules.macroGridWidth);
            this.macroGridHeight = Math.max(1, rules.macroGridHeight);
            this.macroCellWidth = Math.max(1, (int) Math.ceil(width / (double) this.macroGridWidth));
            this.macroCellHeight = Math.max(1, (int) Math.ceil(height / (double) this.macroGridHeight));
            this.biomeMap = new byte[area];
            this.macroBiomeGrid = new byte[this.macroGridWidth * this.macroGridHeight];
            this.tileMap = new byte[area];
            this.naturalMap = new byte[area];
        }

        void generate() throws IOException {
            long t0 = System.currentTimeMillis();
            File dir = new File(rules.outputDirectory);
            if (!dir.exists() && !dir.mkdirs()) {
                throw new IOException("Nao foi possivel criar a pasta de saida: " + dir.getAbsolutePath());
            }

            System.out.println("Seed: " + rules.seed);
            System.out.println("Gerando terreno base...");
            generateBaseTerrain();
            logTime("Terreno base", t0);

            long t1 = System.currentTimeMillis();
            System.out.println("Gerando rios...");
            generateRivers();
            updateShallowWaterNearLand();
            logTime("Rios", t1);

            long t3 = System.currentTimeMillis();
            System.out.println("Posicionando estruturas naturais...");
            placeNaturalStructures();
            ensureNaturalMinimums();
            ensureNaturalMinimumsByBiome();
            logTime("Estruturas naturais", t3);

            long t4 = System.currentTimeMillis();
            System.out.println("Posicionando ginasios, dungeons e vilas...");
            placePois();
            logTime("POIs", t4);

            long t5 = System.currentTimeMillis();
            findSpawnChunk();
            System.out.println("Exportando mundo em chunks...");
            writeWorldChunks(dir);
            logTime("Export", t5);

            long t6 = System.currentTimeMillis();
            System.out.println("Gerando foto do mundo...");
            renderBaseWorld(new File(dir, "world_foto.png"));
            logTime("Foto do mundo", t6);

            printSummary();
            logTime("Tempo total", t0);
        }

        private void findSpawnChunk() {
            int chunkSize = Math.max(1, rules.diskChunkBlocos);
            int chunksX = (int) Math.ceil(width / (double) chunkSize);
            int chunksY = (int) Math.ceil(height / (double) chunkSize);
            int centerCx = chunksX / 2;
            int centerCy = chunksY / 2;

            for (int radius = 0; radius <= Math.max(chunksX, chunksY); radius++) {
                for (int cy = Math.max(0, centerCy - radius); cy <= Math.min(chunksY - 1, centerCy + radius); cy++) {
                    for (int cx = Math.max(0, centerCx - radius); cx <= Math.min(chunksX - 1, centerCx + radius); cx++) {
                        if (Math.max(Math.abs(cx - centerCx), Math.abs(cy - centerCy)) != radius) {
                            continue;
                        }
                        if (isValidSpawnChunk(cx, cy, chunkSize)) {
                            spawnChunkX = cx;
                            spawnChunkY = cy;
                            spawnX = Math.min(width - 1, cx * chunkSize + chunkSize / 2);
                            spawnY = Math.min(height - 1, cy * chunkSize + chunkSize / 2);
                            System.out.println("Spawn encontrado no chunk (" + spawnChunkX + "," + spawnChunkY + ") em bloco (" + spawnX + "," + spawnY + ")");
                            return;
                        }
                    }
                }
            }

            spawnChunkX = centerCx;
            spawnChunkY = centerCy;
            spawnX = Math.min(width - 1, spawnChunkX * chunkSize + chunkSize / 2);
            spawnY = Math.min(height - 1, spawnChunkY * chunkSize + chunkSize / 2);
            System.out.println("[WARN] Nenhum chunk 100% FIELD encontrado, usando centro como fallback.");
        }

        private boolean isValidSpawnChunk(int cx, int cy, int chunkSize) {
            int x0 = cx * chunkSize;
            int y0 = cy * chunkSize;
            int x1 = Math.min(width, x0 + chunkSize);
            int y1 = Math.min(height, y0 + chunkSize);

            for (Poi poi : pois) {
                if (poi.x >= x0 && poi.x < x1 && poi.y >= y0 && poi.y < y1) {
                    return false;
                }
            }

            for (int y = y0; y < y1; y++) {
                for (int x = x0; x < x1; x++) {
                    int idx = index(x, y);
                    if ((tileMap[idx] & 0xFF) != Tile.FIELD_GRASS.ordinal()) {
                        return false;
                    }
                    if ((biomeMap[idx] & 0xFF) != Biome.FIELD.ordinal()) {
                        return false;
                    }
                    if ((naturalMap[idx] & 0xFF) != NaturalStructure.NONE.ordinal()) {
                        return false;
                    }
                }
            }
            return true;
        }

        private void writeWorldChunks(File outputDir) throws IOException {
            int chunkSize = Math.max(1, rules.diskChunkBlocos);
            int chunksX = (int) Math.ceil(width / (double) chunkSize);
            int chunksY = (int) Math.ceil(height / (double) chunkSize);

            File chunksDir = new File(outputDir, "world_chunks");
            if (!chunksDir.exists() && !chunksDir.mkdirs()) {
                throw new IOException("Nao foi possivel criar pasta world_chunks: " + chunksDir.getAbsolutePath());
            }

            File metaFile = new File(outputDir, "world_meta.json");
            try (BufferedWriter writer = Files.newBufferedWriter(metaFile.toPath(), StandardCharsets.UTF_8)) {
                writer.write("{\n");
                writer.write("  \"seed\": " + rules.seed + ",\n");
                writer.write("  \"width\": " + width + ",\n");
                writer.write("  \"height\": " + height + ",\n");
                writer.write("  \"chunk_blocos\": " + chunkSize + ",\n");
                writer.write("  \"chunks_x\": " + chunksX + ",\n");
                writer.write("  \"chunks_y\": " + chunksY + ",\n");
                writer.write("  \"spawn_chunk_x\": " + spawnChunkX + ",\n");
                writer.write("  \"spawn_chunk_y\": " + spawnChunkY + ",\n");
                writer.write("  \"spawn_x\": " + spawnX + ",\n");
                writer.write("  \"spawn_y\": " + spawnY + ",\n");
                writer.write("  \"rules_file\": \"" + rules.rulesFileUsed.replace("\\", "\\\\") + "\"\n");
                writer.write("}\n");
            }

            byte[] structuresMap = buildStructuresGrid();
            int totalChunks = chunksX * chunksY;
            int chunksGerados = 0;
            for (int cy = 0; cy < chunksY; cy++) {
                for (int cx = 0; cx < chunksX; cx++) {
                    File chunkFile = new File(chunksDir, "chunk_" + cx + "_" + cy + ".json");
                    writeChunkJson(chunkFile, cx, cy, chunkSize, structuresMap);
                    chunksGerados++;
                }
                System.out.println("[PROGRESSO] ETAPA=CHUNKS ATUAL=" + chunksGerados + " TOTAL=" + totalChunks + " MSG=Salvando chunks");
            }
        }

        private void writeChunkJson(File file, int cx, int cy, int chunkSize, byte[] structuresMap) throws IOException {
            int x0 = cx * chunkSize;
            int y0 = cy * chunkSize;

            try (BufferedWriter writer = Files.newBufferedWriter(file.toPath(), StandardCharsets.UTF_8)) {
                writer.write("{\n");
                writer.write("  \"meta\": {\n");
                writer.write("    \"chunk_x\": " + cx + ",\n");
                writer.write("    \"chunk_y\": " + cy + ",\n");
                writer.write("    \"chunk_blocos\": " + chunkSize + ",\n");
                writer.write("    \"world_width\": " + width + ",\n");
                writer.write("    \"world_height\": " + height + ",\n");
                writer.write("    \"seed\": " + rules.seed + "\n");
                writer.write("  },\n");

                writer.write("  \"grid_blocos\": ");
                writeChunkGridFromMap(writer, tileMap, x0, y0, chunkSize);
                writer.write(",\n");

                writer.write("  \"grid_biomas\": ");
                writeChunkGridFromMap(writer, biomeMap, x0, y0, chunkSize);
                writer.write(",\n");

                writer.write("  \"grid_estruturas\": ");
                writeChunkGridFromMap(writer, structuresMap, x0, y0, chunkSize);
                writer.write("\n}\n");
            }
        }

        private byte[] buildStructuresGrid() {
            byte[] grid = Arrays.copyOf(naturalMap, naturalMap.length);
            for (Poi poi : pois) {
                int idx = index(poi.x, poi.y);
                grid[idx] = (byte) poiCode(poi.type);
            }
            return grid;
        }

        private int poiCode(PoiType type) {
            return switch (type) {
                case GYM -> 101;
                case DUNGEON -> 102;
                case VILLAGE -> 103;
            };
        }

        private void writeChunkGridFromMap(BufferedWriter writer, byte[] map, int x0, int y0, int chunkSize) throws IOException {
            writer.write("[\n");
            for (int by = 0; by < chunkSize; by++) {
                int y = y0 + by;
                writer.write("    [");
                for (int bx = 0; bx < chunkSize; bx++) {
                    int x = x0 + bx;
                    int value = 0;
                    if (x >= 0 && y >= 0 && x < width && y < height) {
                        int idx = index(x, y);
                        value = map[idx] & 0xFF;
                    }
                    writer.write(Integer.toString(value));
                    if (bx < chunkSize - 1) {
                        writer.write(',');
                    }
                }
                writer.write("]");
                if (by < chunkSize - 1) {
                    writer.write(',');
                }
                writer.write('\n');
            }
            writer.write("  ]");
        }

        private void generateBaseTerrain() {
            Arrays.fill(naturalMap, (byte) NaturalStructure.NONE.ordinal());
            Arrays.fill(biomeCounts, 0);
            buildMacroBiomeGrid();

            for (int y = 0; y < height; y++) {
                if (y % 500 == 0) {
                    System.out.println("  linha " + y + " / " + height);
                }
                for (int x = 0; x < width; x++) {
                    int idx = index(x, y);

                    double edgePenalty = edgeWaterPenalty(x, y);
                    if (hardBorder(x, y)) {
                        biomeMap[idx] = (byte) Biome.OCEAN.ordinal();
                        tileMap[idx] = (byte) Tile.WATER_DEEP.ordinal();
                        biomeCounts[Biome.OCEAN.ordinal()]++;
                        continue;
                    }

                    double elevation = elevation(x, y) - edgePenalty;
                    double moisture = moisture(x, y);

                    if (elevation < rules.seaLevel - rules.deepWaterExtraDepth) {
                        biomeMap[idx] = (byte) Biome.OCEAN.ordinal();
                        tileMap[idx] = (byte) Tile.WATER_DEEP.ordinal();
                        biomeCounts[Biome.OCEAN.ordinal()]++;
                        continue;
                    }
                    if (elevation < rules.seaLevel + rules.shallowWaterBand) {
                        biomeMap[idx] = (byte) Biome.SHALLOW_WATER.ordinal();
                        tileMap[idx] = (byte) Tile.WATER_SHALLOW.ordinal();
                        biomeCounts[Biome.SHALLOW_WATER.ordinal()]++;
                        continue;
                    }

                    if (isLakeCandidate(elevation, moisture, x, y)) {
                        biomeMap[idx] = (byte) Biome.SHALLOW_WATER.ordinal();
                        tileMap[idx] = (byte) Tile.WATER_SHALLOW.ordinal();
                        biomeCounts[Biome.SHALLOW_WATER.ordinal()]++;
                        continue;
                    }

                    Biome biome = macroBiomeForTile(x, y);
                    biomeMap[idx] = (byte) biome.ordinal();
                    tileMap[idx] = (byte) tileForBiome(biome).ordinal();
                    biomeCounts[biome.ordinal()]++;
                }
            }
            updateCoastsAndBeaches();
            updateShallowWaterNearLand();
            updateCoastsAndBeaches();
        }

        private void generateRivers() {
            int created = 0;
            int attempts = 0;
            while (created < rules.riverSources && attempts < rules.riverSources * rules.riverMaxAttemptsPerSource) {
                attempts++;
                int x = boundedRandomInt(rules.riverSourceMargin, width - rules.riverSourceMargin, rules.seed + 91L * attempts);
                int y = boundedRandomInt(rules.riverSourceMargin, height - rules.riverSourceMargin, rules.seed + 131L * attempts);
                int idx = index(x, y);
                if (!isLandBiome(Biome.values()[biomeMap[idx] & 0xFF])) {
                    continue;
                }
                double h = elevation(x, y) - edgeWaterPenalty(x, y);
                if (h < rules.riverSourceMinHeight) {
                    continue;
                }
                if (nearWater(x, y, rules.riverSourceNearWaterRadius)) {
                    continue;
                }
                carveRiverFrom(x, y);
                created++;
            }
            System.out.println("  fontes de rio criadas: " + created + " / " + rules.riverSources);
        }

        private void buildMacroBiomeGrid() {
            for (int my = 0; my < macroGridHeight; my++) {
                for (int mx = 0; mx < macroGridWidth; mx++) {
                    int sampleX = clamp(mx * macroCellWidth + macroCellWidth / 2, 0, width - 1);
                    int sampleY = clamp(my * macroCellHeight + macroCellHeight / 2, 0, height - 1);
                    macroBiomeGrid[macroIndex(mx, my)] = (byte) classifyMacroBiome(sampleX, sampleY).ordinal();
                }
            }

            for (int i = 0; i < rules.macroSmoothingPasses; i++) {
                smoothMacroBiomeGrid(rules.macroMajorityRadius);
            }
            removeSmallMacroRegions(rules.macroMinRegionCells);
            smoothMacroBiomeGrid(rules.macroMajorityRadius);
        }

        private Biome classifyMacroBiome(int x, int y) {
            double latitude = 1.0 - Math.abs((y / (double) (height - 1)) * 2.0 - 1.0);
            double macroTemperature = clamp01(
                    fbm(x, y,
                            rules.macroTemperatureOctaves,
                            rules.macroTemperaturePersistence,
                            rules.macroTemperatureLacunarity,
                            rules.macroTemperatureScale,
                            rules.macroTemperatureSeedOffset
                    ) * rules.macroTemperatureNoiseWeight + latitude * rules.macroTemperatureLatitudeWeight
            );
            double macroMoisture = fbm(x, y,
                    rules.macroMoistureOctaves,
                    rules.macroMoisturePersistence,
                    rules.macroMoistureLacunarity,
                    rules.macroMoistureScale,
                    rules.macroMoistureSeedOffset
            );
            double macroMagic = ridgeFbm(x, y,
                    rules.macroMagicOctaves,
                    rules.macroMagicPersistence,
                    rules.macroMagicLacunarity,
                    rules.macroMagicScale,
                    rules.macroMagicSeedOffset
            );
            double macroVolcanic = ridgeFbm(x, y,
                    rules.macroVolcanicOctaves,
                    rules.macroVolcanicPersistence,
                    rules.macroVolcanicLacunarity,
                    rules.macroVolcanicScale,
                    rules.macroVolcanicSeedOffset
            );
            double macroSwamp = fbm(x, y,
                    rules.macroSwampOctaves,
                    rules.macroSwampPersistence,
                    rules.macroSwampLacunarity,
                    rules.macroSwampScale,
                    rules.macroSwampSeedOffset
            );

            BiomeRule volcanic = biomeRule(Biome.VOLCANIC);
            if (volcanic != null && macroVolcanic > volcanic.minPrimaryNoise && macroTemperature > volcanic.minTemperature) {
                return Biome.VOLCANIC;
            }
            BiomeRule magic = biomeRule(Biome.MAGIC);
            if (magic != null && macroMagic > magic.minPrimaryNoise) {
                return Biome.MAGIC;
            }
            BiomeRule swamp = biomeRule(Biome.SWAMP);
            if (swamp != null && macroSwamp > swamp.minPrimaryNoise && macroMoisture > swamp.minMoisture) {
                return Biome.SWAMP;
            }
            BiomeRule snow = biomeRule(Biome.SNOW);
            if (snow != null && macroTemperature < snow.maxTemperature) {
                return Biome.SNOW;
            }
            BiomeRule desert = biomeRule(Biome.DESERT);
            if (desert != null && macroTemperature > desert.minTemperature && macroMoisture < desert.maxMoisture) {
                return Biome.DESERT;
            }
            BiomeRule forest = biomeRule(Biome.FOREST);
            if (forest != null && macroMoisture > forest.minMoisture) {
                return Biome.FOREST;
            }
            return Biome.FIELD;
        }

        private BiomeRule biomeRule(Biome biome) {
            for (BiomeRule rule : rules.biomeRules) {
                if (rule.biome == biome) {
                    return rule;
                }
            }
            return null;
        }

        private void smoothMacroBiomeGrid(int radius) {
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
                            Biome neighbor = Biome.values()[macroBiomeGrid[macroIndex(nx, ny)] & 0xFF];
                            if (isLandBiome(neighbor)) {
                                counts[neighbor.ordinal()]++;
                            }
                        }
                    }

                    Biome dominant = Biome.values()[macroBiomeGrid[macroIndex(mx, my)] & 0xFF];
                    int dominantCount = counts[dominant.ordinal()];
                    for (Biome biome : Biome.values()) {
                        if (!isLandBiome(biome)) {
                            continue;
                        }
                        if (counts[biome.ordinal()] > dominantCount) {
                            dominant = biome;
                            dominantCount = counts[biome.ordinal()];
                        }
                    }
                    smoothed[macroIndex(mx, my)] = (byte) dominant.ordinal();
                }
            }

            System.arraycopy(smoothed, 0, macroBiomeGrid, 0, macroBiomeGrid.length);
        }

        private void removeSmallMacroRegions(int minCells) {
            int cells = macroGridWidth * macroGridHeight;
            boolean[] visited = new boolean[cells];
            int[] queue = new int[cells];
            int[] region = new int[cells];

            for (int my = 0; my < macroGridHeight; my++) {
                for (int mx = 0; mx < macroGridWidth; mx++) {
                    int start = macroIndex(mx, my);
                    if (visited[start]) {
                        continue;
                    }

                    Biome biome = Biome.values()[macroBiomeGrid[start] & 0xFF];
                    if (!isLandBiome(biome)) {
                        visited[start] = true;
                        continue;
                    }

                    int qh = 0;
                    int qt = 0;
                    int regionSize = 0;
                    queue[qt++] = start;
                    visited[start] = true;

                    while (qh < qt) {
                        int cell = queue[qh++];
                        region[regionSize++] = cell;
                        int cx = cell % macroGridWidth;
                        int cy = cell / macroGridWidth;

                        if (cx > 0) {
                            int n = macroIndex(cx - 1, cy);
                            if (!visited[n] && (macroBiomeGrid[n] & 0xFF) == biome.ordinal()) {
                                visited[n] = true;
                                queue[qt++] = n;
                            }
                        }
                        if (cx < macroGridWidth - 1) {
                            int n = macroIndex(cx + 1, cy);
                            if (!visited[n] && (macroBiomeGrid[n] & 0xFF) == biome.ordinal()) {
                                visited[n] = true;
                                queue[qt++] = n;
                            }
                        }
                        if (cy > 0) {
                            int n = macroIndex(cx, cy - 1);
                            if (!visited[n] && (macroBiomeGrid[n] & 0xFF) == biome.ordinal()) {
                                visited[n] = true;
                                queue[qt++] = n;
                            }
                        }
                        if (cy < macroGridHeight - 1) {
                            int n = macroIndex(cx, cy + 1);
                            if (!visited[n] && (macroBiomeGrid[n] & 0xFF) == biome.ordinal()) {
                                visited[n] = true;
                                queue[qt++] = n;
                            }
                        }
                    }

                    if (regionSize >= minCells) {
                        continue;
                    }

                    Biome replacement = dominantNeighborMacroBiome(region, regionSize, biome);
                    for (int i = 0; i < regionSize; i++) {
                        macroBiomeGrid[region[i]] = (byte) replacement.ordinal();
                    }
                }
            }
        }

        private Biome dominantNeighborMacroBiome(int[] regionCells, int regionSize, Biome currentBiome) {
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
                        Biome neighbor = Biome.values()[macroBiomeGrid[macroIndex(nx, ny)] & 0xFF];
                        if (isLandBiome(neighbor) && neighbor != currentBiome) {
                            counts[neighbor.ordinal()]++;
                        }
                    }
                }
            }

            Biome best = currentBiome;
            int bestCount = 0;
            for (Biome biome : Biome.values()) {
                if (!isLandBiome(biome)) {
                    continue;
                }
                int count = counts[biome.ordinal()];
                if (count > bestCount) {
                    bestCount = count;
                    best = biome;
                }
            }
            return bestCount > 0 ? best : Biome.FIELD;
        }

        private Biome macroBiomeForTile(int x, int y) {
            double warpScale = macroCellWidth * rules.macroWarpScaleFactor;
            double warpX = fbm(x, y, 3, 0.55, 2.0, warpScale, 777L);
            double warpY = fbm(x + 2000, y + 2000, 3, 0.55, 2.0, warpScale, 888L);

            double warpedX = x + (warpX - 0.5) * macroCellWidth * rules.macroWarpStrength;
            double warpedY = y + (warpY - 0.5) * macroCellHeight * rules.macroWarpStrength;

            double gx = (warpedX + 0.5) / macroCellWidth - 0.5;
            double gy = (warpedY + 0.5) / macroCellHeight - 0.5;

            int mx0 = clamp(fastFloor(gx), 0, macroGridWidth - 1);
            int my0 = clamp(fastFloor(gy), 0, macroGridHeight - 1);
            int mx1 = clamp(mx0 + 1, 0, macroGridWidth - 1);
            int my1 = clamp(my0 + 1, 0, macroGridHeight - 1);

            double tx = smoothstep(clamp01(gx - mx0));
            double ty = smoothstep(clamp01(gy - my0));

            double w00 = (1.0 - tx) * (1.0 - ty);
            double w10 = tx * (1.0 - ty);
            double w01 = (1.0 - tx) * ty;
            double w11 = tx * ty;

            double[] scores = new double[Biome.values().length];
            addMacroBiomeScore(scores, mx0, my0, w00);
            addMacroBiomeScore(scores, mx1, my0, w10);
            addMacroBiomeScore(scores, mx0, my1, w01);
            addMacroBiomeScore(scores, mx1, my1, w11);

            int currentMx = clamp(fastFloor(warpedX / macroCellWidth), 0, macroGridWidth - 1);
            int currentMy = clamp(fastFloor(warpedY / macroCellHeight), 0, macroGridHeight - 1);
            Biome currentMacroBiome = Biome.values()[macroBiomeGrid[macroIndex(currentMx, currentMy)] & 0xFF];
            if (isLandBiome(currentMacroBiome)) {
                scores[currentMacroBiome.ordinal()] += rules.macroLocalBlend;
            }

            double edgeNoise = (fbm(x, y, 2, 0.55, 2.0, macroCellWidth * rules.macroEdgeNoiseScaleFactor, 913L) - 0.5)
                    * rules.macroEdgeNoiseStrength;
            applyNeighborEdgeJitter(scores, edgeNoise, x, y, mx0, my0);
            applyNeighborEdgeJitter(scores, edgeNoise, x, y, mx1, my0);
            applyNeighborEdgeJitter(scores, edgeNoise, x, y, mx0, my1);
            applyNeighborEdgeJitter(scores, edgeNoise, x, y, mx1, my1);

            return dominantLandBiome(scores, Biome.FIELD);
        }

        private void applyNeighborEdgeJitter(double[] scores, double edgeNoise, int x, int y, int mx, int my) {
            Biome b = Biome.values()[macroBiomeGrid[macroIndex(mx, my)] & 0xFF];
            if (!isLandBiome(b) || edgeNoise == 0.0) {
                return;
            }
            long h = tileSeed(x + mx * 31, y + my * 17, 991L + b.ordinal() * 131L);
            double tie = random01(h) - 0.5;
            scores[b.ordinal()] += edgeNoise * tie;
        }

        private void addMacroBiomeScore(double[] scores, int mx, int my, double weight) {
            if (weight <= 0.0) {
                return;
            }
            Biome b = Biome.values()[macroBiomeGrid[macroIndex(mx, my)] & 0xFF];
            if (isLandBiome(b)) {
                scores[b.ordinal()] += weight;
            }
        }

        private Biome dominantLandBiome(double[] scores, Biome fallback) {
            Biome best = fallback;
            double bestScore = Double.NEGATIVE_INFINITY;
            for (Biome biome : Biome.values()) {
                if (!isLandBiome(biome)) {
                    continue;
                }
                double score = scores[biome.ordinal()];
                if (score > bestScore) {
                    bestScore = score;
                    best = biome;
                }
            }
            return best;
        }

        private int macroIndex(int x, int y) {
            return y * macroGridWidth + x;
        }

        private void carveRiverFrom(int startX, int startY) {
            int x = startX;
            int y = startY;
            int lastX = -1;
            int lastY = -1;

            for (int step = 0; step < rules.riverMaxLength; step++) {
                paintCircleAsShallowWater(x, y, rules.riverWidth);
                if (nearOcean(x, y, rules.oceanDetectionRadius)) {
                    paintCircleAsShallowWater(x, y, rules.riverWidth + rules.riverTerminalExtraWidth);
                    return;
                }

                double current = elevation(x, y) - edgeWaterPenalty(x, y);
                int bestX = x;
                int bestY = y;
                double bestH = current;

                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dx == 0 && dy == 0) {
                            continue;
                        }
                        int nx = clamp(x + dx, 1, width - 2);
                        int ny = clamp(y + dy, 1, height - 2);
                        if (nx == lastX && ny == lastY) {
                            continue;
                        }
                        double nh = elevation(nx, ny) - edgeWaterPenalty(nx, ny);
                        if (nh < bestH) {
                            bestH = nh;
                            bestX = nx;
                            bestY = ny;
                        }
                    }
                }

                if (bestX == x && bestY == y) {
                    paintCircleAsShallowWater(x, y, rules.riverWidth + rules.riverTerminalExtraWidth);
                    return;
                }

                lastX = x;
                lastY = y;
                x = bestX;
                y = bestY;
            }
        }
        private void placeNaturalStructures() {
            Arrays.fill(naturalCounts, 0);
            for (int y = 0; y < height; y++) {
                if (y % 800 == 0) {
                    System.out.println("  estruturas na linha " + y + " / " + height);
                }
                for (int x = 0; x < width; x++) {
                    int idx = index(x, y);
                    Biome biome = Biome.values()[biomeMap[idx] & 0xFF];
                    if (!isLandBiome(biome)) {
                        continue;
                    }
                    if (nearPoi(x, y, rules.naturalBlockNearPoiRadius)) {
                        continue;
                    }
                    if (nearWater(x, y, rules.naturalBlockNearWaterRadius) && biome != Biome.DESERT && biome != Biome.SWAMP) {
                        continue;
                    }
                    long localSeed = tileSeed(x, y, 701);
                    NaturalStructure chosen = chooseNaturalStructure(biome, x, y, localSeed);
                    if (chosen == NaturalStructure.NONE) {
                        continue;
                    }
                    naturalMap[idx] = (byte) chosen.ordinal();
                    naturalCounts[chosen.ordinal()]++;
                }
            }
        }

        private void ensureNaturalMinimumsByBiome() {
            for (Biome biome : Biome.values()) {
                if (!isLandBiome(biome)) {
                    continue;
                }
                Map<NaturalStructure, Rules.BiomeStructureOverride> perStructure = rules.biomeStructureOverrides.get(biome);
                if (perStructure == null) {
                    continue;
                }
                for (StructureRule rule : rules.structureRules) {
                    Rules.BiomeStructureOverride override = perStructure.get(rule.structure);
                    if (override == null) {
                        continue;
                    }
                    int alvo = 0;
                    if (override.minimumAbsolute != null) {
                        alvo = Math.max(0, override.minimumAbsolute);
                    } else if (override.minimumRelative != null) {
                        alvo = Math.max(0, (int) Math.round(override.minimumRelative * area));
                    }
                    if (alvo <= 0) {
                        continue;
                    }
                    int atual = contarEstruturasNoBioma(rule.structure, biome);
                    if (atual >= alvo) {
                        continue;
                    }
                    int faltam = alvo - atual;
                    int colocadas = 0;
                    int tentativas = 0;
                    while (colocadas < faltam && tentativas < faltam * 80L) {
                        tentativas++;
                        int x = boundedRandomInt(1, width - 1, rules.seed + biome.ordinal() * 1_000_000L + rule.structure.ordinal() * 70_000L + tentativas * 31L);
                        int y = boundedRandomInt(1, height - 1, rules.seed + biome.ordinal() * 1_000_000L + rule.structure.ordinal() * 70_000L + tentativas * 47L);
                        int idx = index(x, y);
                        if ((naturalMap[idx] & 0xFF) != NaturalStructure.NONE.ordinal()) {
                            continue;
                        }
                        if ((biomeMap[idx] & 0xFF) != biome.ordinal()) {
                            continue;
                        }
                        if (!rule.allows(biome)) {
                            continue;
                        }
                        if (adjustChance(rule, biome, x, y) <= 0.0) {
                            continue;
                        }
                        if (nearPoi(x, y, rules.naturalBlockNearPoiRadius)) {
                            continue;
                        }
                        naturalMap[idx] = (byte) rule.structure.ordinal();
                        naturalCounts[rule.structure.ordinal()]++;
                        colocadas++;
                    }
                }
            }
        }

        private int contarEstruturasNoBioma(NaturalStructure structure, Biome biome) {
            int total = 0;
            int structureOrd = structure.ordinal();
            int biomeOrd = biome.ordinal();
            for (int i = 0; i < area; i++) {
                if ((biomeMap[i] & 0xFF) == biomeOrd && (naturalMap[i] & 0xFF) == structureOrd) {
                    total++;
                }
            }
            return total;
        }

        private void ensureNaturalMinimums() {
            for (StructureRule rule : rules.structureRules) {
                int current = naturalCounts[rule.structure.ordinal()];
                int targetMinimum = rules.resolveMinimum(rule, Biome.FIELD, area);
                if (current >= targetMinimum) {
                    continue;
                }
                int missing = targetMinimum - current;
                if (missing <= 0) {
                    continue;
                }
                System.out.println("  reforcando estrutura " + rule.structure + " -> faltam " + missing);
                int placed = 0;
                int attempts = 0;
                while (placed < missing && attempts < missing * 40L) {
                    attempts++;
                    int x = boundedRandomInt(1, width - 1, rules.seed + rule.structure.ordinal() * 100_000L + attempts * 29L);
                    int y = boundedRandomInt(1, height - 1, rules.seed + rule.structure.ordinal() * 100_000L + attempts * 37L);
                    int idx = index(x, y);
                    if ((naturalMap[idx] & 0xFF) != NaturalStructure.NONE.ordinal()) {
                        continue;
                    }
                    Biome biome = Biome.values()[biomeMap[idx] & 0xFF];
                    if (!rule.allows(biome)) {
                        continue;
                    }
                    if (!isLandBiome(biome) || nearPoi(x, y, rules.naturalBlockNearPoiRadius)) {
                        continue;
                    }
                    naturalMap[idx] = (byte) rule.structure.ordinal();
                    naturalCounts[rule.structure.ordinal()]++;
                    placed++;
                }
                System.out.println("    colocadas: " + placed);
            }
        }

        private void placePois() {
            pois.clear();
            placePoiType(PoiType.VILLAGE, rules.villageCount, rules.villageDistance);
            placePoiType(PoiType.GYM, rules.gymCount, rules.gymDistance);
            placePoiType(PoiType.DUNGEON, rules.dungeonCount, rules.dungeonDistance);
        }

        private void placePoiType(PoiType type, int target, int minDistance) {
            int placed = 0;
            int attempts = 0;
            while (placed < target && attempts < target * 40_000) {
                attempts++;
                int x = boundedRandomInt(140, width - 140, rules.seed + type.ordinal() * 10_000_000L + attempts * 53L);
                int y = boundedRandomInt(140, height - 140, rules.seed + type.ordinal() * 10_000_000L + attempts * 67L);
                if (!canPlacePoi(type, x, y, minDistance)) {
                    continue;
                }
                pois.add(new Poi(x, y, type));
                placed++;
            }
            System.out.println("  " + type + ": " + placed + " / " + target + " (tentativas: " + attempts + ")");
        }

        private boolean canPlacePoi(PoiType type, int x, int y, int minDistance) {
            int idx = index(x, y);
            Biome biome = Biome.values()[biomeMap[idx] & 0xFF];
            if (!isLandBiome(biome)) {
                return false;
            }
            if (nearWater(x, y, type == PoiType.VILLAGE ? 3 : 5)) {
                if (type != PoiType.VILLAGE) {
                    return false;
                }
            }
            if (nearWater(x, y, 1) && type != PoiType.VILLAGE) {
                return false;
            }
            if (!preferredBiomeForPoi(type, biome)) {
                return false;
            }
            for (Poi poi : pois) {
                if (distanceSquared(x, y, poi.x, poi.y) < (long) minDistance * minDistance) {
                    return false;
                }
            }
            return true;
        }

        private boolean preferredBiomeForPoi(PoiType type, Biome biome) {
            return switch (type) {
                case VILLAGE -> biome == Biome.FIELD || biome == Biome.FOREST || biome == Biome.DESERT;
                case GYM -> biome != Biome.SHALLOW_WATER && biome != Biome.OCEAN;
                case DUNGEON -> biome == Biome.FOREST || biome == Biome.SNOW || biome == Biome.MAGIC || biome == Biome.VOLCANIC || biome == Biome.SWAMP;
            };
        }

        private void renderBaseWorld(File file) throws IOException {
            BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
            int[] buffer = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();
            for (int i = 0; i < area; i++) {
                buffer[i] = tileColor(Tile.values()[tileMap[i] & 0xFF]);
            }
            ImageIO.write(image, "png", file);
            image.flush();
            System.gc();
        }

        private void renderNaturalStructures(File file) throws IOException {
            BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
            int[] buffer = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();
            for (int i = 0; i < area; i++) {
                buffer[i] = tileColor(Tile.values()[tileMap[i] & 0xFF]);
            }
            for (int i = 0; i < area; i++) {
                NaturalStructure structure = NaturalStructure.values()[naturalMap[i] & 0xFF];
                if (structure != NaturalStructure.NONE) {
                    buffer[i] = naturalColor(structure);
                }
            }
            ImageIO.write(image, "png", file);
            image.flush();
            System.gc();
        }

        private void renderPois(File file) throws IOException {
            BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
            int[] buffer = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();
            for (int i = 0; i < area; i++) {
                buffer[i] = tileColor(Tile.values()[tileMap[i] & 0xFF]);
            }
            for (Poi poi : pois) {
                drawPoint(buffer, poi.x, poi.y, 4, poiColor(poi.type));
            }
            ImageIO.write(image, "png", file);
            image.flush();
            System.gc();
        }

        private void drawPoint(int[] buffer, int cx, int cy, int radius, int color) {
            for (int dy = -radius; dy <= radius; dy++) {
                int y = cy + dy;
                if (y < 0 || y >= height) {
                    continue;
                }
                for (int dx = -radius; dx <= radius; dx++) {
                    int x = cx + dx;
                    if (x < 0 || x >= width) {
                        continue;
                    }
                    if (dx * dx + dy * dy <= radius * radius) {
                        buffer[index(x, y)] = color;
                    }
                }
            }
        }

        private NaturalStructure chooseNaturalStructure(Biome biome, int x, int y, long localSeed) {
            double roll = random01(localSeed);
            double acc = 0.0;
            NaturalStructure best = NaturalStructure.NONE;
            for (StructureRule rule : rules.structureRules) {
                if (!rule.allows(biome)) {
                    continue;
                }
                double chance = adjustChance(rule, biome, x, y);
                acc += chance;
                if (roll < acc) {
                    best = rule.structure;
                    break;
                }
            }
            return best;
        }

        private double adjustChance(StructureRule rule, Biome biome, int x, int y) {
            Rules.BiomeStructureOverride override = rules.structureOverride(biome, rule.structure);
            double chance = override != null && override.chancePerTile != null ? override.chancePerTile : rule.chancePerTile;

            if (override != null) {
                if (override.chanceMultiplier != null) {
                    chance *= override.chanceMultiplier;
                }
                if (override.requireNearWaterRadius != null && !nearWater(x, y, override.requireNearWaterRadius)) {
                    return 0.0;
                }
                if (override.blockNearWaterRadius != null && nearWater(x, y, override.blockNearWaterRadius)) {
                    return 0.0;
                }
                if (override.blockNearPoiRadius != null && nearPoi(x, y, override.blockNearPoiRadius)) {
                    return 0.0;
                }
                double h = elevation(x, y);
                if (override.minHeight != null && h < override.minHeight) {
                    return 0.0;
                }
                if (override.maxHeight != null && h > override.maxHeight) {
                    return 0.0;
                }
                double m = moisture(x, y);
                if (override.minMoisture != null && m < override.minMoisture) {
                    return 0.0;
                }
                if (override.maxMoisture != null && m > override.maxMoisture) {
                    return 0.0;
                }
            }

            switch (rule.structure) {
                case TREE -> {
                    if (biome == Biome.FOREST) chance *= 2.3;
                    if (biome == Biome.SWAMP) chance *= 1.3;
                }
                case BUSH -> {
                    if (biome == Biome.FIELD) chance *= 1.3;
                    if (biome == Biome.MAGIC) chance *= 1.2;
                }
                case ROCK -> {
                    double h = elevation(x, y);
                    chance *= 0.8 + h * 0.8;
                }
                case GOLD, COPPER -> {
                    double h = elevation(x, y);
                    chance *= 0.6 + h * 0.9;
                }
                case PALM -> {
                    if (nearWater(x, y, rules.naturalBoostPalmNearWaterRadius)) chance *= 1.8;
                }
                case PINE -> chance *= 1.4;
                case AMETHYST, DIAMOND, RUBY, EMERALD -> chance *= 1.25;
                case LAVA_POOL -> chance *= 1.4;
                default -> {
                }
            }
            return chance;
        }

        private boolean isLakeCandidate(double elevation, double moisture, int x, int y) {
            if (elevation < rules.seaLevel + rules.lakeElevationOffsetFromSeaLevel && moisture > rules.lakeMinMoisture) {
                double lakeNoise = fbm(x, y, rules.lakeNoiseOctaves, rules.lakeNoisePersistence, rules.lakeNoiseLacunarity, rules.lakeNoiseScale, rules.lakeNoiseSeedOffset);
                return lakeNoise > rules.lakeNoiseThreshold && !nearBorder(x, y, rules.lakeBorderBlockDistance);
            }
            return false;
        }

        private void updateCoastsAndBeaches() {
            for (int y = 1; y < height - 1; y++) {
                for (int x = 1; x < width - 1; x++) {
                    int idx = index(x, y);
                    Biome biome = Biome.values()[biomeMap[idx] & 0xFF];
                    if (!isLandBiome(biome)) {
                        continue;
                    }
                    if (nearWater(x, y, rules.waterDetectionRadiusForBeach)) {
                        tileMap[idx] = (byte) Tile.BEACH_SAND.ordinal();
                    } else {
                        tileMap[idx] = (byte) tileForBiome(biome).ordinal();
                    }
                }
            }
        }

        private void updateShallowWaterNearLand() {
            for (int y = 1; y < height - 1; y++) {
                for (int x = 1; x < width - 1; x++) {
                    int idx = index(x, y);
                    Tile tile = Tile.values()[tileMap[idx] & 0xFF];
                    if (tile == Tile.WATER_DEEP && nearLand(x, y, rules.shallowWaterNearLandRadius)) {
                        tileMap[idx] = (byte) Tile.WATER_SHALLOW.ordinal();
                        biomeCounts[Biome.OCEAN.ordinal()]--;
                        biomeCounts[Biome.SHALLOW_WATER.ordinal()]++;
                        biomeMap[idx] = (byte) Biome.SHALLOW_WATER.ordinal();
                    }
                }
            }
        }

        private void paintCircleAsShallowWater(int cx, int cy, int radius) {
            for (int dy = -radius; dy <= radius; dy++) {
                int y = cy + dy;
                if (y <= 0 || y >= height - 1) {
                    continue;
                }
                for (int dx = -radius; dx <= radius; dx++) {
                    int x = cx + dx;
                    if (x <= 0 || x >= width - 1) {
                        continue;
                    }
                    if (dx * dx + dy * dy > radius * radius) {
                        continue;
                    }
                    int idx = index(x, y);
                    Biome old = Biome.values()[biomeMap[idx] & 0xFF];
                    biomeCounts[old.ordinal()]--;
                    biomeMap[idx] = (byte) Biome.SHALLOW_WATER.ordinal();
                    tileMap[idx] = (byte) Tile.WATER_SHALLOW.ordinal();
                    biomeCounts[Biome.SHALLOW_WATER.ordinal()]++;
                    naturalMap[idx] = (byte) NaturalStructure.NONE.ordinal();
                }
            }
        }

        private boolean nearBorder(int x, int y, int dist) {
            return x < dist || y < dist || x >= width - dist || y >= height - dist;
        }

        private boolean hardBorder(int x, int y) {
            return x < rules.hardOceanBorder || y < rules.hardOceanBorder || x >= width - rules.hardOceanBorder || y >= height - rules.hardOceanBorder;
        }

        private double edgeWaterPenalty(int x, int y) {
            int min = Math.min(Math.min(x, width - 1 - x), Math.min(y, height - 1 - y));
            if (min >= rules.softOceanBorder) {
                return 0.0;
            }
            double t = 1.0 - (double) min / rules.softOceanBorder;
            return t * t * rules.edgeWaterPenaltyStrength;
        }

        private boolean nearWater(int x, int y, int radius) {
            for (int dy = -radius; dy <= radius; dy++) {
                int ny = y + dy;
                if (ny < 0 || ny >= height) {
                    continue;
                }
                for (int dx = -radius; dx <= radius; dx++) {
                    int nx = x + dx;
                    if (nx < 0 || nx >= width) {
                        continue;
                    }
                    Biome biome = Biome.values()[biomeMap[index(nx, ny)] & 0xFF];
                    if (biome == Biome.OCEAN || biome == Biome.SHALLOW_WATER) {
                        return true;
                    }
                }
            }
            return false;
        }

        private boolean nearOcean(int x, int y, int radius) {
            for (int dy = -radius; dy <= radius; dy++) {
                int ny = y + dy;
                if (ny < 0 || ny >= height) {
                    continue;
                }
                for (int dx = -radius; dx <= radius; dx++) {
                    int nx = x + dx;
                    if (nx < 0 || nx >= width) {
                        continue;
                    }
                    Biome biome = Biome.values()[biomeMap[index(nx, ny)] & 0xFF];
                    if (biome == Biome.OCEAN) {
                        return true;
                    }
                }
            }
            return false;
        }

        private boolean nearLand(int x, int y, int radius) {
            for (int dy = -radius; dy <= radius; dy++) {
                int ny = y + dy;
                if (ny < 0 || ny >= height) {
                    continue;
                }
                for (int dx = -radius; dx <= radius; dx++) {
                    int nx = x + dx;
                    if (nx < 0 || nx >= width) {
                        continue;
                    }
                    Biome biome = Biome.values()[biomeMap[index(nx, ny)] & 0xFF];
                    if (isLandBiome(biome)) {
                        return true;
                    }
                }
            }
            return false;
        }

        private boolean nearPoi(int x, int y, int radius) {
            long rr = (long) radius * radius;
            for (Poi poi : pois) {
                if (distanceSquared(x, y, poi.x, poi.y) <= rr) {
                    return true;
                }
            }
            return false;
        }

        private double elevation(int x, int y) {
            double continents = fbm(x, y, 5, 0.50, 2.0, 1200.0, 11L);
            double detail = fbm(x, y, 4, 0.55, 2.0, 260.0, 31L);
            double ridges = ridgeFbm(x, y, 4, 0.50, 2.0, 340.0, 53L);
            return clamp01(continents * 0.62 + detail * 0.20 + ridges * 0.18);
        }

        private double moisture(int x, int y) {
            double a = fbm(x, y, 4, 0.56, 2.0, 520.0, 101L);
            double b = fbm(x, y, 3, 0.55, 2.0, 170.0, 103L);
            return clamp01(a * 0.72 + b * 0.28);
        }

        private double temperature(int x, int y) {
            double latitude = 1.0 - Math.abs((y / (double) (height - 1)) * 2.0 - 1.0);
            double base = 0.12 + latitude * 0.78;
            double noise = fbm(x, y, 4, 0.55, 2.0, 420.0, 151L);
            return clamp01(base * 0.72 + noise * 0.28);
        }

        private double magic(int x, int y) {
            double a = fbm(x, y, 5, 0.58, 2.0, 450.0, 201L);
            double b = ridgeFbm(x, y, 3, 0.55, 2.0, 180.0, 203L);
            return clamp01(a * 0.78 + b * 0.22);
        }

        private double volcanic(int x, int y) {
            double a = ridgeFbm(x, y, 5, 0.57, 2.0, 390.0, 251L);
            double b = fbm(x, y, 3, 0.60, 2.0, 140.0, 257L);
            return clamp01(a * 0.80 + b * 0.20);
        }

        private double swamp(int x, int y) {
            double a = fbm(x, y, 4, 0.58, 2.0, 360.0, 301L);
            double b = fbm(x, y, 3, 0.55, 2.0, 110.0, 307L);
            return clamp01(a * 0.65 + b * 0.35);
        }

        private double fbm(int x, int y, int octaves, double gain, double lacunarity, double baseScale, long seedOffset) {
            double sum = 0.0;
            double amp = 1.0;
            double norm = 0.0;
            double freq = 1.0 / baseScale;
            for (int i = 0; i < octaves; i++) {
                sum += valueNoise(x * freq, y * freq, rules.seed + seedOffset + i * 9973L) * amp;
                norm += amp;
                amp *= gain;
                freq *= lacunarity;
            }
            return clamp01(sum / norm);
        }

        private double ridgeFbm(int x, int y, int octaves, double gain, double lacunarity, double baseScale, long seedOffset) {
            double sum = 0.0;
            double amp = 1.0;
            double norm = 0.0;
            double freq = 1.0 / baseScale;
            for (int i = 0; i < octaves; i++) {
                double n = valueNoise(x * freq, y * freq, rules.seed + seedOffset + i * 1237L);
                n = 1.0 - Math.abs(2.0 * n - 1.0);
                sum += n * amp;
                norm += amp;
                amp *= gain;
                freq *= lacunarity;
            }
            return clamp01(sum / norm);
        }

        private double valueNoise(double x, double y, long seed) {
            int x0 = fastFloor(x);
            int y0 = fastFloor(y);
            int x1 = x0 + 1;
            int y1 = y0 + 1;

            double tx = x - x0;
            double ty = y - y0;

            double sx = smoothstep(tx);
            double sy = smoothstep(ty);

            double n00 = hashToUnit(seed, x0, y0);
            double n10 = hashToUnit(seed, x1, y0);
            double n01 = hashToUnit(seed, x0, y1);
            double n11 = hashToUnit(seed, x1, y1);

            double ix0 = lerp(n00, n10, sx);
            double ix1 = lerp(n01, n11, sx);
            return lerp(ix0, ix1, sy);
        }

        private double hashToUnit(long seed, int x, int y) {
            long h = seed;
            h ^= 0x9E3779B97F4A7C15L * x;
            h ^= 0xC2B2AE3D27D4EB4FL * y;
            h ^= (h >>> 30);
            h *= 0xBF58476D1CE4E5B9L;
            h ^= (h >>> 27);
            h *= 0x94D049BB133111EBL;
            h ^= (h >>> 31);
            long mantissa = (h >>> 11) & ((1L << 53) - 1);
            return mantissa / (double) (1L << 53);
        }

        private long tileSeed(int x, int y, long salt) {
            long h = rules.seed + salt;
            h ^= 0x9E3779B97F4A7C15L * (x + 1L);
            h ^= 0xC2B2AE3D27D4EB4FL * (y + 1L);
            h ^= (h >>> 29);
            h *= 0x165667919E3779F9L;
            h ^= (h >>> 32);
            return h;
        }

        private double random01(long seed) {
            seed ^= (seed >>> 30);
            seed *= 0xBF58476D1CE4E5B9L;
            seed ^= (seed >>> 27);
            seed *= 0x94D049BB133111EBL;
            seed ^= (seed >>> 31);
            long mantissa = (seed >>> 11) & ((1L << 53) - 1);
            return mantissa / (double) (1L << 53);
        }

        private int boundedRandomInt(int minInclusive, int maxExclusive, long seed) {
            double r = random01(seed);
            return minInclusive + (int) (r * (maxExclusive - minInclusive));
        }

        private Tile tileForBiome(Biome biome) {
            return switch (biome) {
                case FIELD -> Tile.FIELD_GRASS;
                case FOREST -> Tile.FOREST_GRASS;
                case DESERT -> Tile.DESERT_SAND;
                case SNOW -> Tile.SNOW;
                case MAGIC -> Tile.MAGIC_SOIL;
                case VOLCANIC -> Tile.VOLCANIC_ROCK;
                case SWAMP -> Tile.DEAD_SOIL;
                case OCEAN -> Tile.WATER_DEEP;
                case SHALLOW_WATER -> Tile.WATER_SHALLOW;
            };
        }

        private boolean isLandBiome(Biome biome) {
            return biome != Biome.OCEAN && biome != Biome.SHALLOW_WATER;
        }

        private int tileColor(Tile tile) {
            return switch (tile) {
                case FIELD_GRASS -> rgb(110, 186, 72);
                case FOREST_GRASS -> rgb(48, 126, 54);
                case BEACH_SAND -> rgb(228, 214, 149);
                case DESERT_SAND -> rgb(218, 188, 100);
                case SNOW -> rgb(235, 242, 248);
                case MAGIC_SOIL -> rgb(138, 72, 192);
                case VOLCANIC_ROCK -> rgb(112, 74, 44);
                case DEAD_SOIL -> rgb(132, 132, 132);
                case WATER_SHALLOW -> rgb(95, 176, 232);
                case WATER_DEEP -> rgb(18, 74, 156);
            };
        }

        private int naturalColor(NaturalStructure structure) {
            return switch (structure) {
                case TREE -> rgb(18, 94, 28);
                case ROCK -> rgb(98, 98, 98);
                case BUSH -> rgb(60, 152, 62);
                case GOLD -> rgb(232, 196, 26);
                case AMETHYST -> rgb(185, 116, 255);
                case DIAMOND -> rgb(112, 245, 255);
                case RUBY -> rgb(220, 36, 62);
                case EMERALD -> rgb(36, 208, 82);
                case PALM -> rgb(42, 120, 46);
                case PINE -> rgb(20, 74, 34);
                case COPPER -> rgb(197, 112, 70);
                case LAVA_POOL -> rgb(240, 88, 20);
                case NONE -> rgb(0, 0, 0);
            };
        }

        private int poiColor(PoiType type) {
            return switch (type) {
                case GYM -> rgb(40, 120, 255);
                case DUNGEON -> rgb(160, 40, 255);
                case VILLAGE -> rgb(255, 236, 80);
            };
        }

        private int rgb(int r, int g, int b) {
            return (r << 16) | (g << 8) | b;
        }

        private int index(int x, int y) {
            return y * width + x;
        }

        private long distanceSquared(int x1, int y1, int x2, int y2) {
            long dx = x1 - x2;
            long dy = y1 - y2;
            return dx * dx + dy * dy;
        }

        private int fastFloor(double v) {
            int i = (int) v;
            return v < i ? i - 1 : i;
        }

        private double smoothstep(double t) {
            return t * t * (3.0 - 2.0 * t);
        }

        private double lerp(double a, double b, double t) {
            return a + (b - a) * t;
        }

        private int clamp(int v, int min, int max) {
            return Math.max(min, Math.min(max, v));
        }

        private double clamp01(double v) {
            return Math.max(0.0, Math.min(1.0, v));
        }

        private void printSummary() {
            System.out.println();
            System.out.println("===== RESUMO =====");
            System.out.println("Biomas / agua:");
            for (Biome biome : Biome.values()) {
                System.out.printf("  %-15s %d%n", biome, biomeCounts[biome.ordinal()]);
            }
            System.out.println("Estruturas naturais:");
            for (NaturalStructure structure : NaturalStructure.values()) {
                if (structure == NaturalStructure.NONE) {
                    continue;
                }
                System.out.printf("  %-15s %d%n", structure, naturalCounts[structure.ordinal()]);
            }
            System.out.println("POIs:");
            long gyms = pois.stream().filter(p -> p.type == PoiType.GYM).count();
            long dungeons = pois.stream().filter(p -> p.type == PoiType.DUNGEON).count();
            long villages = pois.stream().filter(p -> p.type == PoiType.VILLAGE).count();
            System.out.println("  GYM      " + gyms);
            System.out.println("  DUNGEON  " + dungeons);
            System.out.println("  VILLAGE  " + villages);
            System.out.println("Saida em: " + new File(rules.outputDirectory).getAbsolutePath());
        }

        private void logTime(String label, long start) {
            long ms = System.currentTimeMillis() - start;
            System.out.printf("%s: %.2f s%n", label, ms / 1000.0);
        }
    }
}
