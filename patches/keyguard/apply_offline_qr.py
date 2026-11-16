#!/usr/bin/env python3
"""Apply an anchor-checked, bundled ML Kit QR scanner patch to a Keyguard source tree.

Only scanner dependencies and error diagnostics change. Never log raw QR data:
FIDO:/ payloads include ephemeral authentication secrets.
"""
from pathlib import Path
import argparse


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def apply(root: Path, dry_run: bool) -> None:
    changes = []
    versions = root / "gradle/libs.versions.toml"
    original = versions.read_text(encoding="utf-8")
    updated = replace_once(
        original,
        'mlkitBarcodeScanning = "18.3.1"',
        'mlkitBarcodeScanning = "17.3.0"',
        "ML Kit version",
    )
    updated = replace_once(
        updated,
        'google-play-services-mlkit-barcode-scanning = { module = "com.google.android.gms:play-services-mlkit-barcode-scanning", version.ref = "mlkitBarcodeScanning" }',
        'google-mlkit-barcode-scanning = { module = "com.google.mlkit:barcode-scanning", version.ref = "mlkitBarcodeScanning" }',
        "ML Kit bundled model catalog alias",
    )
    changes.append((versions, updated))

    gradle = root / "feature/qr-scanner-android/build.gradle.kts"
    original = gradle.read_text(encoding="utf-8")
    updated = replace_once(
        original,
        "implementation(libs.google.play.services.mlkit.barcode.scanning)",
        "implementation(libs.google.mlkit.barcode.scanning)",
        "Scanner dependency",
    )
    changes.append((gradle, updated))

    screen = root / "feature/qr-scanner-android/src/main/kotlin/com/artemchep/keyguard/feature/qr/ScanQrScreen.kt"
    original = screen.read_text(encoding="utf-8")
    updated = replace_once(
        original,
        "import android.annotation.SuppressLint\n",
        "import android.annotation.SuppressLint\nimport android.util.Log\n",
        "Android logger import",
    )
    updated = replace_once(
        updated,
        """    DisposableEffect(analyzerExecutor) {
        onDispose {
            analyzerExecutor.shutdown()
        }
    }
""",
        """    DisposableEffect(analyzerExecutor, analyzer) {
        onDispose {
            analyzer.close()
            analyzerExecutor.shutdown()
        }
    }
""",
        "Scanner lifecycle cleanup",
    )
    updated = replace_once(
        updated,
        """                    } catch (_: Exception) {
                        // Camera is unavailable.
                    }
""",
        """                    } catch (e: Exception) {
                        Log.e("KeyguardQrScan", "Camera binding failed", e)
                    }
""",
        "Camera bind diagnostics",
    )
    old_analyzer = """private class QrImageAnalyzer(
    private val onReadBarcode: (barcodes: List<Barcode>) -> Unit,
) : ImageAnalysis.Analyzer {
    override fun analyze(imageProxy: ImageProxy) {
        scanBarcode(imageProxy)
    }

    @SuppressLint("UnsafeOptInUsageError")
    @OptIn(ExperimentalGetImage::class)
    private fun scanBarcode(imageProxy: ImageProxy) {
        imageProxy.image?.let { image ->
            val inputImage = InputImage.fromMediaImage(image, imageProxy.imageInfo.rotationDegrees)
            val scanner = BarcodeScanning.getClient()
            scanner
                .process(inputImage)
                .addOnCompleteListener {
                    imageProxy.close()

                    if (it.isSuccessful) onReadBarcode(it.result as List<Barcode>)
                }
        }
    }
}
"""
    new_analyzer = """private class QrImageAnalyzer(
    private val onReadBarcode: (barcodes: List<Barcode>) -> Unit,
) : ImageAnalysis.Analyzer {
    // Reuse the bundled model instead of recreating a scanner for every camera frame.
    private val scanner = BarcodeScanning.getClient()

    fun close() {
        scanner.close()
    }

    @SuppressLint("UnsafeOptInUsageError")
    @OptIn(ExperimentalGetImage::class)
    override fun analyze(imageProxy: ImageProxy) {
        val image = imageProxy.image
        if (image == null) {
            imageProxy.close()
            return
        }
        try {
            val inputImage = InputImage.fromMediaImage(image, imageProxy.imageInfo.rotationDegrees)
            scanner.process(inputImage).addOnCompleteListener { task ->
                imageProxy.close()
                if (task.isSuccessful) {
                    val barcodes = task.result.orEmpty()
                    if (barcodes.isNotEmpty()) {
                        // Never log rawValue: a FIDO QR includes ephemeral secrets.
                        Log.i("KeyguardQrScan", "Barcode recognized (count=" + barcodes.size + ")")
                    }
                    onReadBarcode(barcodes)
                } else {
                    Log.w("KeyguardQrScan", "Barcode recognition failed", task.exception)
                }
            }
        } catch (e: Exception) {
            imageProxy.close()
            Log.e("KeyguardQrScan", "Barcode processing failed", e)
        }
    }
}
"""
    updated = replace_once(updated, old_analyzer, new_analyzer, "ML Kit analysis and diagnostics")
    changes.append((screen, updated))

    if not dry_run:
        for path, updated in changes:
            path.write_text(updated, encoding="utf-8")
    print("Bundled ML Kit scanner patch anchors passed; no QR content logging.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    apply(args.source, args.dry_run)
