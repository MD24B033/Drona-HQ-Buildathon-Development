import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /*
   * This app sits in a subdirectory of a larger repo, so pin the
   * workspace root. Without it Turbopack walks up looking for a
   * lockfile and can settle on one outside the project.
   *
   * process.cwd() is the project directory for both `next dev` and
   * `next build` (including on Vercel, where Root Directory is set to
   * this folder), and unlike __dirname it works whether the config is
   * loaded as CommonJS or ESM.
   */
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;
