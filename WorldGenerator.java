import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumSet;
import java.util.List;

public class WorldGenerator {

    public static void main(String[] args) throws Exception {
        Rules rules = Rules.defaultRules();
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
        final double weight;
        final double minimumLandPercent;

        BiomeRule(Biome biome, double weight, double minimumLandPercent) {
            this.biome = biome;
            this.weight = weight;
            this.minimumLandPercent = minimumLandPercent;
        }
    }

    static final class Rules {
        int width = 320;
        int height = 320;
        long seed = 20260307L;
        String outputDirectory = ".";
        String outputJsonFilename = "world_grids.json";

        int hardOceanBorder = 12;
        int softOceanBorder = 48;
        double seaLevel = 0.48;
        double shallowWaterBand = 0.032;

        int riverSources = 18;
        int riverMaxLength = 140;
        int riverWidth = 1;
        double riverSourceMinHeight = 0.63;

        int gymCount = 8;
        int dungeonCount = 8;
        int villageCount = 0;
        int gymDistance = 38;
        int dungeonDistance = 34;
        int villageDistance = 40;

        BiomeRule[] biomeRules;
        StructureRule[] structureRules;

        static Rules defaultRules() {
            Rules rules = new Rules();
            rules.biomeRules = new BiomeRule[]{
                    new BiomeRule(Biome.FIELD, 1.00, 0.16),
                    new BiomeRule(Biome.FOREST, 1.00, 0.12),
                    new BiomeRule(Biome.DESERT, 0.75, 0.08),
                    new BiomeRule(Biome.SNOW, 0.65, 0.08),
                    new BiomeRule(Biome.MAGIC, 0.40, 0.05),
                    new BiomeRule(Biome.VOLCANIC, 0.35, 0.04),
                    new BiomeRule(Biome.SWAMP, 0.45, 0.05)
            };

            EnumSet<Biome> land = EnumSet.of(Biome.FIELD, Biome.FOREST, Biome.DESERT, Biome.SNOW, Biome.MAGIC, Biome.VOLCANIC, Biome.SWAMP);
            rules.structureRules = new StructureRule[]{
                    new StructureRule(NaturalStructure.TREE, 0.0160, 400, EnumSet.of(Biome.FIELD, Biome.FOREST, Biome.SWAMP, Biome.MAGIC)),
                    new StructureRule(NaturalStructure.ROCK, 0.0060, 240, land),
                    new StructureRule(NaturalStructure.BUSH, 0.0075, 220, EnumSet.of(Biome.FIELD, Biome.FOREST, Biome.SWAMP, Biome.MAGIC)),
                    new StructureRule(NaturalStructure.GOLD, 0.0011, 60, land),
                    new StructureRule(NaturalStructure.AMETHYST, 0.0026, 50, EnumSet.of(Biome.MAGIC)),
                    new StructureRule(NaturalStructure.DIAMOND, 0.0023, 50, EnumSet.of(Biome.SNOW)),
                    new StructureRule(NaturalStructure.RUBY, 0.0025, 50, EnumSet.of(Biome.VOLCANIC)),
                    new StructureRule(NaturalStructure.EMERALD, 0.0023, 50, EnumSet.of(Biome.DESERT)),
                    new StructureRule(NaturalStructure.PALM, 0.0045, 50, EnumSet.of(Biome.DESERT)),
                    new StructureRule(NaturalStructure.PINE, 0.0058, 50, EnumSet.of(Biome.SNOW)),
                    new StructureRule(NaturalStructure.COPPER, 0.0024, 60, land),
                    new StructureRule(NaturalStructure.LAVA_POOL, 0.0035, 50, EnumSet.of(Biome.VOLCANIC))
            };
            return rules;
        }
    }

    static final class Generator {
        private final Rules rules;
        private final int width;
        private final int height;
        private final int area;

        private final byte[] biomeMap;
        private final byte[] macroBiomeMap;
        private final byte[] tileMap;
        private final byte[] naturalMap;
        private final List<Poi> pois = new ArrayList<>();
        private final int[] biomeCounts = new int[Biome.values().length];
        private final int[] naturalCounts = new int[NaturalStructure.values().length];

