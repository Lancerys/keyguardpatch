#!/usr/bin/env python3
"""Switch only the ML Kit barcode dependency to the bundled model.

No QR scanner Kotlin source or application logic is changed.
"""
from pathlib import Path
import argparse


def replace_once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Upstream ML Kit dependency anchor changed (matches={count}): {old}")
    return source.replace(old, new, 1)


def apply(root: Path) -> None:
    catalog = root / "gradle/libs.versions.toml"
    scanner_build = root / "feature/qr-scanner-android/build.gradle.kts"
    versions = catalog.read_text(encoding="utf-8")
    build = scanner_build.read_text(encoding="utf-8")
    versions = replace_once(versions,
        'mlkitBarcodeScanning = "18.3.1"',
        'mlkitBarcodeScanning = "17.3.0"')
    versions = replace_once(versions,
        'google-play-services-mlkit-barcode-scanning = { module = "com.google.android.gms:play-services-mlkit-barcode-scanning", version.ref = "mlkitBarcodeScanning" }',
        'google-mlkit-barcode-scanning = { module = "com.google.mlkit:barcode-scanning", version.ref = "mlkitBarcodeScanning" }')
    build = replace_once(build,
        'implementation(libs.google.play.services.mlkit.barcode.scanning)',
        'implementation(libs.google.mlkit.barcode.scanning)')
    catalog.write_text(versions, encoding="utf-8")
    scanner_build.write_text(build, encoding="utf-8")
    print("Offline ML Kit dependency swap applied; only three dependency lines changed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    apply(parser.parse_args().source)
