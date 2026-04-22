from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.llm.config import LLMConfig, provider_metadata
from src.utils.io import ensure_dir


MOCK_DISCLAIMER = "Mock provider results are engineering smoke tests and should not be interpreted as evidence of LLM reasoning quality."


def load_reference_inputs(llm_config: LLMConfig) -> dict[str, pd.DataFrame]:
    required = {
        "model_summary": llm_config.nonllm_reference_root / "multiseed_model_summary.csv",
        "objective_policy": llm_config.objective_policy_path,
        "structure_frequency": llm_config.structure_frequency_path,
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise RuntimeError("Required LLM reference artifacts are missing:\n- " + "\n- ".join(missing))
    return {name: pd.read_csv(path) for name, path in required.items()}


def load_v0_summary(llm_config: LLMConfig) -> pd.DataFrame:
    path = llm_config.v0_reference_root / "llm_vs_nonllm_summary.csv"
    if not path.exists():
        raise RuntimeError(f"Required LLM V0 reference summary is missing: {path}")
    return pd.read_csv(path)


def reference_discovery_budget_and_score(series_name: str, llm_config: LLMConfig) -> tuple[float | None, float | None]:
    leaderboard_paths = sorted(
        (llm_config.nonllm_reference_root / "seed_runs").glob(f"seed_*/**/{llm_config.nonllm_reference_method}/leaderboard.csv")
    )
    candidate_counts: list[float] = []
    best_scores: list[float] = []
    for path in leaderboard_paths:
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        series_path = path.parents[1].name
        if series_path != _slugify(series_name):
            continue
        candidate_counts.append(float(len(frame)))
        best_scores.append(float(frame["score"].min()))
    if not candidate_counts:
        return None, None
    return float(sum(candidate_counts) / len(candidate_counts)), float(sum(best_scores) / len(best_scores))


def _slugify(text: str) -> str:
    return (
        text.lower()
        .replace(">=", "ge_")
        .replace("<", "lt_")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def build_series_comparison_row(
    series_name: str,
    llm_leaderboard: pd.DataFrame,
    selected_spec: dict[str, Any],
    selected_test_metrics: dict[str, Any],
    proposal_audit: pd.DataFrame,
    llm_config: LLMConfig,
) -> dict[str, Any]:
    refs = load_reference_inputs(llm_config)
    reference_summary = refs["model_summary"]
    series_ref = reference_summary.loc[
        (reference_summary["series_name"] == series_name)
        & (reference_summary["model_name"] == llm_config.nonllm_reference_method)
    ]
    if series_ref.empty:
        raise RuntimeError(f"Missing non-LLM reference row for series={series_name}")

    ref_row = series_ref.iloc[0]
    structure_frequency = refs["structure_frequency"]
    frequency_subset = structure_frequency.loc[structure_frequency["series_name"] == series_name].copy()
    nonllm_best_spec = None
    if not frequency_subset.empty:
        nonllm_best_spec = str(
            frequency_subset.sort_values(
                ["selected_structure_frequency", "count", "structure_spec"],
                ascending=[False, False, True],
            ).iloc[0]["structure_spec"]
        )
    nonllm_candidates, nonllm_best_score = reference_discovery_budget_and_score(series_name, llm_config)
    llm_candidates = int(len(llm_leaderboard))
    llm_best_score = float(llm_leaderboard.iloc[0]["score"])
    valid_rate = float(proposal_audit["hard_valid"].astype(int).sum() / len(proposal_audit)) if len(proposal_audit) else 0.0
    if nonllm_candidates is None:
        candidate_efficiency_note = "Reference discovery candidate budget unavailable."
    elif abs(nonllm_candidates - llm_candidates) < 1.0e-9:
        candidate_efficiency_note = "Budgets matched; compare best score directly."
    else:
        candidate_efficiency_note = "Budgets not matched; do not interpret as an efficiency claim."

    proposed_maps = sorted(set(proposal_audit["raw_observation_map"].astype(str)))
    return {
        "series_name": series_name,
        "llm_best_spec": f"{selected_spec['structure_name']}|fractional={int(bool(selected_spec['fractional']))}|obs={selected_spec['observation_map']}"
        + (f"|delay={int(selected_spec['delay_weeks'])}" if int(selected_spec["delay_weeks"]) > 0 else ""),
        "llm_best_structure_name": selected_spec["structure_name"],
        "llm_best_fractional": bool(selected_spec["fractional"]),
        "llm_best_observation_map": selected_spec["observation_map"],
        "llm_best_delay_weeks": int(selected_spec["delay_weeks"]),
        "llm_valid_proposal_rate": valid_rate,
        "llm_num_proposals": int(len(proposal_audit)),
        "llm_num_valid_specs": int(proposal_audit["hard_valid"].astype(int).sum()),
        "llm_num_candidates_evaluated": llm_candidates,
        "llm_best_score": llm_best_score,
        "llm_best_rolling_mean_mae": float(llm_leaderboard.iloc[0]["rolling_val_mean_mae"]),
        "llm_best_test_mae": float(selected_test_metrics["test_mae"]),
        "nonllm_best_spec": nonllm_best_spec,
        "nonllm_num_candidates_evaluated": nonllm_candidates,
        "nonllm_best_score": nonllm_best_score,
        "nonllm_best_rolling_mean_mae": float(ref_row["mean_rolling_mae"]),
        "nonllm_best_test_mae": float(ref_row["mean_test_mae"]),
        "llm_minus_nonllm_test_mae": float(selected_test_metrics["test_mae"]) - float(ref_row["mean_test_mae"]),
        "llm_minus_nonllm_rolling_mae": float(llm_leaderboard.iloc[0]["rolling_val_mean_mae"]) - float(ref_row["mean_rolling_mae"]),
        "llm_proposed_delayed_i": bool("delayed_I" in proposed_maps),
        "llm_proposed_h": bool("H" in proposed_maps),
        "llm_proposed_fractional": bool(proposal_audit["raw_fractional"].astype(bool).any()),
        "candidate_to_best_rank": 1,
        "candidate_efficiency_note": candidate_efficiency_note,
        **provider_metadata(llm_config),
    }


def build_valid_proposal_rate_table(audit_tables: dict[str, pd.DataFrame], llm_config: LLMConfig) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for series_name, frame in audit_tables.items():
        invalid = frame.loc[~frame["hard_valid"], "invalid_reason"].astype(str).tolist()
        rows.append(
            {
                "series_name": series_name,
                "num_raw_proposals": int(len(frame)),
                "num_schema_valid": int(frame["schema_valid"].astype(int).sum()),
                "num_hard_valid": int(frame["hard_valid"].astype(int).sum()),
                "valid_proposal_rate": float(frame["hard_valid"].astype(int).sum() / len(frame)) if len(frame) else 0.0,
                "invalid_reasons": ";".join(sorted(set(reason for reason in invalid if reason))),
                **provider_metadata(llm_config),
            }
        )
    return pd.DataFrame(rows).sort_values("series_name").reset_index(drop=True)


def build_candidate_efficiency_table(summary: pd.DataFrame, llm_config: LLMConfig) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "series_name": row["series_name"],
                "nonllm_num_candidates_evaluated": row["nonllm_num_candidates_evaluated"],
                "llm_num_candidates_evaluated": row["llm_num_candidates_evaluated"],
                "nonllm_best_score": row["nonllm_best_score"],
                "llm_best_score": row["llm_best_score"],
                "candidate_efficiency_gain": None,
                "candidate_efficiency_note": row["candidate_efficiency_note"],
                **provider_metadata(llm_config),
            }
        )
    return pd.DataFrame(rows).sort_values("series_name").reset_index(drop=True)


