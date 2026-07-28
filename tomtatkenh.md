# Tóm Tắt Kênh

## 1. Tổng quan ý tưởng

- **Chủ đề nội dung**: tâm lý học tình cảm/quan hệ, chữa lành, phát triển bản thân — dạng "suy ngẫm ngắn" gây đồng cảm (style gần với "Chỉ Thích Anh Á").
- **Định dạng**: video ngắn dọc 9:16, độ dài mỗi video ~30-60s (5-10 scene), giọng đọc + phụ đề đồng bộ.
- **Phong cách hình ảnh**: minh hoạ tối giản (stick-figure line art hoặc flat pastel), nền đơn sắc hoặc ảnh AI tràn viền có lớp phủ gradient bảo vệ chữ. Có thể tô màu nhấn 1 từ khoá trong tiêu đề/phụ đề để tăng điểm nhấn cảm xúc.
- **Giọng văn**: chân thành, gần gũi như tâm sự với bạn bè, tránh học thuật khô khan, tránh sáo rỗng/công thức lặp lại.
- **Cấu trúc kịch bản chuẩn** (áp dụng cho mọi kịch bản): gây chú ý (hook) → nêu quan điểm → giải thích/dẫn chứng → truyền cảm hứng/gợi ý hành động. Không dùng công thức mở đầu lặp lại giữa các đoạn.

## 2. Quy tắc viết kịch bản (áp dụng khi paste vào bất kỳ AI nào)

- Không dùng emoji, không đánh số thứ tự, không link.
- Mỗi đoạn không dùng dấu câu ở cuối câu; ngắt câu bằng dấu phẩy/chấm/hỏi/than để tạo nhịp nói tự nhiên.
- Không lặp cùng 1 từ mở đầu (vd "đôi khi", "có bao giờ", "thực ra") quá 1 lần trong toàn bộ kịch bản.
- Có thể trích dẫn nghiên cứu/tác giả uy tín (tâm lý học: Jung, Kabat-Zinn; văn học/triết: Nietzsche, Trang Tử...) nếu phù hợp, không bắt buộc, không bịa nguồn.
- Văn phong: chân thành, ấm áp, như người có trải nghiệm đang chia sẻ, không giảng dạy.

## 3. 10 Prompt mẫu — dùng làm input cho AI khác (ChatGPT, Gemini, Claude, DeepSeek...) để tạo kịch bản

Mỗi prompt dưới đây là 1 bản hoàn chỉnh, copy nguyên văn dán vào AI là dùng được ngay. Đổi số lượng scene / số từ mỗi đoạn tuỳ nhu cầu.

---

**Prompt 1 — Vì sao nên trân trọng người chủ động quan tâm**
```
Bạn là chuyên gia sáng tạo nội dung, chuyên viết kịch bản video ngắn về tâm lý tình cảm, giọng văn chân thành như tâm sự với bạn bè, không sáo rỗng, không học thuật khô khan.

Viết 6 đoạn narration (mỗi đoạn 15-25 từ, không dấu câu ở cuối) cho chủ đề: "Vì sao nên trân trọng người chủ động quan tâm bạn mỗi ngày".

Cấu trúc: mở đầu gây đồng cảm → nêu quan điểm → ví dụ đời thường → kết truyền cảm hứng.
Không lặp từ mở đầu giữa các đoạn. Không emoji, không số thứ tự, không link.
Chỉ xuất JSON: {"narrations": ["...", "..."]}
```

---

**Prompt 2 — Kiểu gắn bó lo âu (anxious attachment)**
```
Bạn là chuyên gia tâm lý học viết kịch bản video ngắn giải thích khái niệm tâm lý theo cách dễ hiểu, gần gũi.

Viết 7 đoạn narration (15-25 từ/đoạn) giải thích "kiểu gắn bó lo âu trong tình yêu" — dấu hiệu nhận biết, vì sao hình thành, cách chữa lành.

Giọng văn ấm áp, không phán xét, có thể trích 1 nghiên cứu tâm lý học gắn bó (attachment theory) nếu phù hợp, không bịa nguồn.
Không lặp từ mở đầu, không emoji, không số thứ tự.
Chỉ xuất JSON: {"narrations": [...]}
```

---

**Prompt 3 — Ranh giới cá nhân trong tình yêu**
```
Viết kịch bản video ngắn (6 đoạn, 15-25 từ/đoạn) về chủ đề "vì sao có ranh giới cá nhân lại khiến một mối quan hệ bền vững hơn".

Giọng văn: chân thành, như một người từng trải chia sẻ, không giảng dạy, không công thức.
Cấu trúc: hook cảm xúc → quan điểm → ví dụ cụ thể → gợi ý hành động nhẹ nhàng ở cuối.
Không lặp mở đầu, không emoji.
Xuất JSON: {"narrations": [...]}
```

---

