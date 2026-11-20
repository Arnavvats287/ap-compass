"""Verify that the site's curated downloads contain only byte-pinned synthetic invoices."""

from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend/public/demo-data"
BUNDLE = "ap-compass-demo-invoices.zip"
PDFS = {
    "08-northstar-supplies.pdf": "7b35c99758e70703dc23c80fc1b3eb4683c1ae3499e83cc9ea333258586a8005",
    "AS-2611-632.pdf": "230016e9c6a655f754eb5b990a7204a64470dced3c14b5c22bd51efdfd2e992f",
    "KLG-2611-876.pdf": "2aa415f106cdbe6216bd8bb59126650a38d8f8c492a2933125c346e152fa3746",
    "MCL-26-4573.pdf": "881163cc762412625f15f956d276d1f2559fba84c590172e036fed80a8656963",
    "MCL-26-4681.pdf": "c9e8fb3a416124a7ca93586a01291bd05dc28b7609cf4c4c4ba94b7c61c64452",
    "NS-26-5942.pdf": "8103e41c05d939beb18467a82fd99d87d50d306579134ba252b9a248ba3c7186",
    "OOP-2611-617.pdf": "6355af5604fa1d4d2b2a0099b86e5ec9fb77817359d012aaa8e846b268c9aaee",
}


def main():
    assert {item.name for item in PUBLIC.iterdir()} == {*PDFS, BUNDLE}
    with ZipFile(PUBLIC / BUNDLE) as bundle:
        assert sorted(bundle.namelist()) == sorted(PDFS)
        for name, expected in PDFS.items():
            pdf = (PUBLIC / name).read_bytes()
            assert pdf.startswith(b"%PDF-") and len(pdf) <= 8 * 1024 * 1024, name
            assert sha256(pdf).hexdigest() == expected, name
            assert bundle.read(name) == pdf, name
    print(f"Verified {len(PDFS)} pinned PDFs and one PDF-only ZIP.")
    print(f"ZIP SHA-256: {sha256((PUBLIC / BUNDLE).read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
