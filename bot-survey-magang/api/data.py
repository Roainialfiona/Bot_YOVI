from datetime import datetime, timedelta

def get_surveys():
    now = datetime.utcnow()
    data = []

    for i in range(1, 101):
        data.append({
            "id": i,
            "city": "KOTA MALANG",
            "created_at": (now - timedelta(days=i)).isoformat() + "Z",
            "longitude": "112.6304",
            "latitude": "-7.9666",
            "odp_name": "ODP-MLG-01",
            "sto": "MLG",
            "questions": [
                {"question": "Nama usaha?", "answer": f"Toko {i}"},
                {"question": "Jenis usaha (ekosistem)?", "answer": "Retail"},
                {"question": "Alamat usaha?", "answer": "Jl. Contoh"},
                {"question": "Nama PIC yang ditemui?", "answer": "Budi"},
                {"question": "Status PIC yang ditemui? (Owner / Karyawan)", "answer": "Owner"},
                {"question": "Nomor HP PIC yang ditemui?", "answer": "08123456789"},
                {"question": "Hasil visit?", "answer": "Potensial"}
            ],
            "sales_agent": {
                "id": 1,
                "name": "Sales Dummy"
            }
        })
    return data
