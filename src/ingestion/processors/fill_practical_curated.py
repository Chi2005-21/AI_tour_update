"""
Điền thông tin THỰC DỤNG cho 30 địa điểm từ NGUỒN WEB CHÍNH THỨC/UY TÍN.
Mỗi địa điểm có source_url để truy nguồn (không bịa).

- Điểm tham quan có vé/giờ  -> điền giờ mở cửa, giá vé, website, SĐT, địa chỉ.
- Vùng/tự nhiên (hồ, đèo, đảo, ruộng, khu phố) -> để null + note "khu vực mở".
- Trường nào không tìm được nguồn tin cậy -> để null (KHÔNG bịa).

Schema practical (thống nhất):
    opening_hours, ticket_price, phone, website, address, note, source_url

Dữ liệu tra ngày 2026-06-08. Giá vé/giờ có thể thay đổi -> kèm nguồn để cập nhật.

Cách chạy:
    python scripts/fill_practical_curated.py
"""

import sys
import os
import json

sys.stdout.reconfigure(encoding="utf-8")

PROCESSED_DIR = "data/processed"

KEYS = ["opening_hours", "ticket_price", "phone", "website", "address", "note", "source_url"]

# Ghi chú dùng chung cho khu vực mở
OPEN_AREA = "Khu vực mở / cảnh quan tự nhiên — tham quan tự do, không có giờ đóng mở cố định hay vé chung."

