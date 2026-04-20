import type { RawAssessResponse } from "./schema.js";

export interface AssessSummary {
  reliability_score: number;
  confidence: number;
  recommended: boolean;
  one_liner: string;
}

export function makeSummary(a: RawAssessResponse): AssessSummary {
  const score = Math.round(a.reliability_score);
  const recommended = score >= 70 && a.within_budget !== false;

  return {
    reliability_score: score,
    confidence: round2(a.confidence),
    recommended,
    one_liner: oneLiner(a, score, recommended),
  };
}

function oneLiner(a: RawAssessResponse, score: number, recommended: boolean): string {
  const headline = scoreLabel(score, a.data_source);
  const tags: string[] = [];

  if (a.within_budget === true) tags.push("within budget");
  else if (a.within_budget === false) tags.push("OVER budget");

  if (a.recommended_model) tags.push(`use ${a.recommended_model}`);

  if (a.gdpr_compliant === true) tags.push("GDPR-compliant");
  else if (a.gdpr_compliant === false && a.data_residency_risk && a.data_residency_risk !== "none") {
    tags.push(`${a.data_residency_risk} data-residency risk`);
  }

  const tagged = tags.length > 0 ? `${headline} — ${tags.join(", ")}` : headline;
  const suffix = recommended ? "Safe to proceed." : "Consider an alternative from top_alternatives.";
  return `${tagged}. ${suffix}`;
}

function scoreLabel(score: number, dataSource: string): string {
  let label: string;
  if (score >= 90) label = `Highly reliable (${score}/100)`;
  else if (score >= 70) label = `Reliable (${score}/100)`;
  else if (score >= 50) label = `Moderately reliable (${score}/100)`;
  else label = `Low reliability (${score}/100)`;

  if (dataSource === "llm_estimated") label += ", LLM-estimated";
  else if (dataSource === "bayesian_prior") label += ", limited data";
  return label;
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}
