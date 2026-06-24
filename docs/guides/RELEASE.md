# Release tarball

Build a self-contained install package for users who do not want to clone git.

```bash
cd context-synthesizer
bash packaging/build-release-tarball.sh
```

Output:

```
context-synthesizer/packaging/build/context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
```

Ship that tarball (GitHub Release, internal CDN, etc.). Users extract and run:

```bash
tar -xzf context-synthesizer-toolkit-*.tar.gz
cd context-synthesizer-toolkit-*
bash run-setup.sh your.handle
```

The build script refuses to run if `context-synthesizer/.env` contains `ANTHROPIC_API_KEY`.
