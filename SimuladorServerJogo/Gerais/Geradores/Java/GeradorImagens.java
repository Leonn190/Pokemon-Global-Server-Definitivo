
import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;
import java.io.File;
import java.io.IOException;

final class GeradorImagens {
    private final GeneratorContext ctx;

    GeradorImagens(GeneratorContext ctx) {
        this.ctx = ctx;
    }

    void gerarImagens(File outputDir) throws IOException {
        renderBaseWorld(new File(outputDir, "world_foto.png"));
        renderWorldWithObjects(new File(outputDir, "world_foto_objetos.png"));
        renderWorldWithPois(new File(outputDir, "world_foto_estadios_dungeons.png"));
    }

    private void renderBaseWorld(File file) throws IOException {
        BufferedImage image = createBaseImage();
        ImageIO.write(image, "png", file);
        image.flush();
    }

    private void renderWorldWithObjects(File file) throws IOException {
        BufferedImage image = createBaseImage();
        int[] buffer = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();

        for (int i = 0; i < ctx.area; i++) {
            NaturalStructure structure = NaturalStructure.values()[ctx.naturalMap[i] & 0xFF];
            if (structure != NaturalStructure.NONE) {
                buffer[i] = naturalColor(structure);
            }
        }
        for (Poi poi : ctx.pois) {
            if (poi.type == PoiType.VILLAGE) {
                drawPoint(buffer, poi.x, poi.y, 4, poiColor(poi.type));
            }
        }

        ImageIO.write(image, "png", file);
        image.flush();
    }

    private void renderWorldWithPois(File file) throws IOException {
        BufferedImage image = createBaseImage();
        int[] buffer = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();

        for (Poi poi : ctx.pois) {
            if (poi.type == PoiType.GYM || poi.type == PoiType.DUNGEON) {
                drawPoint(buffer, poi.x, poi.y, 4, poiColor(poi.type));
            }
        }

        ImageIO.write(image, "png", file);
        image.flush();
    }

    private BufferedImage createBaseImage() {
        BufferedImage image = new BufferedImage(ctx.width, ctx.height, BufferedImage.TYPE_INT_RGB);
        int[] buffer = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();
        for (int i = 0; i < ctx.area; i++) {
            buffer[i] = tileColor(Tile.values()[ctx.tileMap[i] & 0xFF]);
        }
        return image;
    }

    private void drawPoint(int[] buffer, int cx, int cy, int radius, int color) {
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
                if (dx * dx + dy * dy <= radius * radius) {
                    buffer[ctx.index(x, y)] = color;
                }
            }
        }
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
}
