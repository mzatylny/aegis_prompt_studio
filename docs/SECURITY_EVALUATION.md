# Security evaluation

## Purpose

The scanner is evaluated as a binary classifier and as a category detector. The versioned corpus lives in `src/aegis_prompt_studio/data/security_benchmark.json`, ships with the package, and is hashed in every report so results can be traced to the exact input set.

The baseline corpus contains 41 cases:

- 21 adversarial cases spanning all 10 scanner categories
- 20 benign cases, including security terminology that should not trigger by itself
- plain, URL-encoded, Base64, hexadecimal, ROT13, zero-width, markup, direct, and indirect payloads

## Metrics and policy

At risk threshold 12, the v1.0.0 corpus produces:

| Metric | Baseline |
|---|---:|
| Precision | 100% |
| Recall | 100% |
| Specificity | 100% |
| Accuracy | 100% |
| F1 | 100% |
| Per-category recall | 100% for all 10 categories |

CI requires precision, recall, and F1 of at least 90%. A perfect result on this curated regression corpus does **not** establish production accuracy or robustness against novel attacks. It establishes that known behavior does not regress.

Run the gate locally:

```bash
aegis evaluate --min-precision 0.90 --min-recall 0.90 --min-f1 0.90
```

Write a machine-readable report:

```bash
aegis evaluate --json-out reports/security-evaluation.json
```

## Adding cases

Every scanner rule change should add at least:

1. one adversarial case that demonstrates the intended detection;
2. one nearby benign case that guards against an obvious false positive;
3. the expected category when the rule is category-specific.

Case identifiers are unique and stable. Corpus changes require a dataset version change, review of metric movement, and an explanation in the changelog.

## Known limitations

- The corpus is curated and small; it is not an unbiased sample of real traffic.
- The deterministic scanner cannot infer intent reliably from every linguistic context.
- Multilingual, multimodal, and application-specific payload coverage is limited.
- Precision measured here should not be used as a production probability estimate.
- Threshold selection must reflect the downstream action: warning, quarantine, or block.

Production validation should add representative, privacy-reviewed traffic samples, independent red-team cases, multilingual evaluation, and periodic drift review.
