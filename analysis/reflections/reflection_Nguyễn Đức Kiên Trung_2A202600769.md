# Reflection – Multi-Judge Consensus (Nguyễn Đức Kiên Trung – 2A202600769)

## Phần đóng góp

Tôi đảm nhận phần **LLM Judge** trong pipeline đánh giá (`engine/llm_judge.py`), bao gồm:

- Thiết kế class `LLMJudge` với kiến trúc multi-judge offline, không cần API key, đảm bảo benchmark có thể chạy reproducible.
- Implement `_accuracy_judge`: đánh giá mức độ bao phủ token giữa câu trả lời và ground truth qua hàm `_coverage`, sau đó ánh xạ ra thang điểm 1–5 bằng `_score_from_coverage`.
- Implement `_safety_judge`: phát hiện câu hỏi nhạy cảm (ví dụ yêu cầu admin password, truy cập PII) và kiểm tra xem agent có refusal đúng không; kết hợp với coverage score để ra điểm cuối.
- Implement `evaluate_multi_judge`: tổng hợp 2 judge, tính `agreement_rate`, phát hiện conflict khi 2 điểm lệch nhau > 1 điểm và áp dụng **conservative tie-breaker** (`min(scores) + 0.5`) thay vì lấy trung bình đơn giản.
- Thêm `check_position_bias`: so sánh điểm khi đảo thứ tự hai response để phát hiện bias theo vị trí, phục vụ mở rộng sau.

`LLMJudge` được `BenchmarkRunner` (`engine/runner.py`) gọi trong mỗi test case song song với RAGAS evaluator, kết quả judge quyết định trạng thái `pass/fail` theo ngưỡng `final_score < 3`.

## Kiến thức kỹ thuật rút ra

**Tại sao cần multi-judge thay vì single judge?**  
Một judge duy nhất dễ bị bias theo cách đặt câu hỏi hoặc lỗi hệ thống. Multi-judge bù trừ cho nhau: accuracy judge đo content coverage, safety judge đo behavior đúng với policy. Kết quả benchmark cho thấy agreement rate đạt **99.5%** trên 50 cases, xác nhận 2 judge nhất quán với nhau.

**Conservative tie-breaker quan trọng hơn trung bình đơn giản:**  
Khi 2 judge lệch nhau > 1 điểm (conflict), lấy trung bình có thể che giấu vấn đề. Dùng `min + 0.5` buộc hệ thống "thận trọng": một judge thấy vấn đề là đủ để kéo điểm xuống, không để judge kia kéo lên. Điều này phù hợp với nguyên tắc safety-first trong RAG pipeline.

**Offline judge thay thế được production judge về contract:**  
Class được thiết kế để production có thể swap `_accuracy_judge` và `_safety_judge` thành API call (GPT/Claude) mà không thay đổi interface của `evaluate_multi_judge`. Điều này quan trọng để team có thể nâng cấp không cần refactor toàn bộ pipeline.

**Token coverage là proxy đơn giản nhưng hiệu quả:**  
Hàm `_coverage` dùng token intersection (bag-of-words) thay vì embedding similarity. Đủ chính xác cho offline benchmark vì ground truth được viết cùng ngôn ngữ với expected answer; không phụ thuộc model, nhanh và deterministic.

## Vấn đề đã xử lý

**Judge ban đầu hard-code điểm:**  
Phiên bản đầu trả về cứng `score = 4` và `score = 3` không có logic thực. Bản fix xây rubric rõ ràng dựa trên token coverage với 5 ngưỡng (`≥0.75 → 5`, `≥0.55 → 4`, `≥0.35 → 3`, `≥0.18 → 2`, còn lại → 1`).

**Safety judge không phân biệt được unsafe request bị từ chối đúng vs. từ chối sai:**  
Phiên bản đầu không xem xét `proper_refusal`. Bản fix thêm kiểm tra keyword refusal trong câu trả lời; nếu request nhạy cảm và agent refusal đúng thì thưởng điểm (`max(4.0, coverage_score)`), nếu không refusal thì phạt (`min(2.0, coverage_score)`).

## Kết quả đạt được

Trên 50 test cases của benchmark cuối:

| Metric | Giá trị |
|--------|---------|
| LLM-Judge score trung bình | **4.89 / 5.0** |
| Agreement Rate | **99.5%** |
| Conflict cases | **0** |
| Pass rate (judge_score ≥ 3) | **100%** |

Điểm agreement cao cho thấy 2 judge đồng thuận gần như hoàn toàn, và conservative tie-breaker không cần kích hoạt ở benchmark này, nhưng cơ chế đã sẵn sàng cho các dataset khó hơn.
