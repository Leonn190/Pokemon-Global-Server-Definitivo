import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

final class GeradorDungeons {
    private static final int MAX_DISTANCIA_PORTAS = 400;

    private final GeneratorContext ctx;

    GeradorDungeons(GeneratorContext ctx) {
        this.ctx = ctx;
    }

    void gerar() {
        List<DungeonDef> dungeons = carregarDefinicoes();
        if (dungeons.isEmpty()) {
            System.out.println("  [WARN] DUNGEON: CSV vazio ou sem entradas válidas");
            return;
        }

        int totalPortas = 0;
        for (DungeonDef dungeon : dungeons) {
            totalPortas += dungeon.entradas;
        }

        int colocadas = 0;
        long tentativas = 0L;
        long limiteTentativas = Math.max(100_000L, (long) totalPortas * 120_000L);

        for (DungeonDef dungeon : dungeons) {
            List<Poi> portasDaDungeon = new ArrayList<>();
            for (int porta = 0; porta < dungeon.entradas; porta++) {
                boolean ok = false;
                while (tentativas < limiteTentativas) {
                    tentativas++;
                    int x = ctx.boundedRandomInt(ctx.terrainRules.dungeonConfig.margin, ctx.width - ctx.terrainRules.dungeonConfig.margin,
                        ctx.seed + 25_000_000L + dungeon.code * 9_973L + porta * 367L + tentativas * 53L);
                    int y = ctx.boundedRandomInt(ctx.terrainRules.dungeonConfig.margin, ctx.height - ctx.terrainRules.dungeonConfig.margin,
                        ctx.seed + 25_500_000L + dungeon.code * 12_007L + porta * 491L + tentativas * 67L);

                    if (!podeColocar(x, y, dungeon.allowedBiomes, portasDaDungeon)) {
                        continue;
                    }

                    Poi poi = new Poi(x, y, PoiType.DUNGEON, "25," + dungeon.code, ctx.nearestRegion(x, y).id);
                    ctx.pois.add(poi);
                    portasDaDungeon.add(poi);
                    colocadas++;
                    ok = true;
                    break;
                }
                if (!ok) {
                    System.out.println("  [WARN] Falha ao posicionar porta da dungeon code=" + dungeon.code
                        + " porta=" + (porta + 1) + "/" + dungeon.entradas
                        + " biomas=" + dungeon.allowedBiomes);
                }
            }
        }

        System.out.println("  DUNGEON: portas=" + colocadas + "/" + totalPortas
            + ", tentativas=" + tentativas + ", dungeons_csv=" + dungeons.size());
    }

    private boolean podeColocar(int x, int y, EnumSet<Biome> biomas, List<Poi> portasColocadas) {
        int idx = ctx.index(x, y);
        Biome biome = Biome.values()[ctx.biomeMap[idx] & 0xFF];
        if (!biomas.contains(biome)) return false;
        if (!ctx.isLandBiome(biome) && biome != Biome.SHALLOW_WATER) return false;

        for (Poi poi : ctx.pois) {
            if (portasColocadas.contains(poi)) {
                continue;
            }
            int minDist = ctx.terrainRules.dungeonConfig.minDistance;
            if (ctx.distanceSquared(x, y, poi.x, poi.y) < (long) minDist * minDist) {
                return false;
            }
        }

        if (!portasColocadas.isEmpty()) {
            long maxDist2 = (long) MAX_DISTANCIA_PORTAS * MAX_DISTANCIA_PORTAS;
            boolean perto = false;
            for (Poi poi : portasColocadas) {
                if (ctx.distanceSquared(x, y, poi.x, poi.y) <= maxDist2) {
                    perto = true;
                    break;
                }
            }
            if (!perto) return false;
        }
        return true;
    }

    private List<DungeonDef> carregarDefinicoes() {
        Path csv = Path.of("Dados", "Tabelas", "Pokemon Global Server - Dungeons.csv");
        if (!Files.exists(csv)) {
            System.out.println("  [WARN] CSV de dungeons não encontrado: " + csv);
            return List.of();
        }
        List<DungeonDef> out = new ArrayList<>();
        try {
            List<String> linhas = Files.readAllLines(csv, StandardCharsets.UTF_8);
            if (linhas.isEmpty()) {
                return List.of();
            }
            String[] header = linhas.get(0).split(",", -1);
            Map<String, Integer> colunas = mapearColunas(header);
            for (int i = 1; i < linhas.size(); i++) {
                String linha = linhas.get(i).trim();
                if (linha.isEmpty()) continue;
                String[] cols = linha.split(",", -1);
                int idxBiomas = colunas.getOrDefault("biomas", 5);
                int idxEntradas = colunas.getOrDefault("entradas", 6);
                int idxCode = colunas.getOrDefault("code", 8);
                if (cols.length <= Math.max(idxCode, Math.max(idxBiomas, idxEntradas))) {
                    System.out.println("  [WARN] Linha de dungeon inválida (colunas insuficientes): " + i);
                    continue;
                }
                int entradas = parseInt(cols[idxEntradas], -1);
                int code = parseInt(cols[idxCode], -1);
                EnumSet<Biome> biomas = parseBiomas(cols[idxBiomas]);
                if (entradas <= 0 || code < 0 || biomas.isEmpty()) {
                    System.out.println("  [WARN] Linha de dungeon ignorada: " + i);
                    continue;
                }
                if (biomas.isEmpty()) continue;
                out.add(new DungeonDef(code, Math.max(1, entradas), biomas));
            }
        } catch (IOException e) {
            System.out.println("  [WARN] Falha lendo CSV de dungeons: " + e.getMessage());
            return List.of();
        }
        return out;
    }

    private EnumSet<Biome> parseBiomas(String texto) {
        EnumSet<Biome> out = EnumSet.noneOf(Biome.class);
        for (String raw : texto.toLowerCase(Locale.ROOT).split("/")) {
            String b = raw.trim();
            switch (b) {
                case "campo" -> out.add(Biome.FIELD);
                case "floresta" -> out.add(Biome.FOREST);
                case "deserto" -> out.add(Biome.DESERT);
                case "neve" -> out.add(Biome.SNOW);
                case "magico" -> out.add(Biome.MAGIC);
                case "vulcanico" -> out.add(Biome.VOLCANIC);
                case "pantano" -> out.add(Biome.SWAMP);
                case "oceano" -> {
                    out.add(Biome.OCEAN);
                    out.add(Biome.SHALLOW_WATER);
                }
            }
        }
        return out;
    }

    private Map<String, Integer> mapearColunas(String[] header) {
        Map<String, Integer> colunas = new HashMap<>();
        for (int i = 0; i < header.length; i++) {
            String chave = header[i] == null ? "" : header[i].trim().toLowerCase(Locale.ROOT);
            if (!chave.isEmpty()) {
                colunas.put(chave, i);
            }
        }
        return colunas;
    }

    private int parseInt(String txt, int padrao) {
        try { return Integer.parseInt(txt.trim()); } catch (Exception e) { return padrao; }
    }

    private record DungeonDef(int code, int entradas, EnumSet<Biome> allowedBiomes) {}
}
