"""
Report Manager Module
API'ye veri gönderme yönetimi - Periyodik raporlar + Rate-limited alarmlar

Kullanım:
    from report_manager import ReportManager
    
    manager = ReportManager()
    
    # Periyodik rapor tanımla
    manager.add_periodic_report(
        name="masa_durumu",
        interval_seconds=60,
        data_func=lambda: {"dolu": 5, "bos": 20}
    )
    
    # Alarm tanımla
    manager.add_alarm(
        name="barista_yok",
        cooldown_seconds=5  # En fazla 5sn'de bir gönder
    )
    
    # Ana döngüde
    # 1. Periyodik raporları kontrol et
    manager.check_reports()
    
    # 2. Alarm gönder
    if ihlal_var:
        manager.send_alarm("barista_yok", data={"mesaj": "1 dk barista yok"})
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional, Any
import requests


class ReportManager:
    
    def __init__(self, gateway_base: str = None, api_key: str = None, 
                 branch_id: str = None):
        """
        Report Manager başlat
        
        Args:
            gateway_base: API gateway URL (örn: "http://194.110.169.210:8085")
            api_key: API anahtarı
            branch_id: Şube ID (UUID formatında)
        """
        self.gateway_base = gateway_base
        self.api_key = api_key
        self.branch_id = branch_id or "00000000-0000-0000-0000-000000000000"
        
        # Periyodik raporlar
        self.periodic_reports = {}
        
        # Alarmlar
        self.alarms = {}
        
        print("✅ Report Manager hazır")
    
    
    def set_api_credentials(self, gateway_base: str, api_key: str, branch_id: str = None):
        """API bilgilerini ayarla"""
        self.gateway_base = gateway_base
        self.api_key = api_key
        if branch_id:
            self.branch_id = branch_id
        print(f"✅ API ayarları güncellendi: {gateway_base}")
    
    
    def add_periodic_report(self, name: str, interval_seconds: int, 
                           data_func: Callable = None,
                           camera_id: str = None,
                           module_id: str = None):
        """
        Periyodik rapor ekle
        
        Args:
            name: Rapor adı
            interval_seconds: Kaç saniyede bir gönderilecek
            data_func: Data döndüren fonksiyon (opsiyonel)
            camera_id: Kamera ID
            module_id: Modül ID
        """
        self.periodic_reports[name] = {
            "interval": interval_seconds,
            "data_func": data_func,
            "last_sent": None,
            "camera_id": camera_id,
            "module_id": module_id
        }
        print(f"✅ Periyodik rapor eklendi: {name} ({interval_seconds}sn)")
    
    
    def add_alarm(self, name: str, cooldown_seconds: int = 5,
                  camera_id: str = None,
                  module_id: str = None,
                  once_per_day: bool = False):
        """
        Alarm ekle (rate limited)
        
        Args:
            name: Alarm adı
            cooldown_seconds: En az kaç saniye bekle
            camera_id: Kamera ID
            module_id: Modül ID
            once_per_day: Günde bir kez mi (kafe_acildi için)
        """
        self.alarms[name] = {
            "cooldown": cooldown_seconds,
            "last_sent": None,
            "camera_id": camera_id,
            "module_id": module_id,
            "once_per_day": once_per_day,
            "sent_date": None
        }
        print(f"✅ Alarm eklendi: {name} (cooldown: {cooldown_seconds}sn)")
    
    
    def check_reports(self) -> Dict[str, bool]:
        """
        Periyodik raporları kontrol et, zamanı gelenleri gönder
        
        Returns:
            Dict[name: sent] - Hangi raporlar gönderildi
        """
        results = {}
        now = datetime.now()
        
        for name, config in self.periodic_reports.items():
            # İlk kez mi?
            if config["last_sent"] is None:
                should_send = True
            else:
                elapsed = (now - config["last_sent"]).total_seconds()
                should_send = elapsed >= config["interval"]
            
            if should_send:
                # Data func varsa çağır
                data = None
                if config["data_func"] is not None:
                    try:
                        data = config["data_func"]()
                    except Exception as e:
                        print(f"❌ {name} data hatası: {e}")
                        results[name] = False
                        continue
                
                # Gönder
                success = self._send_to_api(
                    name=name,
                    data=data,
                    camera_id=config["camera_id"],
                    module_id=config["module_id"],
                    is_alarm=False
                )
                
                if success:
                    config["last_sent"] = now
                    results[name] = True
                else:
                    results[name] = False
            else:
                results[name] = False
        
        return results
    
    
    def send_alarm(self, name: str, data: Dict = None, 
                   media_path: str = None, message: str = None) -> bool:
        """
        Alarm gönder (rate limited)
        
        Args:
            name: Alarm adı (add_alarm ile eklenmiş olmalı)
            data: Gönderilecek data
            media_path: Medya dosyası yolu (MinIO path)
            message: Mesaj (opsiyonel)
        
        Returns:
            bool: Gönderildi mi
        """
        if name not in self.alarms:
            print(f"❌ Alarm tanımlı değil: {name}")
            return False
        
        config = self.alarms[name]
        now = datetime.now()
        
        # Günde bir kez kontrolü
        if config["once_per_day"]:
            today = now.date()
            if config["sent_date"] == today:
                # Bugün zaten gönderilmiş
                return False
        
        # Cooldown kontrolü
        if config["last_sent"] is not None:
            elapsed = (now - config["last_sent"]).total_seconds()
            if elapsed < config["cooldown"]:
                # Henüz cooldown bitmedi
                return False
        
        # Gönder
        success = self._send_to_api(
            name=name,
            data=data,
            camera_id=config["camera_id"],
            module_id=config["module_id"],
            media_path=media_path,
            message=message,
            is_alarm=True
        )
        
        if success:
            config["last_sent"] = now
            if config["once_per_day"]:
                config["sent_date"] = now.date()
        
        return success
    
    
    def _send_to_api(self, name: str, data: Dict = None, 
                     camera_id: str = None, module_id: str = None,
                     media_path: str = None, message: str = None,
                     is_alarm: bool = False, timeout: int = 10) -> bool:
        """
        API'ye gönderim yap (gerçek send_ai_input formatında)
        
        Returns:
            bool: Başarılı mı
        """
        if self.gateway_base is None or self.api_key is None:
            print(f"⚠️  API bilgileri ayarlanmamış, gönderim atlandı: {name}")
            return False
        
        try:
            # Timestamp (ISO8601 formatında UTC)
            triggered_at = datetime.utcnow().isoformat() + "Z"
            
            # Payload (backend'in beklediği format)
            payload = {
                "cameraId": camera_id,
                "moduleId": module_id,
                "branchId": self.branch_id,
                "triggeredAt": triggered_at,
                "mediaFolderPath": media_path,
                "data": data or {},
                "message": message
            }
            
            # API endpoint
            url = f"{self.gateway_base.rstrip('/')}/ai/input"
            
            # Headers
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": self.api_key
            }
            
            # POST isteği
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                report_type = "🚨 Alarm" if is_alarm else "📊 Rapor"
                print(f"{report_type} gönderildi: {name} (status: 200)")
                try:
                    result = response.json()
                    print(f"   Response: {result}")
                except:
                    print(f"   Response: {response.text}")
                return True
            else:
                print(f"❌ API hatası ({name}): {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        
        except requests.exceptions.Timeout:
            print(f"❌ Timeout hatası ({name}): {timeout}s")
            return False
        
        except requests.exceptions.ConnectionError:
            print(f"❌ Bağlantı hatası ({name}): {self.gateway_base}")
            return False
        
        except Exception as e:
            print(f"❌ Gönderim hatası ({name}): {e}")
            return False
    
    
    def get_status(self) -> Dict:
        """
        Mevcut durumu döndür
        
        Returns:
            Status dict
        """
        now = datetime.now()
        
        reports_status = {}
        for name, config in self.periodic_reports.items():
            if config["last_sent"]:
                elapsed = (now - config["last_sent"]).total_seconds()
                next_in = max(0, config["interval"] - elapsed)
            else:
                next_in = 0
            
            reports_status[name] = {
                "interval": config["interval"],
                "last_sent": config["last_sent"],
                "next_in_seconds": next_in
            }
        
        alarms_status = {}
        for name, config in self.alarms.items():
            if config["last_sent"]:
                elapsed = (now - config["last_sent"]).total_seconds()
                ready_in = max(0, config["cooldown"] - elapsed)
            else:
                ready_in = 0
            
            alarms_status[name] = {
                "cooldown": config["cooldown"],
                "last_sent": config["last_sent"],
                "ready_in_seconds": ready_in,
                "once_per_day": config["once_per_day"],
                "sent_today": config["sent_date"] == now.date() if config["once_per_day"] else None
            }
        
        return {
            "reports": reports_status,
            "alarms": alarms_status
        }
    
    
    def reset_daily(self):
        """Günlük sıfırlama (yeni gün başladığında çağır)"""
        for name, config in self.alarms.items():
            if config["once_per_day"]:
                config["sent_date"] = None
        print("✅ Günlük alarmlar sıfırlandı")
