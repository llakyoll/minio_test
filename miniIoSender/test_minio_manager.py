# test_minio_manager.py
import numpy as np
import cv2
from minio_manager import MinIOManager

# ─── Bağlantı ───────────────────────────────────────────────
minio = MinIOManager(
    endpoint="localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin123",
    branch_name="Tepe Prime",
    secure=False,
    bucket_name="ai-outputs"
)

# ─── Yardımcı: sahte frame üret ─────────────────────────────
def make_frame(color=(100, 150, 200), label="TEST"):
    frame = np.full((480, 640, 3), color, dtype=np.uint8)
    cv2.putText(frame, label, (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    return frame

# ─── TEST 1: Basit görüntü yükleme ──────────────────────────
print("\n=== TEST 1: upload_image ===")
frame = make_frame(color=(60, 120, 200), label="Report1")
path = minio.upload_image(
    image=frame,
    folder="Masa Doluluk Analizi",
    filename="Report1.jpg"
)
print(f"Dönen path: {path}")
# Beklenen: "Tepe Prime/29-04-2026/Masa Doluluk Analizi/Report1.jpg"

# ─── TEST 2: branch_name olmadan yükleme ────────────────────
print("\n=== TEST 2: branch_name=None ===")
minio_no_branch = MinIOManager(
    endpoint="localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin123",
    branch_name=None,
    secure=False
)
frame2 = make_frame(color=(200, 60, 60), label="NoBranch")
path2 = minio_no_branch.upload_image(frame2, "Barista Analizi", "Alert1.jpg")
print(f"Dönen path: {path2}")
# Beklenen: "29-04-2026/Barista Analizi/Alert1.jpg"

# ─── TEST 3: Boş görüntü ────────────────────────────────────
print("\n=== TEST 3: Boş görüntü (hata bekliyoruz) ===")
path3 = minio.upload_image(None, "Masa Doluluk Analizi", "Bos.jpg")
print(f"Dönen path: {path3}")
# Beklenen: None

# ─── TEST 4: generate_alert_filename (otomatik numaralama) ──
print("\n=== TEST 4: generate_alert_filename ===")
for i in range(1, 4):
    f = make_frame(label=f"Alert{i}")
    minio.upload_image(f, "Barista Analizi", f"Alert{i}.jpg")

filename, index = minio.generate_alert_filename("Barista Analizi", prefix="Alert")
print(f"Sonraki alert: {filename}, index: {index}")
# Beklenen: Alert4.jpg, 4

# ─── TEST 5: get_last_alert_index ───────────────────────────
print("\n=== TEST 5: get_last_alert_index ===")
last = minio.get_last_alert_index("Barista Analizi", prefix="Alert")
print(f"Son alert index: {last}")
# Beklenen: 3

print("\n✅ Tüm birim testler tamamlandı")