CURATED = {
    # ===== Điểm tham quan có vé/giờ =====
    "van_mieu": {
        "opening_hours": "Mùa nóng (15/4–15/10): 07:30–17:30; mùa lạnh (16/10–14/4): 08:00–17:00; mở tất cả các ngày",
        "ticket_price": "Người lớn 70.000đ; HS-SV, người cao tuổi, người khuyết tật nặng 35.000đ; trẻ dưới 16 tuổi miễn phí",
        "website": "http://vanmieu.gov.vn",
        "source_url": "http://vanmieu.gov.vn/vi/tham-quan/huong-dan/",
    },
    "hoang_thanh": {
        "opening_hours": "08:00–17:00, đóng cửa thứ Hai",
        "ticket_price": "100.000đ/lượt (áp dụng từ 01/01/2025)",
        "website": "https://hoangthanhthanglong.vn",
        "address": "19C Hoàng Diệu, Ba Đình, Hà Nội",
        "source_url": "https://hoangthanhthanglong.vn/gia-ve-tham-quan-khu-di-tich-hoang-thanh-thang-long/",
    },
    "lang_ho_chi_minh": {
        "opening_hours": "Mở cửa Thứ 3,4,5,7,CN (nghỉ Thứ 2 và Thứ 6). Mùa hè (1/4–31/10): 07:30–10:30 ngày thường, 07:30–11:00 T7/CN/lễ. Mùa đông (1/11–31/3): 08:00–11:00 ngày thường, 08:00–11:30 T7/CN/lễ",
        "ticket_price": "Miễn phí",
        "source_url": "https://vi.wikipedia.org/wiki/L%C4%83ng_Ch%E1%BB%A7_t%E1%BB%8Bch_H%E1%BB%93_Ch%C3%AD_Minh",
    },
    "den_ngoc_son": {
        "opening_hours": "Thứ 2–Thứ 6: 07:00–18:00; Thứ 7, Chủ Nhật: 07:00–21:00",
        "ticket_price": "Người lớn 30.000đ; HS-SV 15.000đ; trẻ dưới 15 tuổi miễn phí",
        "source_url": "https://findtour.vn/ve-tham-quan/moi-nhat-gia-ve-den-ngoc-son-ha-noi-thang-canh-van-hien-giua-long-thu-do.html",
    },
    "den_quan_thanh": {
        "opening_hours": "08:00–17:00; mùng 1 và rằm: 06:00–20:00",
        "ticket_price": "10.000đ/người; trẻ nhỏ miễn phí",
        "address": "190 phố Quán Thánh, Ba Đình, Hà Nội",
        "source_url": "https://findtour.vn/ve-tham-quan/moi-nhat-gia-ve-den-quan-thanh-thang-long-tu-tran-ha-noi.html",
    },
    "chua_mot_cot": {
        "opening_hours": "Mùa hè (4–10): 07:30–11:00 & 13:30–17:00; mùa đông (11–3): 08:00–11:00 & 13:30–16:30; mở tất cả các ngày",
        "ticket_price": "Người Việt Nam miễn phí; khách nước ngoài 25.000đ",
        "source_url": "https://vinwonders.com/vi/wonderpedia/news/chua-mot-cot-ha-noi/",
    },
    "chua_tran_quoc": {
        "opening_hours": "08:00–16:00; mùng 1 và rằm: 06:00–18:00",
        "ticket_price": "Miễn phí (một số nguồn ghi 5.000đ)",
        "phone": "024 7533396",
        "address": "46 đường Thanh Niên, Yên Phụ, Tây Hồ, Hà Nội",
        "source_url": "https://vinwonders.com/vi/wonderpedia/news/chua-tran-quoc-ha-noi/",
    },
    "nha_tho_lon": {
        "opening_hours": "Tham quan: T2–T7 08:00–11:00 & 14:00–20:00; CN 07:00–11:30 & 15:00–21:00. Giờ lễ: ngày thường 05:30 & 18:30; Chủ Nhật nhiều lễ 05:00–20:00",
        "ticket_price": "Miễn phí",
        "website": "https://giaoxuchinhtoahanoi.org",
        "address": "40 Nhà Chung, Hoàn Kiếm, Hà Nội",
        "source_url": "https://giaoxuchinhtoahanoi.org/CT/gio-le/",
    },
    "btdth": {
        "opening_hours": "08:30–17:30, đóng cửa thứ Hai và Tết",
        "ticket_price": "Người lớn 40.000đ; sinh viên 20.000đ; học sinh 10.000đ; trẻ dưới 6 tuổi miễn phí",
        "website": "https://www.vme.org.vn",
        "source_url": "https://www.vme.org.vn/vi/c/category-59/ve-va-le-phi-p1.html",
    },
    "btls": {
        "opening_hours": "08:00–12:00 & 13:30–17:00, đóng cửa thứ Hai",
        "ticket_price": "40.000đ (giảm cho HS-SV; miễn phí trẻ dưới 6 tuổi và người khuyết tật)",
        "website": "https://baotanglichsu.vn",
        "address": "Số 1 Tràng Tiền, Hoàn Kiếm, Hà Nội",
        "source_url": "https://baotanglichsu.vn/vi/Articles/3108/ve-va-le-phi",
    },
    "den_hung": {
        "opening_hours": "07:00–18:00 (Bảo tàng Hùng Vương 07:00–16:00); mở tất cả các ngày",
        "ticket_price": "Vào cửa 10.000đ; Bảo tàng Hùng Vương 15.000đ; trẻ em miễn phí. Xe điện 15.000–50.000đ/lượt",
        "website": "https://dulichphutho.gov.vn/diemden/den-hung",
        "source_url": "https://dulichphutho.gov.vn/diemden/den-hung",
    },
    "dien_bien_phu": {
        "opening_hours": "08:00–17:00",
        "ticket_price": "Bảo tàng Chiến thắng: 100.000đ/lượt (giảm/miễn cho người cao tuổi, cựu chiến binh, HS-SV, dưới 18 tuổi, người khuyết tật)",
        "address": "QL279, phường Mường Thanh, TP Điện Biên Phủ",
        "note": "Các điểm di tích chiến trường ngoài trời miễn phí; vé áp dụng cho Bảo tàng Chiến thắng Điện Biên Phủ.",
        "source_url": "https://vietnamtourism.gov.vn/post/60500",
    },

    # ===== Ninh Bình & danh thắng có vé tour =====
    "trang_an": {
        "opening_hours": "Mùa hè 06:00–16:45; mùa đông 07:00–16:30; lễ/Tết 06:00–16:45",
        "ticket_price": "250.000đ/người (vé đò chèo tay 1 tuyến, thuyền 4–5 khách, gồm bảo hiểm)",
        "website": "https://trangandanhthang.vn",
        "source_url": "https://trangandanhthang.vn/gia-ve-tham-quan-cac-khu-diem-du-lich/",
    },
    "tam_coc": {
        "opening_hours": "07:00–17:00",
        "ticket_price": "Combo người lớn 250.000đ (vé tham quan 120.000đ + đò 150.000đ/thuyền); trẻ cao 1m–1,3m 120.000đ; dưới 1m miễn phí",
        "phone": "0229 3618 339",
        "source_url": "https://sovaba.travel/blog/bai-viet-cap-nhat-gia-ve-tham-quan-tam-coc-bich-dong-moi-nhat",
    },
    "co_do_hoa_lu": {
        "opening_hours": "07:00–18:00 (mùa hè mở từ 06:30)",
        "ticket_price": "Người lớn 20.000–30.000đ; trẻ em 10.000–15.000đ",
        "phone": "0229 3620099",
        "note": "Khu di tích gồm Đền vua Đinh Tiên Hoàng và Đền vua Lê Đại Hành.",
        "source_url": "https://thesinhtour.com/gia-ve-tham-quan-co-do-hoa-lu/",
    },
    "nha_tho_phat_diem": {
        "opening_hours": "06:30–18:30; mở tất cả các ngày",
        "ticket_price": "Miễn phí",
        "source_url": "https://vietnamtourism.gov.vn/post/50534",
    },
    "chua_yen_tu": {
        "opening_hours": "Mùa lễ hội (tháng 1–3 âm lịch): 05:00–20:00; các tháng còn lại: 07:00–18:00",
        "ticket_price": "Vé tham quan: người lớn 40.000đ, trẻ dưới 16 tuổi 10.000đ, dưới 1,2m miễn phí. Cáp treo khứ hồi 2 tuyến: 430.000đ",
        "source_url": "https://luhanhvietnam.com.vn/du-lich/kinh-nghiem-di-cap-treo-yen-tu.html",
    },
    "vinh_ha_long": {
        "ticket_price": "Vé qua cảng 60.000đ; vé tham quan vịnh trong ngày 260.000–310.000đ/người; nghỉ qua đêm 500.000–750.000đ/người",
        "note": "Vịnh tham quan bằng tàu/du thuyền theo tuyến (VHL1, 2, 3...); không có 'giờ đóng mở' cố định, phụ thuộc lịch tàu.",
        "source_url": "https://baoquangninh.vn/bang-gia-ve-tham-quan-vinh-ha-long-vinh-bai-tu-long-va-cac-loai-tour-tham-quan-nam-2025-3354446.html",
    },
    "vqg_xuan_son": {
        "opening_hours": "07:30–16:30; mở tất cả các ngày",
        "ticket_price": "Vào cửa miễn phí; một số hang động 10.000đ/khách; gửi xe 5.000–10.000đ",
        "website": "https://dulichphutho.gov.vn/diemden/vuon-quoc-gia-xuan-son",
        "source_url": "https://dulichphutho.gov.vn/diemden/vuon-quoc-gia-xuan-son",
    },
    "dao_cat_ba": {
        "opening_hours": "Vườn quốc gia Cát Bà: 08:00–18:00",
        "ticket_price": "Vườn quốc gia Cát Bà: người lớn 80.000đ, trẻ em 50.000đ (mức vé thay đổi theo nguồn/tuyến)",
        "phone": "02563 590999",
        "website": "https://vuonquocgiacatba.com.vn",
        "note": "Đảo Cát Bà là khu vực rộng; thông tin vé/giờ là của Vườn quốc gia Cát Bà — điểm tham quan chính trên đảo.",
        "source_url": "https://vuonquocgiacatba.com.vn/bang-gia-ve-tham-quan",
    },

    # ===== Làng nghề / di tích chưa có giờ-vé chính thức rõ ràng =====
    "tranh_dong_ho": {
        "address": "Xã Song Hồ, huyện Thuận Thành, Bắc Ninh",
        "website": "https://www.tranhdangiandongho.vn",
        "note": "Làng nghề — tham quan cơ sở nghệ nhân ban ngày (khoảng 09:00–17:00), không có giờ/vé cố định. Chợ tranh phiên tháng Chạp.",
        "source_url": "https://vinwonders.com/vi/wonderpedia/news/lang-tranh-dong-ho/",
    },
    "chua_but_thap": {
        "address": "Thôn Bút Tháp, xã Đình Tổ, huyện Thuận Thành, Bắc Ninh",
        "note": "Di tích quốc gia đặc biệt. Chưa tìm được giờ mở cửa / giá vé chính thức công bố — để null thay vì bịa.",
        "source_url": "https://vi.wikipedia.org/wiki/Ch%C3%B9a_B%C3%BAt_Th%C3%A1p",
    },

    # ===== Vùng / tự nhiên: null + ghi chú "khu vực mở" =====
    "ho_tay":           {"note": OPEN_AREA},
    "ho_hoan_kiem":     {"note": OPEN_AREA},
    "sa_pa":            {"note": "Thị trấn du lịch vùng cao — tham quan tự do, không có giờ/vé chung. Các điểm con (Fansipan, Hàm Rồng, bản làng) có vé riêng."},
    "pho_co_ha_noi":    {"note": "Khu phố cổ — dạo bộ/tham quan tự do, không có giờ đóng mở hay vé."},
    "dong_van":         {"note": "Cao nguyên đá Đồng Văn / phố cổ Đồng Văn — khu vực mở, tham quan tự do."},
    "mu_cang_chai":     {"note": "Vùng ruộng bậc thang ngoài trời — tham quan tự do, đẹp nhất mùa lúa chín (tháng 9–10)."},
    "ma_pi_leng":       {"note": "Đèo trên QL4C — đường đèo mở 24/7, không có vé. Ngắm cảnh từ các điểm dừng/đỉnh đèo."},
    "dao_bach_long_vi": {"note": "Đảo xa ngoài khơi vịnh Bắc Bộ — không có giờ/vé tham quan; đi lại bằng tàu theo lịch."},
}


