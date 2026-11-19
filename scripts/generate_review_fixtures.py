"""Generate only the authorized human-resolution regression PDFs; frozen oracle is read-only."""
import json
from generate_fixtures import ROOT, generate


def main():
    cases=json.loads((ROOT/'data/human_resolution_manifest.json').read_text())['fixture_cases']
    cases += [c for c in json.loads((ROOT/'data/fixture_manifest.json').read_text())['fixture_cases'] if c['id']=='AMBIGUOUS_PO']
    generate(ROOT/'tests/fixtures/human_resolution',ids=tuple(c['id'] for c in cases),cases=cases)


if __name__=='__main__': main()
