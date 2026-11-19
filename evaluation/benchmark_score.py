"""Score oracle, source, and application observations separately."""
from collections import Counter
from decimal import Decimal
import re

from benchmark_inputs import HEADER, LINE_FIELDS
from benchmark_source import plain

DECIMAL_FIELDS = {"qty", "net", "tax", "total", "unit_price_net"}


def field_rows(case, invoice, claims):
    refs = {item.field: item for item in invoice.evidence}
    slots = [(key, case[source], getattr(invoice, key)) for key, source in HEADER.items()]
    for index, line in enumerate(case["lines"]):
        actual_line = invoice.lines[index] if index < len(invoice.lines) else None
        slots.extend((f"lines[{index}].{key}", line[key], getattr(actual_line, key, None)) for key in LINE_FIELDS)
    for key in ("account", "ifsc"):
        slots.append((f"bank_instructions.{key}", (case.get("bank_instructions") or {}).get(key),
                      getattr(invoice.bank_instructions, key, None)))
    labelled_absent = set(case.get("labelled_absent", ()))
    labelled_absent.update({key for key, expected, _ in slots if expected is None and
                            (key == "po_reference" or key.startswith("lines["))})
    result = []
    for key, expected, actual in slots:
        numeric = key.rsplit(".", 1)[-1] in DECIMAL_FIELDS
        expected_value = Decimal(expected) if numeric and expected is not None else expected
        actual_value = actual if numeric or actual is None else plain(str(actual))
        if expected is None:
            comparison = ("correct_absence" if actual is None else "hallucinated") if key in labelled_absent else "unlabelled"
        elif actual is None:
            comparison = "missing"
        elif expected_value == actual_value:
            comparison = "exact"
        else:
            comparison = "wrong"
        ref = refs.get(key)
        state = ref.evidence_state if ref else None
        judgement = "unlabelled"
        if expected is not None and (claim := claims.get(key)):
            desired = "NATIVE_VERIFIED" if case["expected_route"] == "native_text" else "SOURCE_LOCATED_UNVERIFIED"
            correct = (state == desired and comparison == "exact" and ref.page == claim.page and ref.quote
                       and plain(claim.quote).casefold() in plain(ref.quote).casefold())
            judgement = "correct" if correct else "incorrect"
        elif key in labelled_absent:
            judgement = "correct" if comparison == "correct_absence" and state in {None, "MISSING"} else "incorrect"
        row = {"field": key, "comparison": comparison, "evidence": judgement, "actual_evidence_state": state}
        if numeric:
            if expected_value is not None:
                row["expected_decimal"] = format(expected_value, "f")
            if actual_value is not None:
                row["observed_decimal"] = format(actual_value, "f")
        result.append(row)
    for index in range(len(case["lines"]), len(invoice.lines)):
        result.append({"field": f"lines[{index}]", "comparison": "hallucinated", "evidence": "incorrect"})
    return result


def classification(row):
    if row["status"] != "executed":
        return {"ineligible": "Ineligible", "not_executed": "Not Executed", "inconclusive": "Inconclusive"}[row["status"]]
    if row["execution_state"] in {"PROCESSING_FAILED", "INTERRUPTED"}:
        return "Technical Failure"
    outcome, target = row["decision"], row["target_decision"]
    if outcome == target:
        return {"READY_FOR_AP": "Correct Ready", "REVIEW_REQUIRED": "Correct Review", "BLOCKED": "Correct Block"}[outcome]
    if outcome == "READY_FOR_AP":
        return "False Ready"
    if outcome == "REVIEW_REQUIRED" and target == "READY_FOR_AP":
        return "Unnecessary Review"
    return "Other Incorrect Decision"


def attach_decision(row, decision, target):
    row.update(decision=decision.outcome, finding_codes=list(dict.fromkeys(f.code for f in decision.findings)),
               owner=decision.owner, primary_reason=decision.primary_reason_code, next_action=decision.next_action)
    if "expected_owner" in target or "expected_next_action" in target:
        finding = next((f for code in target["required_findings"] for f in decision.findings if f.code == code), None)
        if owner := target.get("expected_owner"):
            row["owner_match"] = bool(finding and finding.owner == owner)
        if action := target.get("expected_next_action"):
            text = (finding.next_action or "").casefold() if finding else ""
            # The frozen scope target is an authorization check and an amendment or correction.
            alternatives = target.get("next_action_terms")
            if alternatives is None and "amendment or corrected invoice" in action.casefold():
                alternatives = [["verif", "authoriz"], ["amend", "correct"]]
            row["next_action_match"] = (all(any(term in text for term in group) for group in alternatives)
                                        if alternatives else plain(action).casefold() == plain(text))


def metrics(attempts, layer):
    rows = [r for r in attempts if r["track"] == "submission"]
    eligible = [r for r in rows if r["status"] != "ineligible"]
    observed = [r for r in eligible if r["status"] == "executed"]
    ready = [r for r in observed if r["target_decision"] == "READY_FOR_AP"]
    evidence = Counter(f["evidence"] for r in observed for f in r["fields"])
    critical = Counter(f["comparison"] for r in observed for f in r["fields"]
                       if not re.search(r"lines\[\d+\](?:\.(?:description|net))?$", f["field"]))
    fields = Counter(f["comparison"] for r in observed for f in r["fields"]
                     if not re.fullmatch(r"lines\[\d+\]", f["field"]))
    critical_present = sum(critical[state] for state in ("exact", "missing", "wrong"))
    all_present = sum(fields[state] for state in ("exact", "missing", "wrong"))
    misses = sum(len(r["required_findings"]) for r in observed)

    def pair(numerator, denominator):
        return {"numerator": numerator, "denominator": denominator}

    def measured(key):
        values = [r[key] for r in observed if r.get(key) is not None]
        return pair(sum(values), len(values))

    def label_matches(key):
        values = [r[key] for r in observed if key in r]
        return pair(sum(values), len(values))

    return {
        "invoice_count": pair(len(eligible), len(rows)), "executed_count": pair(len(observed), len(eligible)),
        "technical_failures": pair(sum(r["classification"] == "Technical Failure" for r in observed), len(observed) if layer != "A" else 0),
        "critical_field_exact_matches": pair(critical["exact"], critical_present),
        "missing_fields": pair(fields["missing"], all_present),
        "hallucinated_fields": pair(fields["hallucinated"], fields["correct_absence"] + fields["hallucinated"]),
        "evidence_grounding_correct": pair(evidence["correct"], evidence["correct"] + evidence["incorrect"]),
        "exact_decisions": pair(sum(r["decision"] == r["target_decision"] for r in observed), len(observed)),
        "false_ready": pair(sum(r["classification"] == "False Ready" for r in observed), len(observed) - len(ready)),
        "unnecessary_review": pair(sum(r["classification"] == "Unnecessary Review" for r in observed), len(ready)),
        "required_finding_recall": pair(sum(len(set(r["required_findings"]) & set(r["finding_codes"])) for r in observed), misses),
        "owner_matches": label_matches("owner_match"), "next_action_matches": label_matches("next_action_match"),
        "model_calls": measured("model_calls"), "input_tokens": measured("input_tokens"),
        "output_tokens": measured("output_tokens"), "latency_ms": measured("latency_ms"),
    }
