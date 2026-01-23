import os
import pandas as pd
from pathlib import Path

# --- AYARLAR ---
TARGET_DIR = "canli_test_sonuclari"

def analyze_folders(base_dir):
    print(f"📂 Analiz ediliyor: {base_dir} ...\n")
    
    data = []
    
    # Klasörleri gez
    total_folders = 0
    empty_folders = 0
    
    # Path nesnesine çevir
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print("❌ Klasör bulunamadı!")
        return

    for folder in base_path.iterdir():
        if folder.is_dir():
            total_folders += 1
            folder_size = 0
            file_count = 0
            files_info = []
            
            # İçindeki dosyaları gez
            for file in folder.iterdir():
                if file.is_file():
                    size_mb = file.stat().st_size / (1024 * 1024) # MB cinsinden
                    folder_size += size_mb
                    file_count += 1
                    files_info.append({
                        "name": file.name,
                        "size_mb": size_mb
                    })
            
            if file_count == 0:
                empty_folders += 1
            
            # Veriyi listeye ekle
            data.append({
                "folder_id": folder.name,
                "total_size_mb": round(folder_size, 2),
                "file_count": file_count,
                # Örnek: En büyük dosyanın boyutu
                "max_file_mb": round(max([f['size_mb'] for f in files_info], default=0), 2)
            })

    # DataFrame oluştur
    df = pd.DataFrame(data)
    
    if df.empty:
        print("⚠️ Hiç veri bulunamadı.")
        return

    # --- RAPORLAMA ---
    print("="*40)
    print("📊 ÖZET RAPOR")
    print("="*40)
    print(f"Toplam Klasör (URL): {total_folders}")
    print(f"Boş/Hatalı Klasör  : {empty_folders}")
    print(f"Toplam Veri Boyutu : {df['total_size_mb'].sum():.2f} MB")
    print(f"Ortalama Boyut/URL : {df['total_size_mb'].mean():.2f} MB")
    print("-" * 40)
    
    # En çok yer kaplayan 10 URL (Muhtemelen HTML'i çok şişik olanlar)
    print("\n🐘 EN BÜYÜK 10 URL (Data Boyutu):")
    print(df.nlargest(10, 'total_size_mb')[['folder_id', 'total_size_mb', 'file_count']].to_string(index=False))

    # En az yer kaplayanlar (Muhtemelen sadece resim çekip HTML alamayanlar)
    print("\nzk EN KÜÇÜK/BOŞ 10 URL:")
    print(df.nsmallest(10, 'total_size_mb')[['folder_id', 'total_size_mb', 'file_count']].to_string(index=False))
    
    # CSV Olarak Kaydet
    csv_name = "analiz_raporu.csv"
    df.sort_values(by='total_size_mb', ascending=False).to_csv(csv_name, index=False)
    print(f"\n💾 Detaylı rapor kaydedildi: {csv_name}")

if __name__ == "__main__":
    analyze_folders(TARGET_DIR)