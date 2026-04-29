# test_report_manager.py
import time
from report_manager import ReportManager

manager = ReportManager(
    gateway_base="http://localhost:8085",
    api_key="test-key-123",
    branch_id="11111111-1111-1111-1111-111111111111"
)

# --- Periyodik rapor tanımla ---
manager.add_periodic_report(
    name="masa_durumu",
    interval_seconds=5,  # Test için 5 saniye
    data_func=lambda: {"dolu": 3, "bos": 12},
    camera_id="cam-001",
    module_id="mod-masa"
)

# --- Alarmlar tanımla ---
manager.add_alarm(
    name="barista_yok",
    cooldown_seconds=3,
    camera_id="cam-002",
    module_id="mod-barista"
)

manager.add_alarm(
    name="kafe_acildi",
    cooldown_seconds=5,
    once_per_day=True,
    camera_id="cam-001",
    module_id="mod-kafe"
)

# --- Test döngüsü ---
print("\n🚀 Test başlıyor...\n")

for i in range(10):
    print(f"\n--- Döngü {i + 1} ---")

    # Periyodik raporları kontrol et
    results = manager.check_reports()
    print(f"Rapor sonuçları: {results}")

    # 2. döngüde alarm gönder
    if i == 1:
        sent = manager.send_alarm("barista_yok", data={"sure": "2dk"}, message="Barista tezgahta yok")
        print(f"barista_yok alarmı gönderildi: {sent}")

    # 3. döngüde tekrar dene (cooldown'da olmalı)
    if i == 2:
        sent = manager.send_alarm("barista_yok", data={"sure": "3dk"})
        print(f"barista_yok (cooldown testi): {sent}")  # False bekliyoruz

    # 5. döngüde kafe_acildi gönder
    if i == 4:
        sent = manager.send_alarm("kafe_acildi", message="Kafe açıldı!")
        print(f"kafe_acildi: {sent}")

    # Status'u yazdır
    status = manager.get_status()
    for alarm_name, alarm_status in status["alarms"].items():
        print(f"  ⏱  {alarm_name} → hazır olma: {alarm_status['ready_in_seconds']:.1f}s")

    time.sleep(2)

print("\n✅ Test tamamlandı")