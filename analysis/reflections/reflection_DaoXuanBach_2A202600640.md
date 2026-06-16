# Reflection - Đào Xuân Bách - 2A202600640

## 1. Vai trò cá nhân

Trong Lab Day 14, em phụ trách phần **Dataset & Synthetic Data Generation (SDG)** cho hệ thống AI Evaluation Factory. Mục tiêu chính của phần này là tạo một Golden Dataset đủ tốt để nhóm có thể benchmark agent một cách định lượng, đặc biệt là đo riêng chất lượng Retrieval trước khi đánh giá chất lượng câu trả lời cuối cùng.

Các file em phụ trách:

- `data/synthetic_gen.py`
- `data/knowledge_base.json`
- `data/golden_set.jsonl`

## 2. Đóng góp kỹ thuật

Em đã xây dựng bộ dữ liệu benchmark gồm **50 test cases** dựa trên **15 policy documents** nội bộ giả lập. Mỗi case được chuẩn hóa theo schema:

- `id`: mã định danh test case.
- `question`: câu hỏi đầu vào cho agent.
- `expected_answer`: câu trả lời kỳ vọng.
- `expected_retrieval_ids`: danh sách document IDs mà retriever cần lấy đúng.
- `context`: context chuẩn dùng để đối chiếu.
- `metadata`: thông tin về độ khó, loại case và source.

Ngoài các câu hỏi thường, em bổ sung nhiều nhóm hard cases để kiểm tra giới hạn của agent:

- **Prompt injection:** người dùng yêu cầu bỏ qua hướng dẫn hoặc tiết lộ mật khẩu admin.
- **Out-of-context:** câu hỏi nằm ngoài phạm vi tài liệu, agent cần biết nói không đủ thông tin.
- **Multi-hop:** câu hỏi cần kết hợp nhiều tài liệu, ví dụ mất điện thoại và laptop cùng lúc.
- **Safety-policy:** câu hỏi liên quan PII, thiết bị cá nhân và làm việc từ xa.

Em cũng thêm `data/knowledge_base.json` làm retrieval corpus để agent và evaluator dùng chung một nguồn dữ liệu nhất quán.

## 3. Kiến thức em rút ra

Điểm quan trọng nhất em học được là **không thể đánh giá RAG chỉ bằng câu trả lời cuối cùng**. Nếu agent trả lời sai, cần biết lỗi nằm ở retrieval, generation hay judging. Vì vậy Golden Dataset phải có `expected_retrieval_ids` để đo được:

- **Hit Rate:** retriever có lấy được ít nhất một tài liệu đúng trong top-k hay không.
- **MRR:** tài liệu đúng có xuất hiện ở vị trí cao trong ranking hay không.
- **Recall@K:** với câu hỏi cần nhiều tài liệu, retriever lấy được bao nhiêu phần trăm tài liệu đúng.

Em cũng hiểu thêm rằng hard cases rất quan trọng vì câu hỏi dễ thường làm benchmark nhìn có vẻ tốt, nhưng không phát hiện được lỗi hallucination, over-retrieval hoặc prompt injection.

## 4. Vấn đề gặp phải và cách xử lý

Ban đầu project chỉ có generator mẫu tạo 1 case, không đủ yêu cầu tối thiểu 50 cases và cũng không có ground-truth retrieval IDs. Em đã thay bằng generator deterministic để:

- Reviewer có thể chạy lại kết quả mà không cần API key.
- Dataset sinh ra ổn định giữa các lần chạy.
- Toàn bộ nhóm có cùng dữ liệu để benchmark, debug và viết báo cáo.

Một vấn đề khác là câu hỏi out-of-context và multi-hop dễ làm retriever lấy nhầm tài liệu vì có nhiều token chung như "công ty", "chính sách", "nhân viên". Em đã chủ động thêm các case này vào dataset để nhóm có dữ liệu phân tích lỗi trong `analysis/failure_analysis.md`.

## 5. Kết quả kiểm chứng

Sau khi tích hợp phần dataset với benchmark pipeline, hệ thống đạt:

- Tổng số cases: 50
- Pass rate: 100%
- Hit Rate: 96%
- MRR: 96%
- Agreement Rate: 99.5%
- Release Gate: `APPROVE`

Các lệnh kiểm chứng:

```bash
python3 data/synthetic_gen.py
python3 main.py
python3 check_lab.py
```

## 6. Tự đánh giá

Phần đóng góp của em tập trung vào nền tảng dữ liệu cho toàn bộ evaluation pipeline. Nếu dataset không có ground-truth rõ ràng, các phần retrieval metrics, judge consensus, regression testing và failure analysis đều khó đánh giá chính xác.

Nếu có thêm thời gian, em muốn cải thiện thêm bằng cách:

- Tăng số lượng negative/out-of-context cases.
- Thêm nhiều câu hỏi multi-turn.
- Thêm nhãn domain để hỗ trợ out-of-domain detection.
- Tạo script thống kê phân bố dataset theo difficulty và case type.
