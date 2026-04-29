"""
MinIO Manager Module
MinIO'ya görüntü yükleme ve path yönetimi

Kullanım:
    from minio_manager import MinIOManager
    
    minio = MinIOManager(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        branch_name="Tepe Prime"
    )
    
    # Görüntü yükle
    path = minio.upload_image(
        image=frame,
        folder="Masa Doluluk Analizi",
        filename="Report1.jpg"
    )
    # Döner: "Tepe Prime/26-11-2025/Masa Doluluk Analizi/Report1.jpg"
"""

import cv2
import io
import os
import urllib3
from datetime import datetime
from minio import Minio
from minio.error import S3Error
from typing import Optional



class MinIOManager:
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str,
                 branch_name: str = None, secure: bool = False, 
                 bucket_name: str = "ai-outputs"):
        """
        MinIO Manager başlat
        
        Args:
            endpoint: MinIO endpoint (örn: "localhost:9000")
            access_key: Access key
            secret_key: Secret key
            branch_name: Şube adı (örn: "Tepe Prime")
            secure: HTTPS kullan mı
            bucket_name: Varsayılan bucket
        """
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self.branch_name = branch_name
        
        try:
            # ✅ TIMEOUT EKLENDİ: 5sn bağlantı, 10sn okuma
            http_client = urllib3.PoolManager(
                timeout=urllib3.Timeout(connect=5.0, read=10.0),
                retries=urllib3.Retry(total=3, backoff_factor=0.5)
            )
            
            self.client = Minio(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
                http_client=http_client  # ✅ Timeout ile
            )
            print(f"✅ MinIO bağlantısı kuruldu: {endpoint} (timeout: 5s/10s)")
        except Exception as e:
            print(f"❌ MinIO bağlantı hatası: {e}")
            self.client = None
    
    
    def upload_image(self, image, folder: str, filename: str,
                     bucket_name: str = None) -> Optional[str]:
        """
        Görüntüyü MinIO'ya yükle
        
        Args:
            image: cv2 image (BGR numpy array)
            folder: Modül klasörü (örn: "Masa Doluluk Analizi")
            filename: Dosya adı (örn: "Report1.jpg")
            bucket_name: Bucket (None ise varsayılan)
        
        Returns:
            full_object_path: "Şube Adı/DD-MM-YYYY/folder/filename" veya None
        """
        if self.client is None:
            print("❌ MinIO client yok")
            return None
        
        if image is None or image.size == 0:
            print("❌ Boş görüntü, yükleme yapılamadı")
            return None
        
        bucket = bucket_name or self.bucket_name
        
        try:
            # Görüntüyü encode et
            is_success, buffer = cv2.imencode(".jpg", image)
            if not is_success:
                print("❌ Görsel encode edilemedi")
                return None
            
            # BytesIO'ya çevir
            byte_io = io.BytesIO(buffer)
            
            # Path oluştur: "Şube Adı/DD-MM-YYYY/folder/filename"
            today_str = datetime.now().strftime("%d-%m-%Y")
            
            if self.branch_name:
                full_object_path = f"{self.branch_name}/{today_str}/{folder}/{filename}"
            else:
                full_object_path = f"{today_str}/{folder}/{filename}"
            
            # Yükle
            self.client.put_object(
                bucket_name=bucket,
                object_name=full_object_path,
                data=byte_io,
                length=len(byte_io.getvalue()),
                content_type="image/jpeg"
            )
            
            print(f"✅ Yüklendi: {full_object_path}")
            return full_object_path
        
        except urllib3.exceptions.TimeoutError:
            print(f"❌ MinIO timeout hatası (bağlantı zaman aşımı)")
            return None
        except S3Error as e:
            print(f"❌ MinIO S3 hatası: {e}")
            return None
        except Exception as e:
            print(f"❌ MinIO yükleme hatası: {e}")
            return None
    
    
    def get_last_alert_index(self, folder: str, prefix: str = "Alert") -> int:
        """
        Klasördeki son alert numarasını bul
        
        Args:
            folder: Modül klasörü (örn: "Masa Doluluk Analizi")
            prefix: Dosya prefix (örn: "Alert")
        
        Returns:
            Son index (örn: Alert5.jpg varsa 5 döner)
        """
        if self.client is None:
            return 0
        
        today_str = datetime.now().strftime("%d-%m-%Y")
        
        # Path oluştur: "Şube Adı/DD-MM-YYYY/folder/prefix"
        if self.branch_name:
            search_prefix = f"{self.branch_name}/{today_str}/{folder}/{prefix}"
        else:
            search_prefix = f"{today_str}/{folder}/{prefix}"
        
        max_index = 0
        try:
            objects = self.client.list_objects(
                self.bucket_name, 
                prefix=search_prefix, 
                recursive=True
            )
            
            for obj in objects:
                name = os.path.basename(obj.object_name)
                if name.startswith(prefix) and name.endswith(".jpg"):
                    # "Alert5.jpg" -> "5"
                    num_part = name.replace(prefix, "").replace(".jpg", "")
                    if num_part.isdigit():
                        max_index = max(max_index, int(num_part))
        
        except urllib3.exceptions.TimeoutError:
            print(f"❌ MinIO timeout hatası (list_objects)")
        except Exception as e:
            print(f"❌ MinIO sayma hatası: {e}")
        
        return max_index
    
    
    def generate_alert_filename(self, folder: str, prefix: str = "Alert") -> tuple[str, int]:
        """
        Otomatik alert dosya adı oluştur
        
        Args:
            folder: Klasör adı
            prefix: Dosya prefix
        
        Returns:
            (filename, index): ("Alert6.jpg", 6)
        """
        last_index = self.get_last_alert_index(folder, prefix)
        next_index = last_index + 1
        filename = f"{prefix}{next_index}.jpg"
        return filename, next_index