        Generator(Rules rules) {
            this.rules = rules;
            this.width = rules.width;
            this.height = rules.height;
            this.area = width * height;
            this.biomeMap = new byte[area];
            this.macroBiomeMap = new byte[area];
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

            long t2 = System.currentTimeMillis();
            System.out.println("Ajustando minimo de biomas...");
            rebalanceBiomesMinimums();
            smoothIsolatedLandBiomes();
            updateCoastsAndBeaches();
            updateShallowWaterNearLand();
            logTime("Ajuste de biomas", t2);

            long t3 = System.currentTimeMillis();
            System.out.println("Posicionando estruturas naturais...");
            placeNaturalStructures();
            ensureNaturalMinimums();
            logTime("Estruturas naturais", t3);

            long t4 = System.currentTimeMillis();
            System.out.println("Posicionando ginasios e dungeons...");
            placePois();
            logTime("POIs", t4);

            long t5 = System.currentTimeMillis();
            System.out.println("Renderizando imagens...");
            renderBaseWorld(new File(dir, "01_blocos_biomas.png"));
            renderNaturalStructures(new File(dir, "02_estruturas_naturais.png"));
            renderPois(new File(dir, "03_pois.png"));
            exportWorldGridsJson(new File(dir, rules.outputJsonFilename));
            logTime("Render", t5);

            printSummary();
            logTime("Tempo total", t0);
        }

        private void generateBaseTerrain() {
            Arrays.fill(naturalMap, (byte) NaturalStructure.NONE.ordinal());
            Arrays.fill(biomeCounts, 0);
            buildMacroBiomeMap();

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
                    double temperature = temperature(x, y);
                    double magic = magic(x, y);
                    double volcanic = volcanic(x, y);
                    double swamp = swamp(x, y);

                    if (elevation < rules.seaLevel - 0.04) {
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

                    Biome macroBiome = Biome.values()[macroBiomeMap[idx] & 0xFF];
                    Biome biome = classifyLandBiome(temperature, moisture, magic, volcanic, swamp, elevation, macroBiome);
                    Tile tile = tileForBiome(biome);
                    biomeMap[idx] = (byte) biome.ordinal();
                    tileMap[idx] = (byte) tile.ordinal();
                    biomeCounts[biome.ordinal()]++;
                }
            }
            updateCoastsAndBeaches();
            updateShallowWaterNearLand();
            smoothIsolatedLandBiomes();
            updateCoastsAndBeaches();
        }

        private void generateRivers() {
            int created = 0;
            int attempts = 0;
            while (created < rules.riverSources && attempts < rules.riverSources * 50) {
                attempts++;
                int x = boundedRandomInt(200, width - 200, rules.seed + 91L * attempts);
                int y = boundedRandomInt(200, height - 200, rules.seed + 131L * attempts);
                int idx = index(x, y);
                if (!isLandBiome(Biome.values()[biomeMap[idx] & 0xFF])) {
                    continue;
                }
                double h = elevation(x, y) - edgeWaterPenalty(x, y);
                if (h < rules.riverSourceMinHeight) {
                    continue;
                }
                if (nearWater(x, y, 8)) {
                    continue;
                }
                carveRiverFrom(x, y);
                created++;
            }
            System.out.println("  fontes de rio criadas: " + created + " / " + rules.riverSources);
        }

        private void buildMacroBiomeMap() {
            for (int y = 0; y < height; y++) {
                for (int x = 0; x < width; x++) {
                    int idx = index(x, y);

                    double latitude = 1.0 - Math.abs((y / (double) (height - 1)) * 2.0 - 1.0);
                    double macroTemperature = clamp01(fbm(x, y, 4, 0.56, 2.0, 2200.0, 811L) * 0.60 + latitude * 0.40);
                    double macroMoisture = fbm(x, y, 4, 0.56, 2.0, 2100.0, 821L);
                    double macroMagic = ridgeFbm(x, y, 3, 0.58, 2.0, 2500.0, 831L);
                    double macroVolcanic = ridgeFbm(x, y, 3, 0.58, 2.0, 2600.0, 841L);
                    double macroSwamp = fbm(x, y, 3, 0.58, 2.0, 1900.0, 851L);

                    Biome macroBiome;
                    if (macroVolcanic > 0.76 && macroTemperature > 0.50) {
                        macroBiome = Biome.VOLCANIC;
                    } else if (macroMagic > 0.80) {
                        macroBiome = Biome.MAGIC;
                    } else if (macroSwamp > 0.66 && macroMoisture > 0.63) {
                        macroBiome = Biome.SWAMP;
                    } else if (macroTemperature < 0.32) {
                        macroBiome = Biome.SNOW;
                    } else if (macroTemperature > 0.72 && macroMoisture < 0.38) {
                        macroBiome = Biome.DESERT;
                    } else if (macroMoisture > 0.58) {
                        macroBiome = Biome.FOREST;
                    } else {
                        macroBiome = Biome.FIELD;
                    }

                    macroBiomeMap[idx] = (byte) macroBiome.ordinal();
                }
            }
        }

