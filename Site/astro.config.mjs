import { defineConfig } from "astro/config";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const raizDoRepositorio = path.resolve(__dirname, "..");

export default defineConfig({
  vite: {
    resolve: {
      alias: {
        "@recursos": path.resolve(raizDoRepositorio, "Recursos"),
      },
    },
    server: {
      fs: {
        allow: [raizDoRepositorio],
      },
    },
  },
});
