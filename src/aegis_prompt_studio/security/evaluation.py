from __future__ import annotations

import hashlib
from importlib.resources import files
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from aegis_prompt_studio.models import SecurityCategory
from aegis_prompt_studio.security.scanner import PromptSecurityScanner


class BenchmarkCase(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    text: str = Field(min_length=1)
    expected_threat: bool
    expected_categories: list[SecurityCategory] = Field(default_factory=list)

    @model_validator(mode="after")
    def categories_match_label(self) -> BenchmarkCase:
        if self.expected_categories and not self.expected_threat:
            raise ValueError("benign cases cannot declare expected threat categories")
        return self


class BenchmarkDataset(BaseModel):
    version: str
    description: str
    cases: list[BenchmarkCase] = Field(min_length=1)

    @model_validator(mode="after")
    def case_ids_are_unique(self) -> BenchmarkDataset:
        case_ids = [case.id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("benchmark case IDs must be unique")
        if not any(case.expected_threat for case in self.cases):
            raise ValueError("benchmark must contain threat cases")
        if not any(not case.expected_threat for case in self.cases):
            raise ValueError("benchmark must contain benign cases")
        return self


class EvaluationFailure(BaseModel):
    case_id: str
    expected_threat: bool
    predicted_threat: bool
    risk_score: int
    expected_categories: list[SecurityCategory]
    detected_categories: list[SecurityCategory]


class SecurityEvaluationReport(BaseModel):
    dataset_version: str
    dataset_sha256: str
    risk_threshold: int
    total_cases: int
    threat_cases: int
    benign_cases: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    specificity: float
    accuracy: float
    f1: float
    per_category_recall: dict[str, float]
    failures: list[EvaluationFailure]

    def meets_policy(self, min_precision: float, min_recall: float, min_f1: float) -> bool:
        return (
            self.precision >= min_precision
            and self.recall >= min_recall
            and self.f1 >= min_f1
        )


def load_benchmark(path: str | Path | None = None) -> tuple[BenchmarkDataset, str]:
    if path is None:
        payload = files("aegis_prompt_studio").joinpath("data/security_benchmark.json").read_bytes()
    else:
        payload = Path(path).read_bytes()
    dataset = BenchmarkDataset.model_validate_json(payload)
    return dataset, hashlib.sha256(payload).hexdigest()


def evaluate_scanner(
    scanner: PromptSecurityScanner | None = None,
    dataset_path: str | Path | None = None,
    risk_threshold: int = 12,
) -> SecurityEvaluationReport:
    """Evaluate scanner classification and category coverage on a versioned corpus."""
    if not 0 <= risk_threshold <= 100:
        raise ValueError("risk_threshold must be between 0 and 100")
    dataset, digest = load_benchmark(dataset_path)
    active_scanner = scanner or PromptSecurityScanner()

    true_positives = false_positives = true_negatives = false_negatives = 0
    failures: list[EvaluationFailure] = []
    category_totals: dict[SecurityCategory, int] = {}
    category_hits: dict[SecurityCategory, int] = {}

    for case in dataset.cases:
        result = active_scanner.scan(case.text)
        predicted_threat = result.risk_score >= risk_threshold
        detected = {finding.category for finding in result.findings}

        if case.expected_threat and predicted_threat:
            true_positives += 1
        elif case.expected_threat:
            false_negatives += 1
        elif predicted_threat:
            false_positives += 1
        else:
            true_negatives += 1

        missing_category = False
        for category in case.expected_categories:
            category_totals[category] = category_totals.get(category, 0) + 1
            if category in detected:
                category_hits[category] = category_hits.get(category, 0) + 1
            else:
                missing_category = True

        if predicted_threat != case.expected_threat or missing_category:
            failures.append(
                EvaluationFailure(
                    case_id=case.id,
                    expected_threat=case.expected_threat,
                    predicted_threat=predicted_threat,
                    risk_score=result.risk_score,
                    expected_categories=case.expected_categories,
                    detected_categories=sorted(detected, key=lambda item: item.value),
                )
            )

    total = len(dataset.cases)
    precision = _ratio(true_positives, true_positives + false_positives)
    recall = _ratio(true_positives, true_positives + false_negatives)
    specificity = _ratio(true_negatives, true_negatives + false_positives)
    accuracy = _ratio(true_positives + true_negatives, total)
    f1 = _ratio(2 * precision * recall, precision + recall)
    per_category_recall = {
        category.value: _ratio(category_hits.get(category, 0), count)
        for category, count in sorted(category_totals.items(), key=lambda item: item[0].value)
    }

    return SecurityEvaluationReport(
        dataset_version=dataset.version,
        dataset_sha256=digest,
        risk_threshold=risk_threshold,
        total_cases=total,
        threat_cases=true_positives + false_negatives,
        benign_cases=true_negatives + false_positives,
        true_positives=true_positives,
        false_positives=false_positives,
        true_negatives=true_negatives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        specificity=specificity,
        accuracy=accuracy,
        f1=f1,
        per_category_recall=per_category_recall,
        failures=failures,
    )


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0
