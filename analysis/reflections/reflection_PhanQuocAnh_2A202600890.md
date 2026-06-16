# Reflection Phan Quoc Anh - Agent/RAG Pipeline

## Phần đóng góp
- Nâng cấp `MainAgent` từ câu trả lời mẫu thành deterministic RAG agent.
- Agent đọc `data/knowledge_base.json`, retrieve top-k, trả `contexts`, `retrieved_ids`, `sources`, `tokens_used`.
- Thêm strict grounding để candidate V2 trả lời dựa trên context.

## Kiến thức kỹ thuật
- Một agent RAG cần expose intermediate signals để debug: retrieved IDs, contexts, retrieval score và token usage.
- Strict grounding giúp giảm hallucination khi gặp câu hỏi nhạy cảm hoặc ngoài phạm vi.

## Vấn đề đã xử lý
- Agent scaffold ban đầu không thể đo retrieval vì không trả `retrieved_ids`.
- Đã sửa scoring retrieval để title/document được so khớp đúng với query.