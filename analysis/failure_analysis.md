## 1. Tổng quan Benchmark

- **Tổng số cases:** 50
- **Tỉ lệ Pass/Fail:** X/Y
- **Điểm RAGAS trung bình:**
  - Faithfulness: 0.XX
  - Relevancy: 0.XX
- **Điểm LLM-Judge trung bình:** X.X / 5.0
- **Tỉ lệ Pass/Fail:** 50/0
- **Agent baseline:** Agent_V1_Base
- **Agent candidate:** Agent_V2_Optimized
- **Release gate:** APPROVE
- **Điểm RAGAS/custom trung bình:**
  - Faithfulness: 0.9846
  - Relevancy: 0.8399
  - Hit Rate: 0.9600
  - MRR: 0.9600
  - Recall@K: 0.9500
- **Điểm LLM-Judge trung bình:** 4.89 / 5.0
- **Agreement Rate:** 0.9950
- **Latency trung bình:** 0.0227 giây
- **Estimated cost:** 0.000564 USD / 50 cases

## 2. Phân nhóm lỗi (Failure Clustering)

| Nhóm lỗi      | Số lượng | Nguyên nhân dự kiến                     |
| ------------- | -------- | --------------------------------------- |
| Hallucination | 5        | Retriever lấy sai context               |
| Incomplete    | 3        | Prompt quá ngắn, không yêu cầu chi tiết |
| Tone Mismatch | 2        | Agent trả lời quá suồng sã              |

## 3. Phân tích 5 Whys (Chọn 3 case tệ nhất)

### Case #1: [Mô tả ngắn]

1. **Symptom:** Agent trả lời sai về...
2. **Why 1:** LLM không thấy thông tin trong context.
3. **Why 2:** Vector DB không tìm thấy tài liệu liên quan nhất.
4. **Why 3:** Chunking size quá lớn làm loãng thông tin quan trọng.
5. **Why 4:** ...
6. **Root Cause:** Chiến lược Chunking không phù hợp với dữ liệu bảng biểu.

## 4. Kế hoạch cải tiến (Action Plan)

- [ ] Thay đổi Chunking strategy từ Fixed-size sang Semantic Chunking.
- [ ] Cập nhật System Prompt để nhấn mạnh vào việc "Chỉ trả lời dựa trên context".
- [ ] Thêm bước Reranking vào Pipeline.
      Không có case bị fail theo ngưỡng judge score `< 3`. Tuy nhiên benchmark vẫn ghi nhận 2 điểm cần cải thiện ở tầng retrieval.

| Nhóm lỗi                      | Số lượng       | Case     | Nguyên nhân dự kiến                                                                                                 |
| ----------------------------- | -------------- | -------- | ------------------------------------------------------------------------------------------------------------------- |
| Out-of-context over-retrieval | 1              | CASE_047 | Retriever vẫn lấy tài liệu có token chung như "cong ty", "chinh sach", dù câu hỏi nằm ngoài phạm vi knowledge base. |
| Multi-hop miss                | 1              | CASE_048 | Câu hỏi gộp "mất điện thoại" và "mất laptop" nhưng token matching chưa hiểu đồng nghĩa MFA/device loss đủ tốt.      |
| Generation failure            | 0              | N/A      | Candidate agent trả lời có căn cứ theo context và không hallucinate ở các hard cases.                               |
| Judge conflict                | 0 nghiêm trọng | N/A      | Accuracy judge và safety/grounding judge có agreement trung bình 99.5%.                                             |

## 3. Phân tích 5 Whys

### Case #47: Out-of-context crypto policy

1. **Symptom:** Retriever trả về `POLICY_DATA_007` và `POLICY_ONBOARD_010` dù câu hỏi hỏi về chính sách mua bán tiền mã hóa.
2. **Why 1:** Query có các token chung như "cong ty", "chinh sach", "nhan vien" trùng với nhiều policy nội bộ.
3. **Why 2:** Retriever hiện tại dùng cosine trên bag-of-words, chưa có classifier phát hiện out-of-domain.
4. **Why 3:** Threshold retrieval cố định phải đủ thấp để không làm rớt các câu multi-hop, nên dễ over-retrieve với câu hỏi ngoài phạm vi.
5. **Why 4:** Dataset chưa có nhiều negative examples cho các chủ đề tài chính/cá nhân ngoài scope.
6. **Root Cause:** Thiếu tầng intent/domain detection trước retrieval.
7. **Action:** Thêm OOD classifier hoặc dynamic threshold theo confidence gap giữa top-1 và top-2.

### Case #48: Mất điện thoại và laptop cùng lúc

1. **Symptom:** Expected IDs là `POLICY_DEVICE_009` và `POLICY_MFA_002`, nhưng retriever ưu tiên một số policy khác.
2. **Why 1:** Query dùng cụm "mất điện thoại" còn tài liệu MFA dùng "mat dien thoai" nhưng semantic chính là thu hồi token MFA.
3. **Why 2:** Bag-of-words chưa làm tốt expansion cho các cụm đồng nghĩa như phone/MFA/token và laptop/device/asset.
4. **Why 3:** Multi-hop retrieval cần lấy đủ 2 tài liệu, trong khi top-k đã tối ưu còn 2 để kiểm soát cost.
5. **Why 4:** Không có reranker để đánh giá lại quan hệ giữa từng retrieved document và từng sub-question.
6. **Root Cause:** Retriever chưa tách câu hỏi multi-hop thành sub-queries.
7. **Action:** Query decomposition trước retrieval: tách "mất điện thoại" và "mất laptop" thành 2 lượt search rồi merge kết quả.

### Case #50: PII trên laptop cá nhân khi làm việc từ xa

1. **Symptom:** Đây là hard safety-policy case có rủi ro hallucination nếu agent chỉ trả lời chung chung.
2. **Why 1:** Câu hỏi cần kết hợp `POLICY_DATA_007` và `POLICY_REMOTE_012`.
3. **Why 2:** Nếu chỉ top-1, agent có thể bỏ sót ràng buộc remote-work hoặc PII.
4. **Why 3:** Candidate V2 dùng top-k=2 và strict grounding nên trả lời đầy đủ hơn baseline.
5. **Why 4:** Judge safety/grounding xác nhận có refusal rõ ràng và bám context.
6. **Root Cause được kiểm soát:** Tối ưu top-k và strict grounding đã giảm lỗi thiếu context trong hard case.

## 4. Kế hoạch cải tiến

- [x] Thay mock evaluator bằng retrieval metrics thật: Hit Rate, MRR, Recall@K.
- [x] Thay single/mock judge bằng multi-judge consensus offline có conflict resolution.
- [x] Thêm regression gate dựa trên quality, retrieval, agreement, latency và cost.
- [x] Sinh reports tự động từ benchmark.
- [ ] Thêm OOD classifier để CASE_047 không over-retrieve.
- [ ] Thêm query decomposition/reranking cho các câu multi-hop như CASE_048.
- [ ] Bổ sung thêm negative cases về chủ đề ngoài phạm vi để calibrate threshold tốt hơn.
