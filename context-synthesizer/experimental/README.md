# Experimental code (unsupported)

Code in this directory is **not part of the supported Context Synthesizer product**. It is kept for reference only and is **not imported** by `proxy_tool.py`.

## `copilot_backend.py`

Historical experiment: route Claude-shaped API calls through GitHub Copilot's API instead of Anthropic.

**Do not use in production or public installs.**

- May violate [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)
- No prompt-cache alignment, no compaction fidelity guarantees
- Removed from the default proxy path in v0.1.1+

To study or fork this code, copy it into your own project at your own risk. We do not provide support for it.