def build_valid_proposal_rate_by_round_table(series_outputs: list[dict[str, Any]], llm_config: LLMConfig) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in series_outputs:
        for round_output in item["round_outputs"]:
            audit = round_output["proposal_audit"]
            rows.append(
                {
                    "series_name": item["series_name"],
                    "round_id": int(round_output["round_id"]),
                    "num_raw_proposals": int(len(audit)),
                    "num_schema_valid": int(audit["schema_valid"].astype(int).sum()),
                    "num_hard_valid": int(audit["hard_valid"].astype(int).sum()),
                    "num_evaluated": int(audit["evaluated"].astype(int).sum()),
                    "valid_proposal_rate": float(audit["hard_valid"].astype(int).sum() / len(audit)) if len(audit) else 0.0,
                    **provider_metadata(llm_config),
                }
            )
    return pd.DataFrame(rows).sort_values(["series_name", "round_id"]).reset_index(drop=True)


def build_llm_v1_comparison_row(
    series_output: dict[str, Any],
    llm_config: LLMConfig,
    v0_summary: pd.DataFrame,
) -> dict[str, Any]:
    refs = load_reference_inputs(llm_config)
    ref_summary = refs["model_summary"]
    structure_frequency = refs["structure_frequency"]
    series_name = str(series_output["series_name"])
    v0_row = v0_summary.loc[v0_summary["series_name"] == series_name]
    if v0_row.empty:
        raise RuntimeError(f"Missing LLM V0 reference row for series={series_name}")
    v0_row = v0_row.iloc[0]
    nonllm_row = ref_summary.loc[
        (ref_summary["series_name"] == series_name)
        & (ref_summary["model_name"] == llm_config.nonllm_reference_method)
    ]
    if nonllm_row.empty:
        raise RuntimeError(f"Missing non-LLM reference row for series={series_name}")
    nonllm_row = nonllm_row.iloc[0]
    nonllm_best_spec = None
    structure_subset = structure_frequency.loc[structure_frequency["series_name"] == series_name]
    if not structure_subset.empty:
        nonllm_best_spec = str(
            structure_subset.sort_values(
                ["selected_structure_frequency", "count", "structure_spec"],
                ascending=[False, False, True],
            ).iloc[0]["structure_spec"]
        )
    nonllm_candidates, nonllm_best_score = reference_discovery_budget_and_score(series_name, llm_config)
    final_candidate = series_output["final_selected_candidate"]
    final_test_row = series_output["final_test_report"].iloc[0]
    total_v1_candidates = int(sum(len(round_output["llm_leaderboard"]) for round_output in series_output["round_outputs"]))
    rounds_completed = int(len(series_output["round_outputs"]))
    early_stop_round = next((record.round_id for record in series_output["trace_records"] if record.early_stop), None)
    if nonllm_candidates is None:
        efficiency_note = "Reference discovery candidate budget unavailable."
    else:
        efficiency_note = "Budgets not matched; do not interpret as an efficiency claim."
    return {
        "series_name": series_name,
        "v1_best_spec": f"{final_candidate['best_spec']['structure_name']}|fractional={int(bool(final_candidate['best_spec']['fractional']))}|obs={final_candidate['best_spec']['observation_map']}"
        + (f"|delay={int(final_candidate['best_spec']['delay_weeks'])}" if int(final_candidate["best_spec"]["delay_weeks"]) > 0 else ""),
        "v1_selected_round_id": int(final_candidate["selected_round_id"]),
        "v1_best_score": float(final_candidate["selection_score"]),
        "v1_best_validation_mae": float(final_candidate["selection_validation_mae"]),
        "v1_best_rolling_mean_mae": float(final_candidate["selection_rolling_mean_mae"]),
        "v1_final_test_mae": float(final_test_row["test_mae"]),
        "v1_rounds_completed": rounds_completed,
        "v1_early_stop_round": early_stop_round,
        "v1_num_candidates_evaluated": total_v1_candidates,
        "v0_best_spec": v0_row["llm_best_spec"],
        "v0_best_score": v0_row["llm_best_score"],
        "v0_best_rolling_mean_mae": v0_row["llm_best_rolling_mean_mae"],
        "v0_best_test_mae": v0_row["llm_best_test_mae"],
        "v0_num_candidates_evaluated": v0_row["llm_num_candidates_evaluated"],
        "nonllm_best_spec": nonllm_best_spec,
        "nonllm_best_score": nonllm_best_score,
        "nonllm_best_rolling_mean_mae": float(nonllm_row["mean_rolling_mae"]),
        "nonllm_best_test_mae": float(nonllm_row["mean_test_mae"]),
        "nonllm_num_candidates_evaluated": nonllm_candidates,
        "v1_minus_v0_test_mae": float(final_test_row["test_mae"]) - float(v0_row["llm_best_test_mae"]),
        "v1_minus_v0_rolling_mae": float(final_candidate["selection_rolling_mean_mae"]) - float(v0_row["llm_best_rolling_mean_mae"]),
        "v1_minus_nonllm_test_mae": float(final_test_row["test_mae"]) - float(nonllm_row["mean_test_mae"]),
        "v1_minus_nonllm_rolling_mae": float(final_candidate["selection_rolling_mean_mae"]) - float(nonllm_row["mean_rolling_mae"]),
        "candidate_efficiency_note": efficiency_note,
        **provider_metadata(llm_config),
    }


