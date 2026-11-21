# Original component and checkpoint tests

This directory preserves the original Python scripts and recorded outcomes for the storage-deletion and historical-checkpoint experiments discussed in Sections IV and VI.A of *After the Clawback: Revocation Closure in Agentic Legal Workflows*.

The scripts under `source/` come unchanged from fixed commits of `risu-research/formal-exec-2609`. `verify_historical.py` checks the Git blob hash of all seven scripts and the results recorded in `component_results.json` and `checkpoint_results.json`. The original component evidence was recovered from the October 2, 2026 research handoff. The two seven-case checkpoint archives were recovered from the November 20, 2026 Section VI.A audit handoff.

## Check the recorded evidence

From the repository root:

```sh
python experiments/component_history/verify_historical.py
```

This check uses only Python's standard library. It verifies five original component-stack runs and the 14 individual recorded checkpoint replays, including per-case SQL rows and decisions. It does not claim to regenerate the original historical container images or their ephemeral SQLite files.

## Source studies and recorded runs

| Study | Source | GitHub Actions run |
| --- | --- | --- |
| Chroma and Qdrant record deletion | `source/chroma_qdrant.py` | [36926079202](https://github.com/risu-research/formal-exec-2609/actions/runs/36926079202) |
| Haystack, LlamaIndex and LangGraph | `source/haystack_llama_base.py` | [36926310521](https://github.com/risu-research/formal-exec-2609/actions/runs/36926310521) |
| LlamaIndex default/strict deletion, Haystack filtering, LangGraph history | `source/haystack_llama_followup.py` | [36926948898](https://github.com/risu-research/formal-exec-2609/actions/runs/36926948898) |
| Chroma and Qdrant feeding LangGraph | `source/composed_chroma_langgraph.py` | [36927069080](https://github.com/risu-research/formal-exec-2609/actions/runs/36927069080) |
| PostgreSQL 16 with PostgresSaver | `source/postgres_saver.py` | [36927335530](https://github.com/risu-research/formal-exec-2609/actions/runs/36927335530) |
| Seven InMemorySaver checkpoint-to-SQL cases | `source/replay_inmemory.py` | [44450492824](https://github.com/risu-research/formal-exec-2609/actions/runs/44450492824) |
| Seven PostgresSaver checkpoint-to-SQL cases | `source/replay_postgres.py` | [44450716347](https://github.com/risu-research/formal-exec-2609/actions/runs/44450716347) |

The original source-retrieval experiments used Haystack 3.3.0, LlamaIndex Core 0.14.25, LangGraph 1.2.12, and PostgresSaver 3.1.2. The historical container IDs and exact version information are retained in `component_results.json` and in the linked original run records. The original five source experiments were recorded with constructed source and mixed-document markers, rather than client data.

The original component outputs demonstrate that deleting an identified source document or point need not delete an independently created mixed artifact. The separate LlamaIndex follow-up tests the difference between default index deletion and `delete_from_docstore=True`. The LangGraph and PostgreSQL runs show the latest state repaired with 3 of 4 historical checkpoints still containing the revoked marker. The two seven-case replays isolate whether a resumed checkpoint leads to a new physical SQL write under each guard.

## Evidence boundaries

The historical five component runs were independently recovered as original GitHub Actions result ZIPs, and their SHA-256 values matched the previously archived ledger. The complete submitted handoff is not part of this public repository. The minimal recorded scenario results and the original immutable script hashes are included here instead.

The seven-case original replay scripts created temporary SQLite databases and discarded them after collecting each database's actual `effects` rows. The recorded per-case rows, independent read-only audit and GitHub Actions logs are preserved. A fresh run may use a separate evidence-capture wrapper to retain newly generated databases, but those are distinct from the original 2026 DB files.
