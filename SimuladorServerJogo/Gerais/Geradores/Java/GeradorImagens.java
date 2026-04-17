import javax.imageio.ImageIO;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;
import java.io.File;
import java.io.IOException;

final class GeradorImagens {
    private static final int REGION_NAME_OUTLINE = rgb(255, 255, 255);
    private static final int REGION_NAME_FILL = rgb(20, 20, 20);
    private static final int VILLAGE_NAME_OUTLINE = rgb(255, 255, 255);
    private static final int VILLAGE_NAME_FILL = rgb(140, 0, 0);
    private static final int VILLAGE_POINT_COLOR = rgb(220, 28, 28);
    private static final int GYM_POINT_COLOR = rgb(255, 255, 255);
    private static final int DUNGEON_POINT_COLOR = rgb(0, 0, 0);
    private static final int ROUTE_COLOR = rgb(150, 92, 48);
    private static final int ROUTE_OUTLINE = rgb(245, 233, 196);

    private final GeneratorContext ctx;

    GeradorImagens(GeneratorContext ctx) {
        this.ctx = ctx;
    }

    void gerarImagens(File outputDir) throws IOException {
        renderBaseWorld(new File(outputDir, "world_foto.png"));
        renderWorldWithObjects(new File(outputDir, "world_foto_objetos.png"));
        renderWorldWithPois(new File(outputDir, "world_foto_estadios_dungeons.png"));
        renderWorldWithRegions(new File(outputDir, "world_foto_regioes.png"));
        renderWorldWithRoutes(new File(outputDir, "world_foto_rotas.png"));
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
                drawPoint(buffer, poi.x, poi.y, 5, poiColor(poi.type));
            }
        }

        ImageIO.write(image, "png", file);
        image.flush();
    }

    private void renderWorldWithPois(File file) throws IOException {
        BufferedImage image = createBaseImage();
        int[] buffer = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();

        for (Poi poi : ctx.pois) {
            if (poi.type == PoiType.GYM) {
                drawPoint(buffer, poi.x, poi.y, 12, GYM_POINT_COLOR);
            } else if (poi.type == PoiType.DUNGEON) {
                drawPoint(buffer, poi.x, poi.y, 12, DUNGEON_POINT_COLOR);
            }
        }

        ImageIO.write(image, "png", file);
        image.flush();
    }

    private void renderWorldWithRegions(File file) throws IOException {
        BufferedImage image = new BufferedImage(ctx.width, ctx.height, BufferedImage.TYPE_INT_RGB);
        int[] buffer = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();

        for (int y = 0; y < ctx.height; y++) {
            for (int x = 0; x < ctx.width; x++) {
                int idx = ctx.index(x, y);
                Tile tile = Tile.values()[ctx.tileMap[idx] & 0xFF];
                if (tile == Tile.WATER_DEEP || tile == Tile.WATER_SHALLOW) {
                    buffer[idx] = tileColor(tile);
                } else {
                    buffer[idx] = ctx.nearestRegion(x, y).color;
                }
            }
        }

        ImageIO.write(image, "png", file);
        image.flush();
    }

    private void renderWorldWithRoutes(File file) throws IOException {
        BufferedImage image = createBaseImage();
        Graphics2D g = image.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        int routeStroke = Math.max(2, Math.min(ctx.width, ctx.height) / 520);

        g.setStroke(new BasicStroke(routeStroke + 2f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
        g.setColor(new Color(ROUTE_OUTLINE));
        for (RouteData route : ctx.routes) {
            drawRoute(g, route);
        }

        g.setStroke(new BasicStroke(routeStroke, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
        g.setColor(new Color(ROUTE_COLOR));
        for (RouteData route : ctx.routes) {
            drawRoute(g, route);
        }

        int[] buffer = ((DataBufferInt) image.getRaster().getDataBuffer()).getData();
        for (Poi poi : ctx.pois) {
            if (poi.type == PoiType.VILLAGE) {
                drawPoint(buffer, poi.x, poi.y, 7, VILLAGE_POINT_COLOR);
            }
        }

        int villageFontSize = Math.max(18, Math.min(ctx.width, ctx.height) / 150);
        g.setFont(new Font("SansSerif", Font.BOLD, villageFontSize));
        for (Poi poi : ctx.pois) {
            if (poi.type == PoiType.VILLAGE && poi.name != null && !poi.name.isBlank()) {
                drawLabel(g, poi.name, poi.x, poi.y - villageFontSize / 2 - 12, VILLAGE_NAME_FILL, VILLAGE_NAME_OUTLINE);
            }
        }
        g.dispose();

        ImageIO.write(image, "png", file);
        image.flush();
    }

    private void drawRoute(Graphics2D g, RouteData route) {
        if (route.points == null || route.points.size() < 2) {
            return;
        }
        for (int i = 1; i < route.points.size(); i++) {
            int[] a = route.points.get(i - 1);
            int[] b = route.points.get(i);
            g.drawLine(a[0], a[1], b[0], b[1]);
        }
    }

    private void drawLabel(Graphics2D g, String text, int centerX, int baselineY, int fillRgb, int outlineRgb) {
        FontMetrics metrics = g.getFontMetrics();
        int textX = centerX - metrics.stringWidth(text) / 2;
        int ascent = metrics.getAscent();
        int textY = baselineY + ascent / 3;

        g.setStroke(new BasicStroke(Math.max(2f, g.getFont().getSize2D() / 10f), BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
        g.setColor(new Color(outlineRgb));
        for (int oy = -2; oy <= 2; oy++) {
            for (int ox = -2; ox <= 2; ox++) {
                if (ox == 0 && oy == 0) {
                    continue;
                }
                g.drawString(text, textX + ox, textY + oy);
            }
        }
        g.setColor(new Color(fillRgb));
        g.drawString(text, textX, textY);
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
            case CACTUS -> rgb(34, 132, 50);
            case SHELL -> rgb(238, 224, 202);
            case AQUAMARINE -> rgb(70, 208, 220);
            case COAL -> rgb(62, 62, 62);
            case IRON -> rgb(176, 168, 156);
            case FLOWER -> rgb(238, 92, 170);
            case JADE -> rgb(90, 178, 120);
            case PLANT -> rgb(84, 176, 74);
            case SAPPHIRE -> rgb(72, 106, 226);
            case TOPAZ -> rgb(236, 182, 72);
            case TREE_TROMBOSA -> rgb(28, 112, 40);
            case HOUSE -> rgb(174, 84, 54);
            case NONE -> rgb(0, 0, 0);
        };
    }

    private int poiColor(PoiType type) {
        return switch (type) {
            case GYM -> GYM_POINT_COLOR;
            case DUNGEON -> DUNGEON_POINT_COLOR;
            case VILLAGE -> rgb(255, 236, 80);
        };
    }

    private static int rgb(int r, int g, int b) {
        return (r << 16) | (g << 8) | b;
    }
}
