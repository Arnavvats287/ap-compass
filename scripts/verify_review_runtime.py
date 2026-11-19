"""Read-only verification of a migrated demo copy and its persisted human reassessments."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.contracts import RunSnapshotV1, VendorV1, PurchaseOrderV1, PriorBilledInvoiceV1
from app.orchestration.reviews import ReviewActionSnapshot, fingerprint


def readonly(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('Existing SQLite database required')
    return sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)


def verify(database, baseline):
    with readonly(database) as current, readonly(baseline) as original:
        tables = ('vendor', 'purchase_order', 'po_line', 'prior_billed_invoice',
                  'invoice_run', 'run_stage', 'policy_snapshot')
        counts = {}
        for table in tables:
            key = 'version' if table == 'policy_snapshot' else 'id'
            rows = original.execute(f'SELECT * FROM {table} ORDER BY {key}').fetchall()
            for row in rows:
                assert current.execute(f'SELECT * FROM {table} WHERE {key}=?', (row[0],)).fetchone() == row
            counts[table] = len(rows)
        authority = []
        for table, contract in (('vendor',VendorV1), ('purchase_order',PurchaseOrderV1),
                                ('prior_billed_invoice',PriorBilledInvoiceV1)):
            authority.append([contract.model_validate_json(row[0]).model_dump(mode='json')
                              for row in current.execute(f'SELECT payload FROM {table} ORDER BY id')])
        authority_id = fingerprint(authority)
        actions = []
        for run_id, payload in current.execute('SELECT run_id,payload FROM review_action ORDER BY id'):
            action = ReviewActionSnapshot.model_validate_json(payload)
            run = RunSnapshotV1.model_validate_json(current.execute(
                'SELECT payload FROM invoice_run WHERE id=?', (run_id,)).fetchone()[0])
            assert fingerprint(run.model_copy(update={'stages':()}).model_dump(mode='json')) == action.source_snapshot_fingerprint
            assert action.original_decision == run.decision
            assert action.policy_snapshot == run.policy_snapshot
            actions.append({'run_id':run_id, 'action_id':action.id, 'original':run.decision.outcome,
                            'reassessed':action.reassessment.outcome,
                            'authority_matches_current':action.authority_fingerprint == authority_id})
        return {'prior_rows_unchanged':True, 'baseline_counts':counts, 'actions':actions,
                'authority_fingerprint':authority_id, 'review_count':len(actions)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True)
    parser.add_argument('--baseline',required=True)
    parser.add_argument('--output')
    args = parser.parse_args()
    report = verify(args.db,args.baseline)
    if args.output:
        Path(args.output).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
