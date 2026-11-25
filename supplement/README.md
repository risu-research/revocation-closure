# Supplementary research reproduction collection

This collection accompanies *After the Clawback: Revocation Closure in Agentic Legal Workflows*. Repository release v1.2.0 includes the exact supplementary package version 1.0.0. The earlier repository release v1.1.0 remains fixed at commit `43991454d3345a85f36464c6a6011e0b519a723d` and DOI [10.5281/zenodo.24412056](https://doi.org/10.5281/zenodo.24412056).

Download [revocation_closure_supplement_v1.0.0.zip](revocation_closure_supplement_v1.0.0.zip) from the release's source tree. Verify the archive before extracting it.

```sh
cd supplement
sha256sum -c SHA256SUMS
unzip revocation_closure_supplement_v1.0.0.zip -d /tmp/revocation-supplement
cd /tmp/revocation-supplement/revocation_closure_reproduction
python -m venv ../venv
. ../venv/bin/activate
python -m pip install -r requirements.txt
python -B verify_release.py
python -B verify_paper_results.py
python -B test_integration.py
python -B reproduce_all.py all --out ../results --workers 2
python -B verify_paper_results.py --fresh-results ../results/results
```

Read the extracted README, PAPER_TO_ARTIFACT.md, and EVIDENCE.md for the scope of each fixed synthetic experiment. The legacy verifier checks a pristine snapshot of the original release. The original framework workflows have separate dependencies and are described in the original reproduction guide. The supplement contains no actual client payloads or commercial provider credentials. The included software is licensed under MIT; linked court records and third-party software retain their terms.

The release is created only after the tracked archive, original source snapshot, module audits, full supplementary reproduction and manuscript-result recount pass the release workflow. The new version-specific DOI is assigned by Zenodo after release; the concept DOI [10.5281/zenodo.24410798](https://doi.org/10.5281/zenodo.24410798) identifies the version series.
