import crypto from "crypto";

export function hashInputs(obj: unknown): string {
  const json = JSON.stringify(obj);
  return `sha256:${crypto.createHash("sha256").update(json).digest("hex")}`;
}
