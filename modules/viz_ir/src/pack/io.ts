import fs from "fs";
import path from "path";
import type { VizPack } from "./types";
import { stableStringify } from "../utils/stableStringify";

export type SaveVizPackOptions = {
  write_svg?: boolean;
  write_pack_json?: boolean;
};

function ensureDir(p: string) {
  fs.mkdirSync(p, { recursive: true });
}

export function saveVizPackToDir(pack: VizPack, rootDir: string, opts: SaveVizPackOptions = {}): void {
  const writePack = opts.write_pack_json ?? true;
  const writeSvg = opts.write_svg ?? true;

  ensureDir(rootDir);

  if (writePack) {
    const packPath = path.join(rootDir, "pack.json");
    fs.writeFileSync(packPath, stableStringify(pack), "utf8");
  }

  const svg = pack.payload?.renders?.svg ?? null;
  if (writeSvg && typeof svg === "string" && svg.length) {
    const renderDir = path.join(rootDir, "renders");
    ensureDir(renderDir);
    fs.writeFileSync(path.join(renderDir, "overview.svg"), svg, "utf8");
  }

  const fp = pack.payload?.frame_pack as { frames?: Array<{ render?: { svg?: string | null }; svg?: string | null }> } | null;
  if (fp && Array.isArray(fp.frames)) {
    const framesDir = path.join(rootDir, "frames");
    ensureDir(framesDir);

    for (let i = 0; i < fp.frames.length; i += 1) {
      const fr = fp.frames[i];
      const svgStr = fr?.render?.svg ?? fr?.svg ?? null;
      if (typeof svgStr === "string" && svgStr.length) {
        const name = `frame_${String(i).padStart(3, "0")}.svg`;
        fs.writeFileSync(path.join(framesDir, name), svgStr, "utf8");
      }
    }
  }
}

export function loadVizPackFromDir(rootDir: string): VizPack {
  const packPath = path.join(rootDir, "pack.json");
  const raw = fs.readFileSync(packPath, "utf8");
  const pack = JSON.parse(raw) as VizPack;

  const svgPath = path.join(rootDir, "renders", "overview.svg");
  if (!pack.payload) (pack as { payload?: VizPack["payload"] }).payload = { viz_ir: {} } as VizPack["payload"];
  if (!pack.payload.renders) pack.payload.renders = {};

  if (!pack.payload.renders.svg && fs.existsSync(svgPath)) {
    pack.payload.renders.svg = fs.readFileSync(svgPath, "utf8");
  }

  return pack;
}
