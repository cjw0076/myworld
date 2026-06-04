# Research Note — GPU present but torch/transformers/peft not installed — `pip install torch transformers peft`

- fetched_at: 2026-05-18T03:06:05+09:00
- source: Tavily search API (autonomous search→absorb organ)
- status: DRAFT — MemoryOS review required (DNA Invariant 2)

## Synthesized answer

To install torch, transformers, and peft, use `pip install torch transformers peft`. Ensure compatible versions for peft and torch.

## Sources (provenance — DNA Invariant 5)

### [PEFT is not installed. Please install it with `pip install peft`] · Issue ...
- url: https://github.com/huggingface/transformers/issues/27309
- score: 0.67706895

I am attempting to fine-tune a fully quantized LLM model. So, I need to attach trainable adapters to enhance its performance.

### want to install peft and accelerate compatible with torch 1.9.0+cu111
- url: https://stackoverflow.com/questions/77826406/want-to-install-peft-and-accelerate-compatible-with-torch-1-9-0cu111
- score: 0.5112048

The latest peft 0.7.2.dev0 requires torch>=1.13.0, is not compatible to my torch 1.9.0+cu111 which is incompatible. the command

### peft - PyPI
- url: https://pypi.org/project/peft/
- score: 0.44767818

PEFT is integrated with Transformers for easy model training and inference, Diffusers for conveniently managing different adapters, and Accelerate for

### pip install 'transformers[torch]' pulls nvidia dependencies · Issue #39780 · huggingface/transformers · GitHub
- url: https://github.com/huggingface/transformers/issues/39780
- score: 0.43712714

## Navigation Menu. # Search code, repositories, users, issues, pull requests... # Provide feedback. We read every piece of feedback, and take your input very seriously. # Saved searches. ## Use saved searches to filter your results more quickly. To see all available qualifiers, see our documentation. # pip install 'transformers[torch]' pulls nvidia dependencies #39780. ## Footer. ### System Info. ### Who can help? ### Tasks. ### Reproduction. `docker run --rm -it python:3.13-slim-bookworm bash -c "python3 -m pip --version && python3 -m pip install transformers[torch] pillow; transformers env"`. I'm adding an explicit pillow dependency due to #39779. `pip 25.1.1 from /usr/local/lib/python3.1

### Installing specific versions of pytorch and transformers via pip
- url: http://hpc-community.unige.ch/t/installing-specific-versions-of-pytorch-and-transformers-via-pip/4065
- score: 0.42391166

I have tried installing pyTorch via pip and it does not seem to take effect. Similarly, if I load transformers via module load Transformers/X.X.

## Origin

Open question surfaced by the AIOS dream/consolidation organ; fetched
by the autonomous search→absorb executor. This note is a draft memory
candidate — acceptance requires explicit MemoryOS review.