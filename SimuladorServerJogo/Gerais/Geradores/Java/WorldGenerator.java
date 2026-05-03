
import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class WorldGenerator {
    public static void main(String[] args) throws Exception {
        System.setProperty("java.awt.headless", "true");
        if (args.length < 4) {
            throw new IllegalArgumentException("Uso: java WorldGenerator <seed> <outputDir> <regrasTerreno.toml> <regrasBiomas.toml> [regrasLocalidades.toml]");
        }

        long seed;
        try {
            seed = Long.parseLong(args[0]);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Seed invalida: " + args[0], e);
        }

        TerrainRules terrainRules = TerrainRules.load(Path.of(args[2]));
        BiomeRules biomeRules = BiomeRules.load(Path.of(args[3]));
        Path localityPath = args.length >= 5
            ? Path.of(args[4])
            : Path.of(args[2]).getParent().resolve("Localidades.toml");
        LocalityRules localityRules = LocalityRules.load(localityPath);
        GeneratorContext generator = new GeneratorContext(seed, args[1], terrainRules, biomeRules, localityRules);
        generator.generate();
    }
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
    LAVA_POOL,
    CACTUS,
    SHELL,
    AQUAMARINE,
    COAL,
    IRON,
    FLOWER,
    JADE,
    PLANT,
    SAPPHIRE,
    TOPAZ,
    TREE_TROMBOSA,
    HOUSE
}

enum PoiType {
    GYM,
    DUNGEON,
    VILLAGE
}

enum ClimateSource {
    NONE,
    TEMPERATURE,
    MOISTURE,
    MAGIC,
    VOLCANIC,
    SWAMP
}

final class Poi {
    final int x;
    final int y;
    final PoiType type;
    final String name;
    final int regionId;

    Poi(int x, int y, PoiType type) {
        this(x, y, type, null, -1);
    }

    Poi(int x, int y, PoiType type, String name, int regionId) {
        this.x = x;
        this.y = y;
        this.type = type;
        this.name = name;
        this.regionId = regionId;
    }
}

final class RegionData {
    final int id;
    final String name;
    final int centerX;
    final int centerY;
    final int color;

    RegionData(int id, String name, int centerX, int centerY, int color) {
        this.id = id;
        this.name = name;
        this.centerX = centerX;
        this.centerY = centerY;
        this.color = color;
    }
}

final class GeneratorContext {
    static final String[] GYM_TYPES = {
        "Normal","Fogo","Agua","Planta","Eletrico","Gelo","Lutador","Venenoso","Terra","Voador",
        "Psiquico","Inseto","Pedra","Fantasma","Dragao","Sombrio","Metal","Fada","Cosmico","Sonoro"
    };

    final long seed;
    final String outputDirectory;
    final TerrainRules terrainRules;
    final BiomeRules biomeRules;
    final LocalityRules localityRules;
    final int width;
    final int height;
    final int area;

    final byte[] biomeMap;
    final byte[] tileMap;
    final byte[] naturalMap;
    final byte[] macroBiomeGrid;
    final int[] biomeCounts;
    final int[] naturalCounts;
    final List<Poi> pois;
    final List<RegionData> regions;
    final List<RouteData> routes;

    final int macroGridWidth;
    final int macroGridHeight;
    final int macroCellWidth;
    final int macroCellHeight;

    int spawnChunkX = -1;
    int spawnChunkY = -1;
    int spawnX = -1;
    int spawnY = -1;

    final GeradorBiomas geradorBiomas;
    final GeradorTerreno geradorTerreno;
    final GeradorLocalidades geradorLocalidades;
    final GeradorRotas geradorRotas;
    final GeradorObjetos geradorObjetos;
    final GeradorImagens geradorImagens;

