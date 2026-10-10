# 0003 Validator unit tests use in-memory contract vectors

Status: adopted.

`pipeline/test_validate.py` builds small in-memory records (site_id `contract-test`) that deliberately break each contract rule, so we can check the validator rejects them. They are not measurements. They are never written to `data/`, `artifacts/` or exports, and they never reach the UI. Reason: rule coverage is needed before real exports exist. Integration checks on real data run `python -m pipeline.validate` against the genuine exports.
