# 2A202600775 - Đỗ Thiện Lĩnh - Benchmark, Async & Regression Gate

## Phần đóng góp

- Hoàn thiện `main.py` để chạy V1 vs V2 thật.
- Tổng hợp metrics: score, pass rate, Hit Rate, MRR, Recall@K, faithfulness, relevancy, agreement, latency, tokens và cost.
- Implement release gate tự động theo ngưỡng quality, retrieval, judge reliability, latency và cost regression.

## Kiến thức kỹ thuật

- Regression testing không chỉ so score mà còn phải kiểm soát cost và latency.
- Async batch runner giúp benchmark 50 cases chạy dưới 2 phút.
- Release gate nên trả quyết định rõ ràng `APPROVE` hoặc `BLOCK_RELEASE`.

## Vấn đề đã xử lý

- Gate ban đầu chỉ xét `delta > 0`.
- Bản mới sinh `reports/summary.json` và `reports/benchmark_results.json` đầy đủ.