    GeneratorContext(long seed, String outputDirectory, TerrainRules terrainRules, BiomeRules biomeRules, LocalityRules localityRules) {
        this.seed = seed;
        this.outputDirectory = outputDirectory;
        this.terrainRules = terrainRules;
        this.biomeRules = biomeRules;
        this.localityRules = localityRules;
        this.width = terrainRules.width;
        this.height = terrainRules.height;
        this.area = width * height;
        this.biomeMap = new byte[area];
        this.tileMap = new byte[area];
        this.naturalMap = new byte[area];
        this.biomeCounts = new int[Biome.values().length];
        this.naturalCounts = new int[NaturalStructure.values().length];
        this.pois = new ArrayList<>();
        this.regions = new ArrayList<>();
        this.routes = new ArrayList<>();
        this.macroGridWidth = Math.max(1, biomeRules.macroGridWidth);
        this.macroGridHeight = Math.max(1, biomeRules.macroGridHeight);
        this.macroCellWidth = Math.max(1, (int) Math.ceil(width / (double) macroGridWidth));
        this.macroCellHeight = Math.max(1, (int) Math.ceil(height / (double) macroGridHeight));
        this.macroBiomeGrid = new byte[macroGridWidth * macroGridHeight];
        this.geradorBiomas = new GeradorBiomas(this);
        this.geradorTerreno = new GeradorTerreno(this);
        this.geradorLocalidades = new GeradorLocalidades(this);
        this.geradorRotas = new GeradorRotas(this);
        this.geradorObjetos = new GeradorObjetos(this);
        this.geradorImagens = new GeradorImagens(this);
    }

    void generate() throws IOException {
        long t0 = System.currentTimeMillis();
        File dir = new File(outputDirectory);
        if (!dir.exists() && !dir.mkdirs()) {
            throw new IOException("Nao foi possivel criar a pasta de saida: " + dir.getAbsolutePath());
        }

        System.out.println("Seed: " + seed);
        System.out.println("Gerando terreno base...");
        geradorTerreno.generateBaseTerrain();
        logTime("Terreno base", t0);

        long t1 = System.currentTimeMillis();
        System.out.println("Gerando rios...");
        geradorTerreno.generateRivers();
        geradorTerreno.finalizeWaters();
        logTime("Rios", t1);

        long t2 = System.currentTimeMillis();
        System.out.println("Gerando localidades, vilas e ginasios...");
        geradorLocalidades.generate();
        logTime("Localidades", t2);

        long t3 = System.currentTimeMillis();
        System.out.println("Posicionando estruturas naturais...");
        geradorObjetos.placeNaturalStructures();
        logTime("Estruturas naturais", t3);

        long t4 = System.currentTimeMillis();
        System.out.println("Gerando rotas entre vilas...");
        geradorRotas.generate();
        logTime("Rotas", t4);

        long t5 = System.currentTimeMillis();
        System.out.println("Posicionando dungeons...");
        geradorObjetos.placeDungeons();
        logTime("Dungeons", t5);

        long t6 = System.currentTimeMillis();
        findSpawnChunk();
        System.out.println("Exportando mundo em chunks...");
        writeWorldChunks(dir);
        logTime("Export", t6);

        long t7 = System.currentTimeMillis();
        System.out.println("Gerando fotos do mundo...");
        geradorImagens.gerarImagens(dir);
        logTime("Fotos do mundo", t7);

        printSummary();
        logTime("Tempo total", t0);
    }

    int index(int x, int y) {
        return y * width + x;
    }

    int macroIndex(int mx, int my) {
        return my * macroGridWidth + mx;
    }

    boolean isLandBiome(Biome biome) {
        return biome != Biome.OCEAN && biome != Biome.SHALLOW_WATER;
    }

    long distanceSquared(int x1, int y1, int x2, int y2) {
        long dx = x1 - x2;
        long dy = y1 - y2;
        return dx * dx + dy * dy;
    }

    int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    double clamp01(double value) {
        return Math.max(0.0, Math.min(1.0, value));
    }

    int fastFloor(double value) {
        int i = (int) value;
        return value < i ? i - 1 : i;
    }

    double smoothstep(double t) {
        return t * t * (3.0 - 2.0 * t);
    }

    double lerp(double a, double b, double t) {
        return a + (b - a) * t;
    }

    double valueNoise(double x, double y, long seedValue) {
        int x0 = fastFloor(x);
        int y0 = fastFloor(y);
        int x1 = x0 + 1;
        int y1 = y0 + 1;
        double tx = x - x0;
        double ty = y - y0;
        double sx = smoothstep(tx);
        double sy = smoothstep(ty);

        double n00 = hashToUnit(seedValue, x0, y0);
        double n10 = hashToUnit(seedValue, x1, y0);
        double n01 = hashToUnit(seedValue, x0, y1);
        double n11 = hashToUnit(seedValue, x1, y1);

        double ix0 = lerp(n00, n10, sx);
        double ix1 = lerp(n01, n11, sx);
        return lerp(ix0, ix1, sy);
    }