        private void carveRiverFrom(int startX, int startY) {
            int x = startX;
            int y = startY;
            int lastX = -1;
            int lastY = -1;

            for (int step = 0; step < rules.riverMaxLength; step++) {
                paintCircleAsShallowWater(x, y, rules.riverWidth);
                if (nearOcean(x, y, 2)) {
                    paintCircleAsShallowWater(x, y, rules.riverWidth + 1);
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
                    paintCircleAsShallowWater(x, y, rules.riverWidth + 1);
                    return;
                }

                lastX = x;
                lastY = y;
                x = bestX;
                y = bestY;
            }
        }

        private void rebalanceBiomesMinimums() {
            int landCount = totalLandCount();
            for (BiomeRule biomeRule : rules.biomeRules) {
                Biome biome = biomeRule.biome;
                int current = biomeCounts[biome.ordinal()];
                int minimum = (int) Math.round(landCount * biomeRule.minimumLandPercent);
                if (current >= minimum) {
                    continue;
                }
                int missing = minimum - current;
                System.out.println("  reforcando bioma " + biome + " -> faltam " + missing + " tiles");
                int filled = 0;
                long localSeed = rules.seed + biome.ordinal() * 1_000_003L;
                int attempts = 0;
                while (filled < missing && attempts < missing * 15L) {
                    attempts++;
                    int x = boundedRandomInt(1, width - 1, localSeed + attempts * 17L);
                    int y = boundedRandomInt(1, height - 1, localSeed + attempts * 23L);
                    int idx = index(x, y);
                    Biome currentBiome = Biome.values()[biomeMap[idx] & 0xFF];
                    if (!isLandBiome(currentBiome) || currentBiome == biome) {
                        continue;
                    }
                    if (nearPoi(x, y, 6)) {
                        continue;
                    }
                    double score = suitabilityForBiome(biome, x, y);
                    if (score < 0.55) {
                        continue;
                    }
                    filled += paintBiomePatch(x, y, biome, 2, 0.50);
                }
                System.out.println("    convertidos: " + filled);
            }
        }

