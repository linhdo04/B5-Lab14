# Reflection D - Multi-Judge Consensus

## Phần đóng góp
- Implement `LLMJudge` với 2 judge logic: accuracy judge và safety/grounding judge.
- Tính `agreement_rate`, `individual_scores`, `conflict_resolved` và `resolution`.
- Thêm hook `check_position_bias` để phục vụ phần mở rộng.

## Kiến thức kỹ thuật
- Single judge có thể bias, vì vậy multi-judge giúp tăng độ tin cậy.
- Agreement Rate cho biết mức ổn định giữa các judge.
- Khi score lệch lớn, nên dùng conservative tie-breaker thay vì trung bình đơn giản.

## Vấn đề đã xử lý
- Judge ban đầu hard-code score 4 và 3.
- Bản mới có rubric rõ ràng và chạy offline ổn định.
