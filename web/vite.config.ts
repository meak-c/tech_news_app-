import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  // GitHub Pagesのサブパス(/<repo>/)でも動くよう相対パスで出力する
  base: "./",
  test: {
    environment: "node",
  },
});