def build_llm_v1_candidate_efficiency_table(summary: pd.DataFrame, llm_config: LLMConfig) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "series_name": row["series_name"],
                "v1_num_candidates_evaluated": row["v1_num_candidates_evaluated"],
                "v0_num_candidates_evaluated": row["v0_num_candidates_evaluated"],
                "nonllm_num_candidates_evaluated": row["nonllm_num_candidates_evaluated"],
                "v1_best_score": row["v1_best_score"],
                "v0_best_score": row["v0_best_score"],
                "nonllm_best_score": row["nonllm_best_score"],
                "candidate_efficiency_note": row["candidate_efficiency_note"],
                **provider_metadata(llm_config),
            }
        )
    return pd.DataFrame(rows).sort_values("series_name").reset_index(drop=True)


def build_llm_v1_refinement_improvement_table(
    series_outputs: list[dict[str, Any]],
    summary: pd.DataFrame,
    llm_config: LLMConfig,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in series_outputs:
        initial_best = None
        final_best = float(item["final_selected_candidate"]["selection_score"])
        if item["round_outputs"] and item["round_outputs"][0]["selection_artifact"] is not None:
            initial_best = float(item["round_outputs"][0]["selection_artifact"]["selection_score"])
        rows.append(
            {
                "series_name": item["series_name"],
                "rounds_completed": int(len(item["round_outputs"])),
                "initial_round_best_score": initial_best,
                "final_round_best_score": final_best,
                "absolute_score_improvement": None if initial_best is None else initial_best - final_best,
                "improved_flag": False if initial_best is None else bool(final_best < initial_best - llm_config.min_score_improvement),
                "early_stop_flag": bool(any(record.early_stop for record in item["trace_records"])),
                **provider_metadata(llm_config),
            }
        )
    return pd.DataFrame(rows).sort_values("series_name").reset_index(drop=True)


def build_llm_v1_semantic_alignment_table(
    series_outputs: list[dict[str, Any]],
    llm_config: LLMConfig,
) -> pd.DataFrame:
    refs = load_reference_inputs(llm_config)
    structure_frequency = refs["structure_frequency"]
    rows: list[dict[str, Any]] = []
    for item in series_outputs:
        series_name = item["series_name"]
        proposed_maps = sorted(
            {
                str(row["raw_observation_map"])
                for round_output in item["round_outputs"]
                for _, row in round_output["proposal_audit"].iterrows()
            }
        )
        nonllm_subset = structure_frequency.loc[structure_frequency["series_name"] == series_name].copy()
        nonllm_selected_observation_map = None
        if not nonllm_subset.empty:
            top = nonllm_subset.sort_values(
                ["selected_structure_frequency", "count", "structure_spec"],
                ascending=[False, False, True],
            ).iloc[0]["structure_spec"]
            if "|obs=" in str(top):
                nonllm_selected_observation_map = str(top).split("|obs=", 1)[1].split("|", 1)[0]
        rows.append(
            {
                "series_name": series_name,
                "target_semantics": "hospitalization_rate",
                "proposed_observation_maps": ";".join(proposed_maps),
                "v1_selected_observation_map": item["final_selected_candidate"]["best_spec"]["observation_map"],
                "nonllm_selected_observation_map": nonllm_selected_observation_map,
                "semantic_alignment_flag": bool("delayed_I" in proposed_maps or "H" in proposed_maps or "I+H" in proposed_maps),
                "notes": "Mock provider engineering smoke test only.",
                **provider_metadata(llm_config),
            }
        )
    return pd.DataFrame(rows).sort_values("series_name").reset_index(drop=True)


def build_semantic_alignment_table(
    summary: pd.DataFrame,
    proposal_audits: dict[str, pd.DataFrame],
    llm_config: LLMConfig,
) -> pd.DataFrame:
    refs = load_reference_inputs(llm_config)
    structure_frequency = refs["structure_frequency"]
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        series_name = row["series_name"]
        proposed_maps = sorted(set(proposal_audits[series_name]["raw_observation_map"].astype(str)))
        nonllm_subset = structure_frequency.loc[structure_frequency["series_name"] == series_name].copy()
        nonllm_selected_observation_map = None
        if not nonllm_subset.empty:
            top = nonllm_subset.sort_values(
                ["selected_structure_frequency", "count", "structure_spec"],
                ascending=[False, False, True],
            ).iloc[0]["structure_spec"]
            if "|obs=" in str(top):
                nonllm_selected_observation_map = str(top).split("|obs=", 1)[1].split("|", 1)[0]
        rows.append(
            {
                "series_name": series_name,
                "target_semantics": "hospitalization_rate",
                "proposed_observation_maps": ";".join(proposed_maps),
                "nonllm_selected_observation_map": nonllm_selected_observation_map,
                "semantic_alignment_flag": bool("delayed_I" in proposed_maps or "H" in proposed_maps or "I+H" in proposed_maps),
                "notes": "Mock provider engineering smoke test only.",
                **provider_metadata(llm_config),
            }
        )
    return pd.DataFrame(rows).sort_values("series_name").reset_index(drop=True)


def write_llm_v0_report(summary: pd.DataFrame, report_path: Path, llm_config: LLMConfig) -> None:
    objective_policy = load_reference_inputs(llm_config)["objective_policy"]
    lines = [
        "# LLM-V0 Report",
        "",
        "LLM-V0 is a proposal-only layer.",
        "It does not perform iterative refinement.",
        "It does not make final scientific claims from mock-provider results.",
        "It is intended to validate schema, leakage guards, hard validation, candidate execution, and comparison against non-LLM discovery.",
        "",
        MOCK_DISCLAIMER,
        "",
        "## Series Summary",
        "",
    ]
    for _, row in summary.sort_values("series_name").iterrows():
        objective_row = objective_policy.loc[objective_policy["series_name"] == row["series_name"]]
        objective_note = None
        if not objective_row.empty:
            objective_note = str(objective_row.iloc[0]["recommended_reason"])
        lines.extend(
            [
                f"### {row['series_name']}",
                "",
                f"- LLM best spec: `{row['llm_best_spec']}`",
                f"- LLM validation/rolling score: `{row['llm_best_score']:.6f}`",
                f"- LLM selected-candidate test MAE: `{row['llm_best_test_mae']:.6f}`",
                f"- Non-LLM reference method: `{llm_config.nonllm_reference_method}`",
                f"- Candidate budget note: {row['candidate_efficiency_note']}",
                *( [f"- Objective-aware reference note: {objective_note}"] if objective_note else [] ),
                "",
            ]
        )
    ensure_dir(report_path.parent)
    report_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_llm_v1_report(
    summary: pd.DataFrame,
    refinement_improvement: pd.DataFrame,
    report_path: Path,
    llm_config: LLMConfig,
) -> None:
    lines = [
        "# LLM-V1 Iterative Report",
        "",
        "LLM-V1 adds iterative validation-feedback refinement on top of the mock-only LLM-V0 proposal layer.",
        "It still does not make final scientific claims from mock-provider results.",
        "",
        MOCK_DISCLAIMER,
        "",
        "## Series Summary",
        "",
    ]
    for _, row in summary.sort_values("series_name").iterrows():
        lines.extend(
            [
                f"### {row['series_name']}",
                "",
                f"- V1 best spec: `{row['v1_best_spec']}`",
                f"- V1 selected round: `{row['v1_selected_round_id']}`",
                f"- V1 best score: `{row['v1_best_score']:.6f}`",
                f"- V1 final selected-candidate test MAE: `{row['v1_final_test_mae']:.6f}`",
                f"- V0 best spec: `{row['v0_best_spec']}`",
                f"- Non-LLM reference spec: `{row['nonllm_best_spec']}`",
                f"- Candidate budget note: {row['candidate_efficiency_note']}",
                "",
            ]
        )
    if not refinement_improvement.empty:
        lines.extend(["## Refinement Improvement", ""])
        for _, row in refinement_improvement.sort_values("series_name").iterrows():
            lines.append(
                f"- `{row['series_name']}`: rounds `{row['rounds_completed']}`, "
                f"initial `{row['initial_round_best_score']}`, final `{row['final_round_best_score']}`, "
                f"improved `{row['improved_flag']}`, early_stop `{row['early_stop_flag']}`"
            )
        lines.append("")
    ensure_dir(report_path.parent)
    report_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
