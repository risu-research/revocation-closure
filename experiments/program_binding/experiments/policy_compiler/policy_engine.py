"""Executable, evidence-linked policy IR for three entered protective orders.

A small strict compiler accepts manually reviewed clauses. It does NOT interpret
PDFs, establish privilege, authorize real deletion, or certify legal compliance.
No external dependencies. Unknown information causes HOLD, never a purge.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any
import json
from pathlib import Path

CASES = frozenset({"iottie", "camm", "napoli"})
EVENTS = frozenset({"C_PRIV_NOTICE", "C_PRIV_DISPUTED", "C_PRIV_SELF_DISCOVERY",
                    "PRIVILEGE_CHALLENGE", "FINAL_TERMINATION", "CONFIDENTIALITY_REDESIGNATION",
                    "NO_PRIVILEGED_INFORMATION"})
ACTIONS = frozenset({"USE", "SHARE", "EXTERNAL_EFFECT", "RETAIN", "ARCHIVE",
                     "RETURN", "SEQUESTER", "DESTROY_SOURCE", "DELETE_WHOLE_NOTE",
                     "REDACT_AFFECTED_SPAN", "PRIVILEGE_CHALLENGE", "INSPECT"})
KINDS = frozenset({"source_copy", "mixed_note", "summary", "independent_note",
                   "legal_memo", "work_product_index", "confidential_inspection_note"})
FIELDS = frozenset({"contains_specified", "confidential_information_included",
                    "reproduces_confidential_text", "fragment_locations_verified",
                    "counsel_record", "qualified_archive", "explicit_challenge_authorization",
                    "is_covered_final_material", "claim_active", "protected_material", "inspection_note"})
EFFECTS = frozenset({"RESTRICT_CLAIMED_CONTENT", "REMEDIATE_SPECIFIED_SOURCE",
                     "CONDITIONAL_COPY_BRIDGE", "NO_GLOBAL_FINAL_SCOPE_BRIDGE",
                     "QUALIFIED_FINAL_ARCHIVE", "FINAL_DISPOSITION",
                     "INSPECTION_CONFIDENTIALITY", "LIMITED_CHALLENGE_COPY"})
OPERATIONS_WITH_SIDE_EFFECT = {"USE", "SHARE", "EXTERNAL_EFFECT", "INSPECT"}
DESTRUCTIVE = {"DESTROY_SOURCE", "DELETE_WHOLE_NOTE", "REDACT_AFFECTED_SPAN"}


class PolicyError(ValueError):
    pass


def stable_json(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class Rule:
    id: str
    case: str
    events: tuple[str, ...]
    effect: str
    object_kinds: tuple[str, ...]
    predicates: tuple[tuple[str, bool], ...]
    clause: str
    pdf: str
    pdf_page_1based: tuple[int, ...]
    deadline: dict[str, Any] | None
    interpretation: str
    origin: str


@dataclass(frozen=True)
class Decision:
    verdict: str
    active_effects: tuple[str, ...]
    rule_ids: tuple[str, ...]
    obligations: tuple[str, ...]
    permissible_remedies: tuple[str, ...]
    deadlines: tuple[dict[str, Any], ...]
    reason: str
    evidence: tuple[dict[str, Any], ...]
    policy_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CompiledPolicy:
    def __init__(self, rules: tuple[Rule, ...], digest: str, source_digest: str):
        self.rules = rules
        self.digest = digest
        self.source_digest = source_digest

    @classmethod
    def compile(cls, declaration: dict[str, Any]) -> "CompiledPolicy":
        if set(declaration) != {"schema_version", "rules", "limitations"}:
            raise PolicyError("Unexpected or missing declaration keys")
        if declaration["schema_version"] != "manual-court-clauses-v1":
            raise PolicyError("Unsupported declarations schema")
        raw_rules = declaration["rules"]
        if not isinstance(raw_rules, list) or not raw_rules:
            raise PolicyError("Expected nonempty rule list")
        ids: set[str] = set()
        rules: list[Rule] = []
        required = {"id", "case", "events", "effect", "object_kinds", "predicates",
                    "clause", "pdf", "pdf_page_1based", "deadline", "interpretation", "origin"}
        for item in raw_rules:
            if set(item) != required:
                raise PolicyError("Invalid rule field set")
            if not isinstance(item["id"], str) or item["id"] in ids:
                raise PolicyError("Nonunique rule id")
            ids.add(item["id"])
            if item["case"] not in CASES or item["effect"] not in EFFECTS:
                raise PolicyError("Unknown case/effect")
            if not item["events"] or not set(item["events"]).issubset(EVENTS):
                raise PolicyError("Unknown event")
            if not item["object_kinds"] or not set(item["object_kinds"]).issubset(KINDS):
                raise PolicyError("Unknown object kind")
            if not isinstance(item["predicates"], dict) or not set(item["predicates"]).issubset(FIELDS):
                raise PolicyError("Illegal predicate")
            if any(type(v) is not bool for v in item["predicates"].values()):
                raise PolicyError("Predicates must be boolean; unknown is a runtime value")
            if not item["pdf"].startswith("https://") or not item["clause"] or not item["pdf_page_1based"]:
                raise PolicyError("Missing source and page provenance")
            if not all(isinstance(p, int) and p > 0 for p in item["pdf_page_1based"]):
                raise PolicyError("Invalid page")
            dl = item["deadline"]
            if dl is not None:
                if set(dl) != {"start", "amount", "unit"} or dl["unit"] not in {"calendar_days", "business_days", "prompt", "months", "conditional"}:
                    raise PolicyError("Deadline schema error")
                if not isinstance(dl["amount"], int) or dl["amount"] < 0:
                    raise PolicyError("Deadline amount error")
            if item["origin"] not in {"COURT_TEXT", "FRCP26_INTERPRETATION", "TECHNICAL_SAFETY"}:
                raise PolicyError("Unlabeled legal/technical origin")
            rules.append(Rule(item["id"], item["case"], tuple(item["events"]), item["effect"],
                              tuple(item["object_kinds"]), tuple(sorted(item["predicates"].items())),
                              item["clause"], item["pdf"], tuple(item["pdf_page_1based"]), dl,
                              item["interpretation"], item["origin"]))
        normalized = [asdict(r) for r in rules]
        return cls(tuple(rules), sha256(stable_json(normalized).encode()).hexdigest(),
                   sha256(stable_json(declaration).encode()).hexdigest())

    def as_ir(self) -> dict[str, Any]:
        return {"schema":"revocation-policy-ir-v1", "compiler":"manual-clause-compiler-v1",
                "policy_digest":self.digest, "declaration_digest":self.source_digest,
                "rule_count":len(self.rules), "rules":[asdict(r) for r in self.rules],
                "interpretation_boundary":"Manual legal mapping; not generated from PDFs"}

    def decide(self, *, case:str, event:str, action:str, kind:str,
               facts:dict[str, bool | None], proof:dict[str, Any] | None = None) -> Decision:
        """Return normative decision, NEVER perform a destructive action.

        Missing facts produce a conservative HOLD for use effects, not an invented
        legal obligation. `proof` is used only for authorizing deliberate remediation.
        """
        if case not in CASES or event not in EVENTS or action not in ACTIONS or kind not in KINDS:
            raise PolicyError("Unknown case/event/action/object")
        if not isinstance(facts,dict) or not set(facts).issubset(FIELDS):
            raise PolicyError("Unknown facts")
        if any(v is not None and type(v) is not bool for v in facts.values()):
            raise PolicyError("Invalid fact value")
        proof = proof or {}
        if not isinstance(proof,dict):
            raise PolicyError("proof should be an object")
        active: list[Rule] = []
        uncertain: list[Rule] = []
        for r in self.rules:
            if r.case != case or event not in r.events or kind not in r.object_kinds:
                continue
            mismatched = False
            unknown = False
            for name,value in r.predicates:
                fv = facts.get(name)
                if fv is None:
                    unknown = True
                elif fv is not value:
                    mismatched = True
            if mismatched:
                continue
            (uncertain if unknown else active).append(r)
        eff = {r.effect for r in active}
        obligations: list[str] = []
        remedies: list[str] = []
        if "RESTRICT_CLAIMED_CONTENT" in eff:
            obligations.extend(["DO_NOT_USE_OR_DISCLOSE_SPECIFIED_INFORMATION",
                                "PROMPTLY_SEQUESTER_RETURN_OR_DESTROY_SPECIFIED_INFORMATION_AND_COPIES"])
            remedies.extend(["SEQUESTER", "RETURN", "DESTROY_SPECIFIED_CONTENT_WITH_AUTHORIZATION"])
        if "REMEDIATE_SPECIFIED_SOURCE" in eff:
            obligations.append("REMEDIATE_SPECIFIED_SOURCE_COPIES")
        if "CONDITIONAL_COPY_BRIDGE" in eff:
            obligations.append("COVERED_CONFIDENTIAL_SUMMARY_IS_A_COPY_FOR_CLAUSE_20")
        if "NO_GLOBAL_FINAL_SCOPE_BRIDGE" in eff:
            obligations.append("DO_NOT_IMPORT_FINAL_ONLY_DERIVATIVE_DEFINITION")
        if "FINAL_DISPOSITION" in eff:
            obligations.append("FINAL_RETURN_OR_DESTROY_QUALIFIED_MATERIAL")
        if "QUALIFIED_FINAL_ARCHIVE" in eff:
            remedies.append("RETAIN_QUALIFIED_COUNSEL_ARCHIVE_SUBJECT_TO_RESTRICTIONS")
        if "LIMITED_CHALLENGE_COPY" in eff:
            remedies.append("RETAIN_EXACTLY_ONE_CHALLENGE_COPY_FOR_NARROW_COURT_PROCEDURE")
        if "INSPECTION_CONFIDENTIALITY" in eff:
            obligations.append("MARK_INSPECTION_NOTES_AS_DESIGNATED_PROTECTED_MATERIAL")
        # Facts about active privilege claims apply across event types, including
        # final archive events. No counsel exception silently grants permission to use.
        affected = facts.get("contains_specified")
        active_claim = facts.get("claim_active")
        direct_restriction = "RESTRICT_CLAIMED_CONTENT" in eff
        use_blocked = direct_restriction or (active_claim is True and affected is True)
        uncertain_exposure = (affected is None and
                              event in {"C_PRIV_NOTICE","C_PRIV_DISPUTED","C_PRIV_SELF_DISCOVERY","FINAL_TERMINATION"})
        # The executor has no DELETE_WHOLE_NOTE operation. Whole-file destruction
        # always requires external human review, even after a qualified notice.
        if action == "DELETE_WHOLE_NOTE":
            verdict="REVIEW_REQUIRED"
            reason="No whole-note destruction instruction inferred; require independent legal/owner authorization"
        elif action in {"DESTROY_SOURCE", "REDACT_AFFECTED_SPAN"}:
            if not proof.get("human_approval_id") or not proof.get("exact_target_verified"):
                verdict="REVIEW_REQUIRED"
                reason="A verified target and a separate human authorization are required"
            elif action == "REDACT_AFFECTED_SPAN" and facts.get("fragment_locations_verified") is not True:
                verdict="REVIEW_REQUIRED"
                reason="Unverified span locations preclude automated partial removal"
            elif affected is False:
                verdict="OUT_OF_SCOPE"
                reason="Object has no identified claimed source information"
            elif affected is None:
                verdict="HOLD"
                reason="Target dependency unresolved; quarantine pending review"
            elif not (direct_restriction or "REMEDIATE_SPECIFIED_SOURCE" in eff or active_claim is True):
                verdict="REVIEW_REQUIRED"
                reason="No relevant live remediation authority in compiled rule set"
            else:
                verdict="PERMIT_HUMAN_AUTHORIZED_REMEDIATION"
                reason="Verified scoped target; permission is not an instruction to delete"
        elif action == "SEQUESTER":
            verdict="REQUIRED_OR_SAFE" if (use_blocked or uncertain_exposure) else "AVAILABLE"
            reason="Non-destructive isolation; not equivalent to deleting files"
        elif action == "RETURN":
            verdict="REMEDY_OPTION" if (direct_restriction or "REMEDIATE_SPECIFIED_SOURCE" in eff or "FINAL_DISPOSITION" in eff) else "REVIEW_REQUIRED"
            reason="Return is an option for a specified information/copy, not blanket return of unrelated notes"
        elif action == "ARCHIVE":
            if use_blocked or active_claim is True and affected is None:
                verdict="HOLD"
                reason="Final-archive permission does not override current privilege restrictions"
            elif "QUALIFIED_FINAL_ARCHIVE" in eff:
                verdict="ALLOW_RESTRICTED_STORAGE"
                reason="Only a qualifying counsel record, confidentiality obligations survive"
            elif uncertain:
                verdict="HOLD"
                reason="Archive eligibility not verified"
            else:
                verdict="NOT_ESTABLISHED"
                reason="No established exception for this object"
        elif action == "PRIVILEGE_CHALLENGE":
            if "LIMITED_CHALLENGE_COPY" in eff and proof.get("court_challenge_only") is True:
                verdict="ALLOW_CHALLENGE_ONLY"
                reason="Narrow single-copy exception; no wider use permission"
            elif case=="napoli" and event=="C_PRIV_DISPUTED" and proof.get("court_challenge_only") is True:
                verdict="ALLOW_CHALLENGE_ONLY"
                reason="Narrow in-camera privilege challenge only"
            else:
                verdict="REVIEW_REQUIRED"
                reason="No verified procedural exception for this scenario"
        elif action in OPERATIONS_WITH_SIDE_EFFECT or action=="RETAIN":
            if use_blocked:
                verdict="BLOCK"
                reason="Live restriction on specified asserted-privileged information"
            elif uncertain_exposure or (active_claim is None and affected is True):
                verdict="HOLD"
                reason="Insufficient evidence about content or current privilege status"
            elif action=="RETAIN" and "FINAL_DISPOSITION" in eff and "QUALIFIED_FINAL_ARCHIVE" not in eff:
                verdict="REVIEW_REQUIRED"
                reason="Final disposition obligation, no qualifying archive exception"
            elif action=="RETAIN" and active_claim is True and affected is True:
                verdict="BLOCK"
                reason="Cannot treat retained privilege copies as ordinary reusable materials"
            else:
                verdict="ALLOW_SCOPED"
                reason="No restriction established by modeled rule for this object/event, other duties remain"
        else:
            raise PolicyError("Unimplemented action")
        matched=tuple(sorted(active,key=lambda r:r.id))
        deadlines=[]; seen=set()
        for r in matched:
            if r.deadline and stable_json(r.deadline) not in seen:
                deadlines.append({"source_rule":r.id, **r.deadline})
                seen.add(stable_json(r.deadline))
        evidence=tuple({"rule_id":r.id,"clause":r.clause,"pdf":r.pdf,
                        "pages":r.pdf_page_1based,"origin":r.origin} for r in matched)
        # Add matched uncertainty to the evidence trace to avoid false negative.
        if uncertain:
            obligations.append("UNRESOLVED_FACTS_FOR_RULES:"+",".join(sorted(r.id for r in uncertain)))
        return Decision(verdict,tuple(sorted(eff)),tuple(r.id for r in matched),
                        tuple(sorted(set(obligations))),tuple(sorted(set(remedies))),
                        tuple(deadlines),reason,evidence,self.digest)


def load_default() -> CompiledPolicy:
    path=Path(__file__).with_name("verified_clause_rules.json")
    return CompiledPolicy.compile(json.loads(path.read_text(encoding="utf-8")))
