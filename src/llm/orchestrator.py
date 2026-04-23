from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data.split import ChronologicalSplit
from src.discovery.rules import StructureSpec
from src.llm.analyst import run_analyst
from src.llm.config import LLMConfig
from src.llm.critic import run_critic
from src.llm.executor import evaluate_llm_candidate_specs, evaluate_selected_spec_on_test
from src.llm.proposer import generate_proposals
from src.llm.provider import build_provider
from src.llm.reporting import (
    build_candidate_efficiency_table,
    build_semantic_alignment_table,
    build_series_comparison_row,
    build_llm_v1_candidate_efficiency_table,
    build_llm_v1_comparison_row,
    build_llm_v1_refinement_improvement_table,
    build_llm_v1_semantic_alignment_table,
    build_valid_proposal_rate_by_round_table,
    build_valid_proposal_rate_table,
    load_v0_summary,
    write_llm_v0_report,
    write_llm_v1_report,
)
from src.llm.schema import proposal_to_dict, validate_llm_proposal_payload
from src.llm.semantics import build_surveillance_semantics_summary
from src.llm.summary import build_prompt_safe_series_summary, build_report_series_summary
from src.llm.trace import RoundTraceRecord, write_refinement_trace_jsonl, write_refinement_trace_markdown
from src.discovery.search import SearchConfig
from src.models.base import FitConfig
from src.utils.io import ensure_dir, write_json


