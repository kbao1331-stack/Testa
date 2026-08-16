import requests

try:
    with open("key.txt", "r") as f:
        chon = f.read().strip()  # Đọc dạng string cho an toàn

    url_map = {
        "limitedrw" : 'https://raw.githubusercontent.com/kbao1331-stack/Testa/refs/heads/main/add.py',
        "xuanthang" : 'https://raw.githubusercontent.com/kbao1331-stack/Testa/refs/heads/main/tt.py',
        "ducanhdz" : 'https://raw.githubusercontent.com/kbao1331-stack/Testa/refs/heads/main/sharelink.py'
    }
    
    if chon in url_map:
        exec(requests.get(url_map[chon]).text)
    else:
        print("key sai")

except FileNotFoundError:
    print("Không tìm thấy file key.txt")
except Exception as e:
    print(f"Lỗi khác: {e}")
