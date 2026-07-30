# Router — Qwen3-0.6B, small slice, low concurrency need
```
vllm serve /mnt/e/models/Qwen3-0.6B \
  --port 8000 \
  --gpu-memory-utilization 0.22 \
  --max-model-len 4096 \
  --max-num-seqs 8 \
  --enforce-eager
```
# budget: 0.22 * 12GB ≈ 2.64 GiB → weights ~1.2GB, leaves ~1.4GB for KV cache (plenty for a router)

# Reasoner — Qwen3-4B, quantized so weights don't eat the whole card
```
vllm serve /mnt/e/models/Qwen3-4B-AWQ \
  --port 8001 \
  --quantization awq \
  --gpu-memory-utilization 0.5 \
  --max-model-len 4096 \
  --max-num-seqs 8 \
  --enforce-eager
```
# budget: 0.5 * 12GB = 6 GiB → weights ~2.5GB, leaves ~3.5GB for KV cache