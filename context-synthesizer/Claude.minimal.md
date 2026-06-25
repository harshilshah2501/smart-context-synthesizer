# Minimal Layer 1 stub (~380 tokens)

Use this only for quick local experiments. **Below Anthropic's 1,024-token cache
minimum** — expect zero `cache_read` until Layer 2 grows.

For production / OSS defaults, use `Claude.md` (production template).

```bash
cp Claude.minimal.md Claude.md   # only if you intentionally want the tiny stub
python3 count_tokens.py
```