def _slugify(text: str) -> str:
    return (
        text.lower()
        .replace(">=", "ge_")
        .replace("<", "lt_")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def _audit_and_validate_proposals(
    *,
    series_name: str,
    round_id: int,
    proposals: list[Any],
    critic_annotations: dict[int, dict[str, Any]],
    critic_rejected_ids: set[int],
    llm_config: LLMConfig,
    provider_metadata: dict[str, Any],
) -> tuple[pd.DataFrame, list[StructureSpec], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    audit_rows: list[dict[str, Any]] = []
    validated_specs: list[StructureSpec] = []
    invalid_specs: list[dict[str, Any]] = []
    proposal_metadata: dict[str, dict[str, Any]] = {}

    for proposal_index, proposal in enumerate(proposals):
        payload = proposal_to_dict(proposal)
        validation = validate_llm_proposal_payload(payload)
        critic_annotation = critic_annotations.get(proposal_index, {})
        audit_row = {
            "series_name": series_name,
            "round_id": round_id,
            "proposal_id": proposal_index,
            "provider": provider_metadata["provider"],
            "provider_is_mock": provider_metadata["provider_is_mock"],
            "scientific_claim_allowed": provider_metadata["scientific_claim_allowed"],
            "raw_structure_name": payload["structure_name"],
            "raw_fractional": payload["fractional"],
            "raw_observation_map": payload["observation_map"],
            "raw_delay_weeks": int(payload["delay_weeks"]),
            "schema_valid": bool(validation.schema_valid),
            "hard_valid": bool(validation.hard_valid),
            "invalid_reason": validation.invalid_reason or "",
            "critic_priority": critic_annotation.get("critic_priority", "medium"),
            "critic_risk_flags": critic_annotation.get("critic_risk_flags", ""),
            "evaluated": False,
        }
        critic_blocked = llm_config.critic_hard_filter and proposal_index in critic_rejected_ids
        if validation.hard_valid and validation.structure_spec is not None:
            if critic_blocked:
                audit_row["invalid_reason"] = "critic_rejected"
            else:
                validated_specs.append(validation.structure_spec)
                proposal_metadata[validation.structure_spec.spec_key] = {
                    "round_id": round_id,
                    "proposal_id": proposal_index,
                    "role_source": "proposer",
                    "critic_priority": audit_row["critic_priority"],
                    "critic_risk_flags": audit_row["critic_risk_flags"],
                }
                audit_row["evaluated"] = True
        else:
            invalid_specs.append({"proposal_id": proposal_index, **payload, "invalid_reason": audit_row["invalid_reason"]})
        audit_rows.append(audit_row)

    proposal_audit = pd.DataFrame(audit_rows).sort_values(["round_id", "proposal_id"]).reset_index(drop=True)
    return proposal_audit, validated_specs, invalid_specs, proposal_metadata


def _run_llm_round(
    *,
    series_name: str,
    round_id: int,
    prompt_safe_summary: Any,
    semantics_summary: Any,
    llm_config: LLMConfig,
    provider: Any,
    round_dir: Path,
    y: np.ndarray,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    seed: int,
    previous_feedback: dict[str, Any] | None = None,
    analyst_prompt_text: str | None = None,
    analyst_feedback_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    round_dir = ensure_dir(round_dir)
    proposal_batch = generate_proposals(
        prompt_safe_summary,
        semantics_summary.to_dict(),
        llm_config,
        provider,
        round_id=round_id,
        previous_feedback=previous_feedback,
    )
    critic_decision = run_critic(
        prompt_safe_summary,
        semantics_summary.to_dict(),
        proposal_batch.proposals,
        llm_config,
        provider,
    )

    if analyst_prompt_text is not None:
        (round_dir / "analyst_prompt.txt").write_text(analyst_prompt_text, encoding="utf-8")
    if analyst_feedback_payload is not None:
        write_json(analyst_feedback_payload, round_dir / "analyst_feedback.json")

    (round_dir / "proposer_prompt.txt").write_text(proposal_batch.prompt_text, encoding="utf-8")
    write_json(proposal_batch.response_payload, round_dir / "proposer_response.json")
    (round_dir / "critic_prompt.txt").write_text(critic_decision.prompt_text, encoding="utf-8")
    write_json(critic_decision.response_payload, round_dir / "critic_response.json")

    proposal_audit, validated_specs, invalid_specs, proposal_metadata = _audit_and_validate_proposals(
        series_name=series_name,
        round_id=round_id,
        proposals=proposal_batch.proposals,
        critic_annotations=critic_decision.annotations,
        critic_rejected_ids=critic_decision.rejected_ids,
        llm_config=llm_config,
        provider_metadata=proposal_batch.provider_metadata,
    )
    proposal_audit.to_csv(round_dir / "proposal_audit.csv", index=False)
    write_json(invalid_specs, round_dir / "invalid_specs.json")
    write_json(
        [
            {
                "structure_name": spec.structure_name,
                "fractional": spec.fractional,
                "observation_map": spec.observation_map,
                "delay_weeks": spec.delay_weeks,
                "spec_key": spec.spec_key,
            }
            for spec in validated_specs
        ],
        round_dir / "validated_specs.json",
    )

    if validated_specs:
        leaderboard, selection_artifact = evaluate_llm_candidate_specs(
            series_name=series_name,
            specs=validated_specs,
            y=y,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            artifact_dir=round_dir,
            seed=seed + round_id,
            proposal_metadata=proposal_metadata,
            provider_info=proposal_batch.provider_metadata,
        )
        round_summary = {
            "series_name": series_name,
            "round_id": round_id,
            "num_raw_proposals": int(len(proposal_audit)),
            "num_schema_valid": int(proposal_audit["schema_valid"].astype(int).sum()),
            "num_hard_valid": int(proposal_audit["hard_valid"].astype(int).sum()),
            "num_evaluated": int(proposal_audit["evaluated"].astype(int).sum()),
            "round_best_spec": selection_artifact["best_spec"],
            "round_best_score": selection_artifact["selection_score"],
            "round_best_validation_mae": selection_artifact["selection_validation_mae"],
            "round_best_rolling_mean_mae": selection_artifact["selection_rolling_mean_mae"],
            **proposal_batch.provider_metadata,
        }
    else:
        leaderboard = pd.DataFrame(
            columns=[
                "series_name",
                "round_id",
                "proposal_id",
                "role_source",
                "critic_priority",
                "critic_risk_flags",
                "schema_valid",
                "hard_valid",
                "invalid_reason",
            ]
        )
        leaderboard.to_csv(round_dir / "llm_leaderboard.csv", index=False)
        selection_artifact = None
        round_summary = {
            "series_name": series_name,
            "round_id": round_id,
            "num_raw_proposals": int(len(proposal_audit)),
            "num_schema_valid": int(proposal_audit["schema_valid"].astype(int).sum()),
            "num_hard_valid": int(proposal_audit["hard_valid"].astype(int).sum()),
            "num_evaluated": 0,
            "round_best_spec": None,
            "round_best_score": None,
            "round_best_validation_mae": None,
            "round_best_rolling_mean_mae": None,
            **proposal_batch.provider_metadata,
        }
    write_json(round_summary, round_dir / "round_summary.json")
    return {
        "round_id": round_id,
        "round_dir": round_dir,
        "proposal_audit": proposal_audit,
        "llm_leaderboard": leaderboard,
        "selection_artifact": selection_artifact,
        "round_summary": round_summary,
        "provider_metadata": proposal_batch.provider_metadata,
    }


def run_llm_structure_search(
    series_name: str,
    y: np.ndarray,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    llm_config: LLMConfig,
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    artifact_dir = ensure_dir(artifact_dir)
    provider = build_provider(llm_config)
    prompt_safe_summary = build_prompt_safe_series_summary(
        series_name=series_name,
        y_train=y[split.train_slice],
        y_val=y[split.val_slice],
        structure_frequency_path=llm_config.structure_frequency_path,
    )
    semantics_summary = build_surveillance_semantics_summary()
    proposal_batch = generate_proposals(prompt_safe_summary, semantics_summary.to_dict(), llm_config, provider)
    critic_decision = run_critic(
        prompt_safe_summary,
        semantics_summary.to_dict(),
        proposal_batch.proposals,
        llm_config,
        provider,
    )

    (artifact_dir / "proposer_prompt.txt").write_text(proposal_batch.prompt_text, encoding="utf-8")
    write_json(proposal_batch.response_payload, artifact_dir / "proposer_response.json")
    (artifact_dir / "critic_prompt.txt").write_text(critic_decision.prompt_text, encoding="utf-8")
    write_json(critic_decision.response_payload, artifact_dir / "critic_response.json")
    write_json({**prompt_safe_summary.to_prompt_dict(), **proposal_batch.provider_metadata}, artifact_dir / "series_summary.json")
    write_json({**semantics_summary.to_dict(), **proposal_batch.provider_metadata}, artifact_dir / "semantics_summary.json")

    proposal_audit, validated_specs, invalid_specs, proposal_metadata = _audit_and_validate_proposals(
        series_name=series_name,
        round_id=1,
        proposals=proposal_batch.proposals,
        critic_annotations=critic_decision.annotations,
        critic_rejected_ids=critic_decision.rejected_ids,
        llm_config=llm_config,
        provider_metadata=proposal_batch.provider_metadata,
    )

    if not validated_specs:
        raise RuntimeError(f"LLM-V0 produced no hard-valid proposals for series={series_name}")

    proposal_audit.to_csv(artifact_dir / "proposal_audit.csv", index=False)
    write_json(invalid_specs, artifact_dir / "invalid_specs.json")

    validated_spec_payload = [
        {
            "structure_name": spec.structure_name,
            "fractional": spec.fractional,
            "observation_map": spec.observation_map,
            "delay_weeks": spec.delay_weeks,
            "spec_key": spec.spec_key,
        }
        for spec in validated_specs
    ]
    write_json(validated_spec_payload, artifact_dir / "validated_specs.json")

    leaderboard, selection_artifact = evaluate_llm_candidate_specs(
        series_name=series_name,
        specs=validated_specs,
        y=y,
        split=split,
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
        proposal_metadata=proposal_metadata,
        provider_info=proposal_batch.provider_metadata,
    )
    selected_spec = StructureSpec(
        structure_name=str(selection_artifact["best_spec"]["structure_name"]),
        fractional=bool(selection_artifact["best_spec"]["fractional"]),
        observation_map=str(selection_artifact["best_spec"]["observation_map"]),
        delay_weeks=int(selection_artifact["best_spec"]["delay_weeks"]),
    )
    selected_test_metrics = evaluate_selected_spec_on_test(
        spec=selected_spec,
        y=y,
        split=split,
        fit_config=fit_config,
        search_config=search_config,
        seed=seed,
    )
    selected_test_metrics = {**selected_test_metrics, **proposal_batch.provider_metadata}
    write_json(selected_test_metrics, artifact_dir / "selected_candidate_test_metrics.json")
    report_summary = build_report_series_summary(prompt_safe_summary, objective_policy_row=None)
    write_json({**report_summary.to_report_dict(), **proposal_batch.provider_metadata}, artifact_dir / "report_series_summary.json")
    return {
        "series_name": series_name,
        "artifact_dir": artifact_dir,
        "proposal_audit": proposal_audit,
        "llm_leaderboard": leaderboard,
        "selection_artifact": selection_artifact,
        "selected_test_metrics": selected_test_metrics,
        "provider_metadata": proposal_batch.provider_metadata,
}


def run_llm_iterative_refinement(
    series_name: str,
    y: np.ndarray,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    llm_config: LLMConfig,
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    artifact_dir = ensure_dir(artifact_dir)
    rounds_root = ensure_dir(artifact_dir / "rounds")
    provider = build_provider(llm_config)
    prompt_safe_summary = build_prompt_safe_series_summary(
        series_name=series_name,
        y_train=y[split.train_slice],
        y_val=y[split.val_slice],
        structure_frequency_path=llm_config.structure_frequency_path,
    )
    semantics_summary = build_surveillance_semantics_summary()
    write_json(prompt_safe_summary.to_prompt_dict(), artifact_dir / "series_summary.json")
    write_json(semantics_summary.to_dict(), artifact_dir / "semantics_summary.json")

    trace_records: list[RoundTraceRecord] = []
    round_outputs: list[dict[str, Any]] = []
    best_output: dict[str, Any] | None = None
    best_score = float("inf")
    no_improve_rounds = 0
    previous_feedback_context: dict[str, Any] | None = None
    previous_best_spec_dict: dict[str, Any] | None = None

    for round_id in range(1, llm_config.max_rounds + 1):
        analyst_prompt_text = None
        analyst_feedback_payload = None
        analyst_feedback_summary = ""
        if round_id > 1 and round_outputs:
            previous_round = round_outputs[-1]
            previous_selection = previous_round["selection_artifact"]
            previous_best_spec_dict = previous_selection["best_spec"] if previous_selection is not None else previous_best_spec_dict
            analyst_decision = run_analyst(
                series_summary=prompt_safe_summary,
                llm_config=llm_config,
                provider=provider,
                round_id=round_id - 1,
                previous_best_spec=previous_best_spec_dict or {},
                round_leaderboard=previous_round["llm_leaderboard"],
            )
            analyst_prompt_text = analyst_decision.prompt_text
            analyst_feedback_payload = {
                "feedback": analyst_decision.feedback.to_dict(),
                "provider_response": analyst_decision.response_payload,
            }
            analyst_feedback_summary = analyst_decision.feedback.proposer_instruction
            previous_feedback_context = {
                "analyst_feedback": analyst_decision.feedback.to_dict(),
                "previous_best_spec": previous_best_spec_dict,
            }

        round_output = _run_llm_round(
            series_name=series_name,
            round_id=round_id,
            prompt_safe_summary=prompt_safe_summary,
            semantics_summary=semantics_summary,
            llm_config=llm_config,
            provider=provider,
            round_dir=rounds_root / f"round_{round_id}",
            y=y,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            seed=seed,
            previous_feedback=previous_feedback_context,
            analyst_prompt_text=analyst_prompt_text,
            analyst_feedback_payload=analyst_feedback_payload,
        )
        round_outputs.append(round_output)
        selection_artifact = round_output["selection_artifact"]
        round_best_spec = None
        round_best_score = None
        score_improvement = None
        early_stop = False
        if selection_artifact is not None:
            round_best_spec = StructureSpec(
                structure_name=str(selection_artifact["best_spec"]["structure_name"]),
                fractional=bool(selection_artifact["best_spec"]["fractional"]),
                observation_map=str(selection_artifact["best_spec"]["observation_map"]),
                delay_weeks=int(selection_artifact["best_spec"]["delay_weeks"]),
            )
            round_best_score = float(selection_artifact["selection_score"])
            if best_output is None or round_best_score < best_score - llm_config.min_score_improvement:
                score_improvement = None if best_output is None else best_score - round_best_score
                best_output = round_output
                best_score = round_best_score
                previous_best_spec_dict = selection_artifact["best_spec"]
                no_improve_rounds = 0
            else:
                score_improvement = best_score - round_best_score
                no_improve_rounds += 1
        else:
            no_improve_rounds += 1

        if no_improve_rounds >= llm_config.early_stop_patience and round_id > 1:
            early_stop = True

        trace_records.append(
            RoundTraceRecord(
                series_name=series_name,
                round_id=round_id,
                previous_best_spec=(
                    None
                    if len(trace_records) == 0 or trace_records[-1].round_best_spec is None
                    else trace_records[-1].round_best_spec
                ),
                previous_best_score=(
                    None
                    if len(trace_records) == 0 or trace_records[-1].round_best_score is None
                    else trace_records[-1].round_best_score
                ),
                analyst_feedback_summary=analyst_feedback_summary,
                new_specs=[
                    f"{row['raw_structure_name']}|fractional={int(bool(row['raw_fractional']))}|obs={row['raw_observation_map']}"
                    + (f"|delay={int(row['raw_delay_weeks'])}" if int(row["raw_delay_weeks"]) > 0 else "")
                    for _, row in round_output["proposal_audit"].iterrows()
                ],
                round_best_spec=None if round_best_spec is None else round_best_spec.spec_key,
                round_best_score=round_best_score,
                score_improvement=score_improvement,
                early_stop=early_stop,
            )
        )

        if early_stop:
            break

    if best_output is None or best_output["selection_artifact"] is None:
        raise RuntimeError(f"LLM-V1 produced no evaluated candidates for series={series_name}")

    final_spec_dict = best_output["selection_artifact"]["best_spec"]
    final_spec = StructureSpec(
        structure_name=str(final_spec_dict["structure_name"]),
        fractional=bool(final_spec_dict["fractional"]),
        observation_map=str(final_spec_dict["observation_map"]),
        delay_weeks=int(final_spec_dict["delay_weeks"]),
    )
    final_test_metrics = evaluate_selected_spec_on_test(
        spec=final_spec,
        y=y,
        split=split,
        fit_config=fit_config,
        search_config=search_config,
        seed=seed,
    )
    final_provider_metadata = best_output["provider_metadata"]
    final_selected_candidate = {
        "series_name": series_name,
        "selected_round_id": int(best_output["round_id"]),
        "best_spec": final_spec_dict,
        "selection_score": float(best_output["selection_artifact"]["selection_score"]),
        "selection_validation_mae": float(best_output["selection_artifact"]["selection_validation_mae"]),
        "selection_rolling_mean_mae": float(best_output["selection_artifact"]["selection_rolling_mean_mae"]),
        **final_provider_metadata,
    }
    write_json(final_selected_candidate, artifact_dir / "best_validation_candidate.json")
    write_json(final_selected_candidate, artifact_dir / "final_selected_candidate.json")
    final_test_report = pd.DataFrame(
        [
            {
                "series_name": series_name,
                "selected_round_id": int(best_output["round_id"]),
                "structure_name": final_spec.structure_name,
                "fractional": final_spec.fractional,
                "observation_map": final_spec.observation_map,
                "delay_weeks": final_spec.delay_weeks,
                "test_mae": float(final_test_metrics["test_mae"]),
                "test_rmse": float(final_test_metrics["test_rmse"]),
                "test_smape": float(final_test_metrics["test_smape"]),
                **final_provider_metadata,
            }
        ]
    )
    final_test_report.to_csv(artifact_dir / "final_selected_test_report.csv", index=False)
    write_refinement_trace_jsonl(trace_records, artifact_dir / "llm_refinement_trace.jsonl")
    write_refinement_trace_markdown(trace_records, artifact_dir / "llm_refinement_trace.md")
    return {
        "series_name": series_name,
        "artifact_dir": artifact_dir,
        "round_outputs": round_outputs,
        "trace_records": trace_records,
        "best_output": best_output,
        "final_selected_candidate": final_selected_candidate,
        "final_test_report": final_test_report,
        "provider_metadata": final_provider_metadata,
    }


def write_llm_global_outputs(
    series_outputs: list[dict[str, Any]],
    llm_config: LLMConfig,
    output_root: Path,
) -> dict[str, Path]:
    output_root = ensure_dir(output_root)
    audit_tables = {item["series_name"]: item["proposal_audit"] for item in series_outputs}
    summary_rows = [
        build_series_comparison_row(
            series_name=item["series_name"],
            llm_leaderboard=item["llm_leaderboard"],
            selected_spec=item["selection_artifact"]["best_spec"],
            selected_test_metrics=item["selected_test_metrics"],
            proposal_audit=item["proposal_audit"],
            llm_config=llm_config,
        )
        for item in series_outputs
    ]
    summary = pd.DataFrame(summary_rows).sort_values("series_name").reset_index(drop=True)
    for item in series_outputs:
        series_row = summary.loc[summary["series_name"] == item["series_name"]].copy()
        series_row.to_csv(item["artifact_dir"] / "llm_vs_nonllm_summary.csv", index=False)
    valid_rate = build_valid_proposal_rate_table(audit_tables, llm_config)
    candidate_efficiency = build_candidate_efficiency_table(summary, llm_config)
    semantic_alignment = build_semantic_alignment_table(summary, audit_tables, llm_config)

    summary_path = output_root / "llm_vs_nonllm_summary.csv"
    valid_rate_path = output_root / "llm_valid_proposal_rate.csv"
    efficiency_path = output_root / "llm_candidate_efficiency.csv"
    semantic_alignment_path = output_root / "llm_semantic_alignment.csv"
    summary.to_csv(summary_path, index=False)
    valid_rate.to_csv(valid_rate_path, index=False)
    candidate_efficiency.to_csv(efficiency_path, index=False)
    semantic_alignment.to_csv(semantic_alignment_path, index=False)
    report_path = output_root.parent / "reports" / "llm_v0_report.md"
    write_llm_v0_report(summary, report_path, llm_config)
    return {
        "summary": summary_path,
        "valid_proposal_rate": valid_rate_path,
        "candidate_efficiency": efficiency_path,
        "semantic_alignment": semantic_alignment_path,
        "report": report_path,
    }


def write_llm_v1_global_outputs(
    series_outputs: list[dict[str, Any]],
    llm_config: LLMConfig,
    output_root: Path,
) -> dict[str, Path]:
    output_root = ensure_dir(output_root)
    v0_summary = load_v0_summary(llm_config)
    summary_rows = [
        build_llm_v1_comparison_row(
            series_output=item,
            llm_config=llm_config,
            v0_summary=v0_summary,
        )
        for item in series_outputs
    ]
    summary = pd.DataFrame(summary_rows).sort_values("series_name").reset_index(drop=True)
    for item in series_outputs:
        series_row = summary.loc[summary["series_name"] == item["series_name"]].copy()
        series_row.to_csv(item["artifact_dir"] / "llm_v1_vs_v0_vs_nonllm_summary.csv", index=False)

    by_round = build_valid_proposal_rate_by_round_table(series_outputs, llm_config)
    candidate_efficiency = build_llm_v1_candidate_efficiency_table(summary, llm_config)
    refinement_improvement = build_llm_v1_refinement_improvement_table(series_outputs, summary, llm_config)
    semantic_alignment = build_llm_v1_semantic_alignment_table(series_outputs, llm_config)

    summary_path = output_root / "llm_v1_vs_v0_vs_nonllm_summary.csv"
    by_round_path = output_root / "llm_v1_valid_proposal_rate_by_round.csv"
    efficiency_path = output_root / "llm_v1_candidate_efficiency.csv"
    refinement_path = output_root / "llm_v1_refinement_improvement.csv"
    semantic_alignment_path = output_root / "llm_v1_semantic_alignment.csv"
    summary.to_csv(summary_path, index=False)
    by_round.to_csv(by_round_path, index=False)
    candidate_efficiency.to_csv(efficiency_path, index=False)
    refinement_improvement.to_csv(refinement_path, index=False)
    semantic_alignment.to_csv(semantic_alignment_path, index=False)
    report_path = output_root.parent / "reports" / "llm_v1_iterative_report.md"
    write_llm_v1_report(summary, refinement_improvement, report_path, llm_config)
    return {
        "summary": summary_path,
        "valid_proposal_rate_by_round": by_round_path,
        "candidate_efficiency": efficiency_path,
        "refinement_improvement": refinement_path,
        "semantic_alignment": semantic_alignment_path,
        "report": report_path,
    }