**Prompt 4 — Dấu hiệu một mối quan hệ lành mạnh (green flags)**
```
Viết 6-8 đoạn narration ngắn (15-25 từ) liệt kê "những dấu hiệu cho thấy bạn đang ở trong một mối quan hệ lành mạnh", theo giọng tâm sự nhẹ nhàng, mỗi đoạn 1 dấu hiệu + 1 cảm nhận đi kèm.

Không dùng cấu trúc liệt kê máy móc (không đánh số), phải nghe tự nhiên như đang kể chuyện.
Không lặp từ mở đầu. Không emoji.
Xuất JSON: {"narrations": [...]}
```

---

**Prompt 5 — Chữa lành sau chia tay**
```
Bạn là người viết nội dung chữa lành tâm lý cho các video ngắn mạng xã hội.

Viết 7 đoạn narration (15-25 từ/đoạn) về chủ đề "làm sao để chữa lành sau một cuộc chia tay", đi từ cảm giác đau/mất mát → chấp nhận → trưởng thành → hy vọng mới.

Giọng văn dịu dàng, chân thành, không sến súa, không sáo rỗng.
Không lặp mở đầu, không emoji, không số thứ tự.
Xuất JSON: {"narrations": [...]}
```

---

**Prompt 6 — Giao tiếp trong tình yêu**
```
Viết kịch bản video ngắn (6 đoạn, 15-25 từ/đoạn) chủ đề "vì sao giao tiếp thẳng thắn quan trọng hơn im lặng chịu đựng trong tình yêu".

Cấu trúc: mở bằng 1 tình huống quen thuộc → vấn đề → góc nhìn mới → lời khuyên nhẹ nhàng.
Giọng văn gần gũi, không giáo điều. Không lặp từ mở đầu, không emoji.
Xuất JSON: {"narrations": [...]}
```

---

**Prompt 7 — Sự cô đơn khi ở một mình ban đêm**
```
Viết 6 đoạn narration ngắn (15-25 từ/đoạn), chủ đề "cảm giác cô đơn khi nhìn điện thoại sáng lên giữa đêm, chờ tin nhắn từ một người", pha chút tự sự, hơi buồn nhưng kết thúc nhẹ nhàng/tích cực.

Giọng văn chân thực, gần với cảm xúc thật, tránh bi luỵ quá mức.
Không lặp mở đầu, không emoji.
Xuất JSON: {"narrations": [...]}
```

---

**Prompt 8 — Áp lực từ gia đình/cha mẹ**
```
Viết kịch bản video ngắn (6-7 đoạn, 15-25 từ/đoạn) về chủ đề "làm sao để vừa yêu thương cha mẹ vừa giữ được chính kiến của bản thân".

Giọng văn ấm áp, thấu hiểu cả 2 phía, không đổ lỗi cho ai.
Cấu trúc: tình huống quen thuộc → xung đột cảm xúc → góc nhìn cân bằng → thông điệp kết.
Không lặp mở đầu, không emoji.
Xuất JSON: {"narrations": [...]}
```

---

**Prompt 9 — Yêu bản thân trước khi yêu người khác**
```
Viết 6 đoạn narration (15-25 từ/đoạn) chủ đề "vì sao phải học cách yêu bản thân trước khi bước vào một mối quan hệ".

Giọng văn truyền cảm hứng nhẹ nhàng, không hô khẩu hiệu, có ví dụ đời thường cụ thể thay vì lý thuyết suông.
Không lặp mở đầu, không emoji, không số thứ tự.
Xuất JSON: {"narrations": [...]}
```

---

**Prompt 10 — Vì sao một số người khó tin tưởng trong tình yêu**
```
Bạn là chuyên gia tâm lý viết kịch bản video ngắn giải thích hành vi con người theo hướng dễ hiểu, không phán xét.

Viết 7 đoạn narration (15-25 từ/đoạn) giải thích "vì sao một số người khó tin tưởng bạn đời dù được yêu thương thật lòng" — gốc rễ tâm lý, biểu hiện, hướng chữa lành.

Có thể trích 1 khái niệm tâm lý học (không bịa nguồn). Giọng văn thấu cảm, không phán xét.
Không lặp mở đầu, không emoji.
Xuất JSON: {"narrations": [...]}
```

---

## 4. Ghi chú sử dụng

- Các prompt trên độc lập với app Pixelle-Video — dùng được trên bất kỳ AI chat nào (ChatGPT, Gemini, Claude, DeepSeek...) để brainstorm/kịch bản dự phòng.
- Sau khi có kịch bản từ AI ngoài, dán vào chế độ **Custom Script** trong app để giữ nguyên không bị AI viết lại.
- Muốn dùng trực tiếp trong app (không cần công cụ ngoài), dùng ô **Narration Style Notes** ở tab Topic — dán phần "giọng văn/quy tắc riêng" (mục 2 ở trên) vào đó, AI trong app sẽ tự tuân theo.