        private int paintBiomePatch(int centerX, int centerY, Biome biome, int radius, double minimumSuitability) {
            int converted = 0;
            for (int dy = -radius; dy <= radius; dy++) {
                int y = centerY + dy;
                if (y <= 0 || y >= height - 1) {
                    continue;
                }
                for (int dx = -radius; dx <= radius; dx++) {
                    int x = centerX + dx;
                    if (x <= 0 || x >= width - 1) {
                        continue;
                    }
                    if (dx * dx + dy * dy > radius * radius) {
                        continue;
                    }
                    int idx = index(x, y);
                    Biome current = Biome.values()[biomeMap[idx] & 0xFF];
                    if (!isLandBiome(current) || current == biome || nearPoi(x, y, 6)) {
                        continue;
                    }
                    if (suitabilityForBiome(biome, x, y) < minimumSuitability) {
                        continue;
                    }
                    setLand(idx, biome, tileForBiome(biome));
                    converted++;
                }
            }
            return converted;
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
                    if (nearPoi(x, y, 3)) {
                        continue;
                    }
                    if (nearWater(x, y, 1) && biome != Biome.DESERT && biome != Biome.SWAMP) {
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

        private void ensureNaturalMinimums() {
            for (StructureRule rule : rules.structureRules) {
                int current = naturalCounts[rule.structure.ordinal()];
                if (current >= rule.minimum) {
                    continue;
                }
                int missing = rule.minimum - current;
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
                    if (!isLandBiome(biome) || nearPoi(x, y, 3)) {
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
            placePoiType(PoiType.GYM, rules.gymCount, rules.gymDistance);
            placePoiType(PoiType.DUNGEON, rules.dungeonCount, rules.dungeonDistance);
        }

        private void exportWorldGridsJson(File file) throws IOException {
            int[][] biomeGrid = buildGridFromByteMap(biomeMap);
            int[][] blockGrid = buildGridFromByteMap(tileMap);
            int[][] structureGrid = buildStructureGrid();

            StringBuilder sb = new StringBuilder(area * 20);
            sb.append("{\n");
            sb.append("  \"meta\": {\n");
            sb.append("    \"width\": ").append(width).append(",\n");
            sb.append("    \"height\": ").append(height).append(",\n");
            sb.append("    \"seed\": ").append(rules.seed).append("\n");
            sb.append("  },\n");
            sb.append("  \"grid_biomas\": ");
            appendGridJson(sb, biomeGrid);
            sb.append(",\n");
            sb.append("  \"grid_blocos\": ");
            appendGridJson(sb, blockGrid);
            sb.append(",\n");
            sb.append("  \"grid_estruturas\": ");
            appendGridJson(sb, structureGrid);
            sb.append("\n}\n");

            try (FileWriter writer = new FileWriter(file, false)) {
                writer.write(sb.toString());
            }
            System.out.println("JSON das grids salvo em: " + file.getAbsolutePath());
        }

        private int[][] buildGridFromByteMap(byte[] source) {
            int[][] grid = new int[height][width];
            for (int y = 0; y < height; y++) {
                int rowOffset = y * width;
                for (int x = 0; x < width; x++) {
                    grid[y][x] = source[rowOffset + x] & 0xFF;
                }
            }
            return grid;
        }

        private int[][] buildStructureGrid() {
            int[][] grid = buildGridFromByteMap(naturalMap);
            for (Poi poi : pois) {
                int structureCode = switch (poi.type) {
                    case GYM -> 100;
                    case DUNGEON -> 200;
                    case VILLAGE -> 0;
                };
                if (structureCode <= 0) {
                    continue;
                }
                if (poi.y >= 0 && poi.y < height && poi.x >= 0 && poi.x < width) {
                    grid[poi.y][poi.x] = structureCode;
                }
            }
            return grid;
        }

        private void appendGridJson(StringBuilder sb, int[][] grid) {
            sb.append("[\n");
            for (int y = 0; y < grid.length; y++) {
                sb.append("    [");
                int[] row = grid[y];
                for (int x = 0; x < row.length; x++) {
                    if (x > 0) {
                        sb.append(',');
                    }
                    sb.append(row[x]);
                }
                sb.append(']');
                if (y < grid.length - 1) {
                    sb.append(',');
                }
                sb.append('\n');
            }
            sb.append("  ]");
        }

        private void placePoiType(PoiType type, int target, int minDistance) {
            int placed = 0;
            int attempts = 0;
            int margin = Math.max(8, Math.min(width, height) / 18);
            while (placed < target && attempts < target * 8_000) {
                attempts++;
                int x = boundedRandomInt(margin, width - margin, rules.seed + type.ordinal() * 10_000_000L + attempts * 53L);
                int y = boundedRandomInt(margin, height - margin, rules.seed + type.ordinal() * 10_000_000L + attempts * 67L);
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
            double chance = rule.chancePerTile;
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
                    if (nearWater(x, y, 3)) chance *= 1.8;
                }
                case PINE -> chance *= 1.4;
                case AMETHYST, DIAMOND, RUBY, EMERALD -> chance *= 1.25;
                case LAVA_POOL -> chance *= 1.4;
                default -> {
                }
            }
            return chance;
        }

        private Biome classifyLandBiome(double temperature, double moisture, double magic, double volcanic, double swamp, double elevation, Biome macroBiome) {
            if (volcanic > 0.76 && elevation > 0.58) {
                return Biome.VOLCANIC;
            }
            if (magic > 0.81) {
                return Biome.MAGIC;
            }
            if (swamp > 0.67 && moisture > 0.65 && elevation < 0.64) {
                return Biome.SWAMP;
            }

            if (isLandBiome(macroBiome)) {
                double macroSuitability = suitabilityForBiome(macroBiome, temperature, moisture, magic, volcanic, swamp, elevation);
                if (macroSuitability >= 0.48) {
                    return macroBiome;
                }
            }

            if (temperature < 0.28) {
                return Biome.SNOW;
            }
            if (temperature > 0.73 && moisture < 0.34) {
                return Biome.DESERT;
            }
            if (moisture > 0.58) {
                return Biome.FOREST;
            }
            return Biome.FIELD;
        }

        private double suitabilityForBiome(Biome biome, int x, int y) {
            double temperature = temperature(x, y);
            double moisture = moisture(x, y);
            double magic = magic(x, y);
            double volcanic = volcanic(x, y);
            double swamp = swamp(x, y);
            double elevation = elevation(x, y) - edgeWaterPenalty(x, y);
            return suitabilityForBiome(biome, temperature, moisture, magic, volcanic, swamp, elevation);
        }

        private double suitabilityForBiome(Biome biome, double temperature, double moisture, double magic, double volcanic, double swamp, double elevation) {
            return switch (biome) {
                case FIELD -> clamp01(0.5 + (0.5 - Math.abs(moisture - 0.45)) + (0.35 - Math.abs(temperature - 0.55)));
                case FOREST -> clamp01(0.55 + moisture * 0.8 - Math.abs(temperature - 0.55));
                case DESERT -> clamp01(temperature * 0.9 + (1.0 - moisture) * 0.8);
                case SNOW -> clamp01((1.0 - temperature) * 1.25 + elevation * 0.2);
                case MAGIC -> clamp01(magic * 1.2 + moisture * 0.2);
                case VOLCANIC -> clamp01(volcanic * 1.2 + elevation * 0.25);
                case SWAMP -> clamp01(swamp * 1.1 + moisture * 0.8 - Math.abs(elevation - 0.54));
                default -> 0.0;
            };
        }

        private boolean isLakeCandidate(double elevation, double moisture, int x, int y) {
            if (elevation < rules.seaLevel + 0.085 && moisture > 0.68) {
                double lakeNoise = fbm(x, y, 4, 0.55, 2.0, 130.0, 7777L);
                return lakeNoise > 0.76 && !nearBorder(x, y, rules.softOceanBorder);
            }
            return false;
        }

        private void smoothIsolatedLandBiomes() {
            byte[] smoothed = Arrays.copyOf(biomeMap, area);
            int[] counts = new int[Biome.values().length];

            for (int y = 1; y < height - 1; y++) {
                for (int x = 1; x < width - 1; x++) {
                    if (nearWater(x, y, 1)) {
                        continue;
                    }

                    int idx = index(x, y);
                    Biome current = Biome.values()[biomeMap[idx] & 0xFF];
                    if (!isLandBiome(current)) {
                        continue;
                    }

                    Arrays.fill(counts, 0);
                    int sameNeighbors = 0;
                    for (int dy = -1; dy <= 1; dy++) {
                        for (int dx = -1; dx <= 1; dx++) {
                            if (dx == 0 && dy == 0) {
                                continue;
                            }
                            Biome neighbor = Biome.values()[biomeMap[index(x + dx, y + dy)] & 0xFF];
                            if (!isLandBiome(neighbor)) {
                                continue;
                            }
                            counts[neighbor.ordinal()]++;
                            if (neighbor == current) {
                                sameNeighbors++;
                            }
                        }
                    }

                    if (sameNeighbors >= 2) {
                        continue;
                    }

                    Biome dominant = current;
                    int dominantCount = 0;
                    for (Biome biome : Biome.values()) {
                        if (!isLandBiome(biome)) {
                            continue;
                        }
                        int count = counts[biome.ordinal()];
                        if (count > dominantCount) {
                            dominantCount = count;
                            dominant = biome;
                        }
                    }

                    if (dominant != current && dominantCount >= 4) {
                        smoothed[idx] = (byte) dominant.ordinal();
                    }
                }
            }

            for (int i = 0; i < area; i++) {
                Biome oldBiome = Biome.values()[biomeMap[i] & 0xFF];
                Biome newBiome = Biome.values()[smoothed[i] & 0xFF];
                if (oldBiome == newBiome || !isLandBiome(newBiome)) {
                    continue;
                }
                setLand(i, newBiome, tileForBiome(newBiome));
            }
        }

        private void updateCoastsAndBeaches() {
            for (int y = 1; y < height - 1; y++) {
                for (int x = 1; x < width - 1; x++) {
                    int idx = index(x, y);
                    Biome biome = Biome.values()[biomeMap[idx] & 0xFF];
                    if (!isLandBiome(biome)) {
                        continue;
                    }
                    if (nearWater(x, y, 1)) {
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
                    if (tile == Tile.WATER_DEEP && nearLand(x, y, 1)) {
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

        private void setWater(int idx, Biome biome, Tile tile) {
            biomeMap[idx] = (byte) biome.ordinal();
            tileMap[idx] = (byte) tile.ordinal();
            biomeCounts[biome.ordinal()]++;
        }

        private void setLand(int idx, Biome biome, Tile tile) {
            Biome old = Biome.values()[biomeMap[idx] & 0xFF];
            if (old != biome) {
                biomeCounts[old.ordinal()]--;
                biomeCounts[biome.ordinal()]++;
            }
            biomeMap[idx] = (byte) biome.ordinal();
            tileMap[idx] = (byte) tile.ordinal();
        }

        private int totalLandCount() {
            int total = 0;
            for (Biome biome : Biome.values()) {
                if (isLandBiome(biome)) {
                    total += biomeCounts[biome.ordinal()];
                }
            }
            return total;
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
            return t * t * 0.55;
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