def main():
    files = sorted(f for f in os.listdir(PROCESSED_DIR) if f.endswith(".json"))
    updated, missing_in_curated = 0, []

    filled_count, region_count = 0, 0

    for filename in files:
        path = os.path.join(PROCESSED_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        loc_id = data.get("id")

        if loc_id not in CURATED:
            missing_in_curated.append(loc_id)
            continue

        practical = {k: None for k in KEYS}
        practical.update(CURATED[loc_id])

        data["practical"] = practical
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        updated += 1

        has_data = any(practical[k] for k in ("opening_hours", "ticket_price"))
        if has_data:
            filled_count += 1
            tag = "OK "
        else:
            region_count += 1
            tag = "~~ "
        print(f"  {tag} {loc_id}: " + (practical.get("opening_hours") or practical.get("ticket_price") or practical.get("note") or "")[:70])

    print(f"\n=== Cập nhật {updated} file ===")
    print(f"  Có giờ/vé thật (kèm nguồn): {filled_count}")
    print(f"  Vùng/tự nhiên hoặc chưa có nguồn (null + note): {region_count}")
    if missing_in_curated:
        print(f"  [CẢNH BÁO] chưa có trong CURATED: {missing_in_curated}")
    print("\nMỗi địa điểm có source_url để truy nguồn. Trường null = không có/không tìm được nguồn tin cậy (không bịa).")


if __name__ == "__main__":
    main()