    double hashToUnit(long seedValue, int x, int y) {
        long h = seedValue;
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

    double sampleNoise(NoiseLayerConfig config, int x, int y) {
        double sum = 0.0;
        double amplitude = 1.0;
        double norm = 0.0;
        double frequency = 1.0 / config.scale;
        for (int i = 0; i < config.octaves; i++) {
            double n = valueNoise(x * frequency, y * frequency, seed + config.seedOffset + i * 7919L);
            if (config.ridge) {
                n = 1.0 - Math.abs(2.0 * n - 1.0);
            }
            sum += n * amplitude;
            norm += amplitude;
            amplitude *= config.persistence;
            frequency *= config.lacunarity;
        }
        return clamp01(sum / norm);
    }

    double elevation(int x, int y) {
        double continents = sampleNoise(terrainRules.elevationContinents, x, y) * terrainRules.elevationContinents.weight;
        double detail = sampleNoise(terrainRules.elevationDetail, x, y) * terrainRules.elevationDetail.weight;
        double ridges = sampleNoise(terrainRules.elevationRidges, x, y) * terrainRules.elevationRidges.weight;
        return clamp01(continents + detail + ridges);
    }

    double moisture(int x, int y) {
        double large = sampleNoise(terrainRules.moistureLarge, x, y) * terrainRules.moistureLarge.weight;
        double detail = sampleNoise(terrainRules.moistureDetail, x, y) * terrainRules.moistureDetail.weight;
        return clamp01(large + detail);
    }

    boolean nearWater(int x, int y, int radius) {
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
                int idx = index(nx, ny);
                Tile tile = Tile.values()[tileMap[idx] & 0xFF];
                if (tile == Tile.WATER_DEEP || tile == Tile.WATER_SHALLOW) {
                    return true;
                }
            }
        }
        return false;
    }

    boolean nearOcean(int x, int y, int radius) {
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
                if (Biome.values()[biomeMap[index(nx, ny)] & 0xFF] == Biome.OCEAN) {
                    return true;
                }
            }
        }
        return false;
    }

    boolean nearLand(int x, int y, int radius) {
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
                if (isLandBiome(Biome.values()[biomeMap[index(nx, ny)] & 0xFF])) {
                    return true;
                }
            }
        }
        return false;
    }

    boolean nearPoi(int x, int y, int radius) {
        long rr = (long) radius * radius;
        for (Poi poi : pois) {
            if (distanceSquared(x, y, poi.x, poi.y) <= rr) {
                return true;
            }
        }
        return false;
    }

    long tileSeed(int x, int y, long salt) {
        long h = seed + salt;
        h ^= 0x9E3779B97F4A7C15L * (x + 1L);
        h ^= 0xC2B2AE3D27D4EB4FL * (y + 1L);
        h ^= (h >>> 29);
        h *= 0x165667919E3779F9L;
        h ^= (h >>> 32);
        return h;
    }

    double random01(long seedValue) {
        seedValue ^= (seedValue >>> 30);
        seedValue *= 0xBF58476D1CE4E5B9L;
        seedValue ^= (seedValue >>> 27);
        seedValue *= 0x94D049BB133111EBL;
        seedValue ^= (seedValue >>> 31);
        long mantissa = (seedValue >>> 11) & ((1L << 53) - 1);
        return mantissa / (double) (1L << 53);
    }

    int boundedRandomInt(int minInclusive, int maxExclusive, long seedValue) {
        if (maxExclusive <= minInclusive) {
            return minInclusive;
        }
        return minInclusive + (int) (random01(seedValue) * (maxExclusive - minInclusive));
    }

    RegionData nearestRegion(int x, int y) {
        return geradorLocalidades.nearestRegion(x, y);
    }

    boolean isReservedForNaturalStructure(int x, int y) {
        return geradorLocalidades.isReservedForNaturalStructure(x, y)
            || nearPoi(x, y, biomeRules.objectBlockNearPoiRadius);
    }

    void recountBiomes() {
        Arrays.fill(biomeCounts, 0);
        for (int i = 0; i < area; i++) {
            biomeCounts[biomeMap[i] & 0xFF]++;
        }
    }

    void recountNaturals() {
        Arrays.fill(naturalCounts, 0);
        for (int i = 0; i < area; i++) {
            naturalCounts[naturalMap[i] & 0xFF]++;
        }
    }

    void findSpawnChunk() {
        int chunkSize = terrainRules.chunkSize;
        int chunksX = (int) Math.ceil(width / (double) chunkSize);
        int chunksY = (int) Math.ceil(height / (double) chunkSize);
        int centerCx = chunksX / 2;
        int centerCy = chunksY / 2;

        int bestScore = Integer.MIN_VALUE;
        int bestCx = centerCx;
        int bestCy = centerCy;

        for (int radius = 0; radius <= Math.max(chunksX, chunksY); radius++) {
            for (int cy = Math.max(0, centerCy - radius); cy <= Math.min(chunksY - 1, centerCy + radius); cy++) {
                for (int cx = Math.max(0, centerCx - radius); cx <= Math.min(chunksX - 1, centerCx + radius); cx++) {
                    if (Math.max(Math.abs(cx - centerCx), Math.abs(cy - centerCy)) != radius) {
                        continue;
                    }
                    int score = spawnChunkScore(cx, cy, chunkSize);
                    if (score > bestScore) {
                        bestScore = score;
                        bestCx = cx;
                        bestCy = cy;
                    }
                    if (score == chunkSize * chunkSize * 4) {
                        setSpawn(bestCx, bestCy, chunkSize);
                        System.out.println("Spawn encontrado no chunk (" + spawnChunkX + "," + spawnChunkY + ") em bloco (" + spawnX + "," + spawnY + ")");
                        return;
                    }
                }
            }
        }

        setSpawn(bestCx, bestCy, chunkSize);
        System.out.println("[WARN] Nenhum chunk perfeito encontrado para spawn, usando melhor candidato em (" + spawnChunkX + "," + spawnChunkY + ")");
    }

    private void setSpawn(int cx, int cy, int chunkSize) {
        spawnChunkX = cx;
        spawnChunkY = cy;
        spawnX = Math.min(width - 1, cx * chunkSize + chunkSize / 2);
        spawnY = Math.min(height - 1, cy * chunkSize + chunkSize / 2);
    }

    int spawnChunkScore(int cx, int cy, int chunkSize) {
        int x0 = cx * chunkSize;
        int y0 = cy * chunkSize;
        int x1 = Math.min(width, x0 + chunkSize);
        int y1 = Math.min(height, y0 + chunkSize);

        boolean hasPoi = false;
        for (Poi poi : pois) {
            if (poi.x >= x0 && poi.x < x1 && poi.y >= y0 && poi.y < y1) {
                hasPoi = true;
                break;
            }
        }

        int score = 0;
        for (int y = y0; y < y1; y++) {
            for (int x = x0; x < x1; x++) {
                int idx = index(x, y);
                Biome biome = Biome.values()[biomeMap[idx] & 0xFF];
                Tile tile = Tile.values()[tileMap[idx] & 0xFF];
                NaturalStructure structure = NaturalStructure.values()[naturalMap[idx] & 0xFF];
                if (biome == terrainRules.spawnRequiredBiome) {
                    score += 2;
                } else if (isLandBiome(biome)) {
                    score += 1;
                }
                if (tile == geradorBiomas.baseTileFor(terrainRules.spawnRequiredBiome)) {
                    score += 1;
                }
                if (!terrainRules.spawnRequiresNoObjects || structure == NaturalStructure.NONE) {
                    score += 1;
                }
            }
        }

        if (terrainRules.spawnRequiresNoPois && hasPoi) {
            score -= chunkSize * chunkSize * 4;
        }
        return score;
    }

    void writeWorldChunks(File outputDir) throws IOException {
        int chunkSize = terrainRules.chunkSize;
        int chunksX = (int) Math.ceil(width / (double) chunkSize);
        int chunksY = (int) Math.ceil(height / (double) chunkSize);
        int chunksPerFile = terrainRules.chunksPerFile;
        int groupsX = (int) Math.ceil(chunksX / (double) chunksPerFile);
        int groupsY = (int) Math.ceil(chunksY / (double) chunksPerFile);

        File chunksDir = new File(outputDir, "chunks");
        if (!chunksDir.exists() && !chunksDir.mkdirs()) {
            throw new IOException("Nao foi possivel criar a pasta chunks: " + chunksDir.getAbsolutePath());
        }

        writeWorldMeta(new File(outputDir, "world_meta.json"), chunkSize, chunksX, chunksY, chunksPerFile, groupsX, groupsY);

        byte[] structuresMap = buildStructuresGrid();
        int totalFiles = groupsX * groupsY;
        int generated = 0;
        for (int gy = 0; gy < groupsY; gy++) {
            for (int gx = 0; gx < groupsX; gx++) {
                File chunkFile = new File(chunksDir, "chunk_set_" + gx + "_" + gy + ".json");
                writeChunkSetJson(chunkFile, gx, gy, chunksPerFile, chunksX, chunksY, chunkSize, structuresMap);
                generated++;
                System.out.println("[PROGRESSO] ETAPA=CHUNKS ATUAL=" + generated + " TOTAL=" + totalFiles + " MSG=Salvando chunks");
            }
        }
    }

    private void writeWorldMeta(File metaFile, int chunkSize, int chunksX, int chunksY, int chunksPerFile, int groupsX, int groupsY) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(metaFile.toPath(), StandardCharsets.UTF_8)) {
            writer.write("{\n");
            writer.write("  \"seed\": " + seed + ",\n");
            writer.write("  \"width\": " + width + ",\n");
            writer.write("  \"height\": " + height + ",\n");
            writer.write("  \"chunk_blocos\": " + chunkSize + ",\n");
            writer.write("  \"chunk_blocos_disco\": " + chunkSize + ",\n");
            writer.write("  \"chunks_x\": " + chunksX + ",\n");
            writer.write("  \"chunks_y\": " + chunksY + ",\n");
            writer.write("  \"chunks_por_arquivo\": " + chunksPerFile + ",\n");
            writer.write("  \"grupos_x\": " + groupsX + ",\n");
            writer.write("  \"grupos_y\": " + groupsY + ",\n");
            writer.write("  \"spawn_chunk_x\": " + spawnChunkX + ",\n");
            writer.write("  \"spawn_chunk_y\": " + spawnChunkY + ",\n");
            writer.write("  \"spawn_x\": " + spawnX + ",\n");
            writer.write("  \"spawn_y\": " + spawnY + ",\n");

            writer.write("  \"regioes\": [\n");
            for (int i = 0; i < regions.size(); i++) {
                RegionData region = regions.get(i);
                int rr = (region.color >> 16) & 0xFF;
                int rg = (region.color >> 8) & 0xFF;
                int rb = region.color & 0xFF;
                writer.write("    {\"id\": " + region.id
                    + ", \"nome\": \"" + escapeJson(region.name) + "\""
                    + ", \"centro\": [" + region.centerX + ", " + region.centerY + "]"
                    + ", \"cor\": [" + rr + ", " + rg + ", " + rb + "]}");
                if (i < regions.size() - 1) {
                    writer.write(",");
                }
                writer.write("\n");
            }
            writer.write("  ],\n");

            List<Poi> villages = new ArrayList<>();
            for (Poi poi : pois) {
                if (poi.type == PoiType.VILLAGE) {
                    villages.add(poi);
                }
            }
            writer.write("  \"vilas\": [\n");
            for (int i = 0; i < villages.size(); i++) {
                Poi poi = villages.get(i);
                writer.write("    {\"nome\": \"" + escapeJson(poi.name == null ? ("Vila" + (i + 1)) : poi.name) + "\""
                    + ", \"regiao_id\": " + poi.regionId
                    + ", \"posicao\": [" + poi.x + ", " + poi.y + "]}");
                if (i < villages.size() - 1) {
                    writer.write(",");
                }
                writer.write("\n");
            }
            writer.write("  ],\n");

            writer.write("  \"rotas\": [\n");
            for (int i = 0; i < routes.size(); i++) {
                RouteData route = routes.get(i);
                writer.write("    {\"id\": " + route.id
                    + ", \"origem\": \"" + escapeJson(route.fromVillage) + "\""
                    + ", \"destino\": \"" + escapeJson(route.toVillage) + "\""
                    + ", \"tipo_origem\": \"" + escapeJson(route.fromType) + "\""
                    + ", \"tipo_destino\": \"" + escapeJson(route.toType) + "\""
                    + ", \"regiao_origem_id\": " + route.fromRegionId
                    + ", \"regiao_destino_id\": " + route.toRegionId
                    + ", \"pontos\": [");
                for (int pointIndex = 0; pointIndex < route.points.size(); pointIndex++) {
                    int[] point = route.points.get(pointIndex);
                    writer.write("[" + point[0] + "," + point[1] + "]");
                    if (pointIndex < route.points.size() - 1) {
                        writer.write(",");
                    }
                }
                writer.write("]}");
                if (i < routes.size() - 1) {
                    writer.write(",");
                }
                writer.write("\n");
            }
            writer.write("  ],\n");

            writer.write("  \"estadios\": [\n");
            int gymIndex = 0;
            int totalGyms = 0;
            for (Poi poi : pois) {
                if (poi.type == PoiType.GYM) {
                    totalGyms++;
                }
            }
            int current = 0;
            for (Poi poi : pois) {
                if (poi.type != PoiType.GYM) {
                    continue;
                }
                String tipo = GYM_TYPES[gymIndex % GYM_TYPES.length];
                String dimensao = "Estadio" + tipo;
                writer.write("    {\"estadio_id\": " + (1900000000 + gymIndex)
                    + ", \"tipo\": \"" + tipo + "\""
                    + ", \"dimensao\": \"" + dimensao + "\""
                    + ", \"regiao_id\": " + poi.regionId
                    + ", \"posicao\": [" + poi.x + ", " + poi.y + "]}");
                current++;
                gymIndex++;
                if (current < totalGyms) {
                    writer.write(",");
                }
                writer.write("\n");
            }
            writer.write("  ],\n");

            writer.write("  \"dungeons\": [\n");
            List<Poi> dungeons = new ArrayList<>();
            for (Poi poi : pois) {
                if (poi.type == PoiType.DUNGEON) {
                    dungeons.add(poi);
                }
            }
            for (int i = 0; i < dungeons.size(); i++) {
                Poi poi = dungeons.get(i);
                String anotado = poi.name == null ? "25,0" : poi.name;
                int dungeonCode = 0;
                int virgula = anotado.indexOf(',');
                if (virgula >= 0 && virgula + 1 < anotado.length()) {
                    try {
                        dungeonCode = Integer.parseInt(anotado.substring(virgula + 1).trim());
                    } catch (NumberFormatException ignored) {}
                }
                writer.write("    {\"id\": \"" + escapeJson(anotado) + "\""
                    + ", \"base_id\": 25"
                    + ", \"dungeon_code\": " + dungeonCode
                    + ", \"regiao_id\": " + poi.regionId
                    + ", \"posicao\": [" + poi.x + ", " + poi.y + "]}");
                if (i < dungeons.size() - 1) {
                    writer.write(",");
                }
                writer.write("\n");
            }
            writer.write("  ]\n");
            writer.write("}\n");
        }
    }

    private String escapeJson(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    byte[] buildStructuresGrid() {
        byte[] grid = Arrays.copyOf(naturalMap, naturalMap.length);
        for (Poi poi : pois) {
            grid[index(poi.x, poi.y)] = (byte) poiCode(poi.type);
        }
        return grid;
    }

    int poiCode(PoiType type) {
        return switch (type) {
            case GYM -> 101;
            case DUNGEON -> 25;
            case VILLAGE -> 103;
        };
    }

    void writeChunkSetJson(File file, int groupX, int groupY, int chunksPerFile, int chunksX, int chunksY, int chunkSize, byte[] structuresMap) throws IOException {
        int chunkStartX = groupX * chunksPerFile;
        int chunkStartY = groupY * chunksPerFile;
        int chunkEndX = Math.min(chunksX, chunkStartX + chunksPerFile);
        int chunkEndY = Math.min(chunksY, chunkStartY + chunksPerFile);

        try (BufferedWriter writer = Files.newBufferedWriter(file.toPath(), StandardCharsets.UTF_8)) {
            writer.write("{\n");
            writer.write("  \"meta\": {\n");
            writer.write("    \"group_x\": " + groupX + ",\n");
            writer.write("    \"group_y\": " + groupY + ",\n");
            writer.write("    \"chunk_start_x\": " + chunkStartX + ",\n");
            writer.write("    \"chunk_start_y\": " + chunkStartY + ",\n");
            writer.write("    \"chunk_end_x\": " + (chunkEndX - 1) + ",\n");
            writer.write("    \"chunk_end_y\": " + (chunkEndY - 1) + ",\n");
            writer.write("    \"chunks_por_arquivo\": " + chunksPerFile + ",\n");
            writer.write("    \"chunk_blocos\": " + chunkSize + ",\n");
            writer.write("    \"world_width\": " + width + ",\n");
            writer.write("    \"world_height\": " + height + ",\n");
            writer.write("    \"seed\": " + seed + "\n");
            writer.write("  },\n");

            writer.write("  \"chunks\": [\n");
            boolean first = true;
            for (int cy = chunkStartY; cy < chunkEndY; cy++) {
                for (int cx = chunkStartX; cx < chunkEndX; cx++) {
                    if (!first) {
                        writer.write(",\n");
                    }
                    writer.write("    {\n");
                    writer.write("      \"chunk_x\": " + cx + ",\n");
                    writer.write("      \"chunk_y\": " + cy + ",\n");
                    writer.write("      \"grid_blocos\": ");
                    writeChunkGridFromMap(writer, tileMap, cx * chunkSize, cy * chunkSize, chunkSize, "      ");
                    writer.write(",\n");
                    writer.write("      \"grid_biomas\": ");
                    writeChunkGridFromMap(writer, biomeMap, cx * chunkSize, cy * chunkSize, chunkSize, "      ");
                    writer.write(",\n");
                    writer.write("      \"grid_estruturas\": ");
                    writeChunkGridFromMap(writer, structuresMap, cx * chunkSize, cy * chunkSize, chunkSize, "      ");
                    writer.write("\n    }");
                    first = false;
                }
            }
            writer.write("\n  ]\n");
            writer.write("}\n");
        }
    }

    void writeChunkGridFromMap(BufferedWriter writer, byte[] map, int x0, int y0, int chunkSize, String indent) throws IOException {
        String rowIndent = indent + "  ";
        writer.write("[\n");
        for (int by = 0; by < chunkSize; by++) {
            int y = y0 + by;
            writer.write(rowIndent + "[");
            for (int bx = 0; bx < chunkSize; bx++) {
                int x = x0 + bx;
                int value = 0;
                if (x >= 0 && y >= 0 && x < width && y < height) {
                    value = map[index(x, y)] & 0xFF;
                }
                writer.write(Integer.toString(value));
                if (bx < chunkSize - 1) {
                    writer.write(",");
                }
            }
            writer.write("]");
            if (by < chunkSize - 1) {
                writer.write(",");
            }
            writer.write("\n");
        }
        writer.write(indent + "]");
    }

    void printSummary() {
        recountBiomes();
        recountNaturals();
        System.out.println();
        System.out.println("===== RESUMO =====");
        System.out.println("Biomas / agua:");
        for (Biome biome : Biome.values()) {
            System.out.printf(Locale.US, "  %-15s %d%n", biome, biomeCounts[biome.ordinal()]);
        }
        System.out.println("Estruturas naturais:");
        for (NaturalStructure structure : NaturalStructure.values()) {
            if (structure == NaturalStructure.NONE) {
                continue;
            }
            System.out.printf(Locale.US, "  %-15s %d%n", structure, naturalCounts[structure.ordinal()]);
        }
        long gyms = pois.stream().filter(p -> p.type == PoiType.GYM).count();
        long dungeons = pois.stream().filter(p -> p.type == PoiType.DUNGEON).count();
        long villages = pois.stream().filter(p -> p.type == PoiType.VILLAGE).count();
        long routesCount = routes.size();
        System.out.println("Regioes: " + regions.size());
        System.out.println("POIs:");
        System.out.println("  GYM      " + gyms);
        System.out.println("  DUNGEON  " + dungeons);
        System.out.println("  VILLAGE  " + villages);
        System.out.println("Rotas: " + routesCount);
        System.out.println("Saida em: " + new File(outputDirectory).getAbsolutePath());
    }

    void logTime(String label, long start) {
        long ms = System.currentTimeMillis() - start;
        System.out.printf(Locale.US, "%s: %.2f s%n", label, ms / 1000.0);
    }
}
