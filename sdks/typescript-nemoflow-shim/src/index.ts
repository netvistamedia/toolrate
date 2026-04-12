/**
 * @deprecated The `nemoflow` package has been renamed to `toolrate`.
 *
 * Run: `npm install toolrate`
 *
 * ```ts
 * // Old
 * import { NemoFlow } from "nemoflow";
 * const client = new NemoFlow("nf_live_...");
 *
 * // New
 * import { ToolRate } from "toolrate";
 * const client = new ToolRate("nf_live_...");
 * ```
 *
 * The legacy `NemoFlow` export still works when imported from either
 * package — it is an alias for `ToolRate`.
 */

if (typeof console !== "undefined" && typeof console.warn === "function") {
  console.warn(
    "[nemoflow] This package is deprecated and has been renamed to 'toolrate'. " +
      "Please run `npm install toolrate` and update your imports from " +
      "`import { NemoFlow } from 'nemoflow'` to `import { ToolRate } from 'toolrate'`. " +
      "This compatibility shim will be removed in a future release."
  );
}

export * from "toolrate";
