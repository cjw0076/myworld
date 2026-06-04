# Research Note — GPU present but torch/transformers/peft not installed

- fetched_at: 2026-05-20T15:57:29+09:00
- source: Tavily search API (autonomous search→absorb organ)
- status: DRAFT — MemoryOS review required (DNA Invariant 2)

## Synthesized answer

To use GPU with PyTorch, ensure CUDA Toolkit is installed and PyTorch is compatible. Install PEFT with `pip install peft`. Verify GPU usage with `torch.cuda.is_available()`.

## Sources (provenance — DNA Invariant 5)

### [PEFT is not installed. Please install it with `pip install peft`] · Issue ...
- url: https://github.com/huggingface/transformers/issues/27309
- score: 0.67192334

I am attempting to fine-tune a fully quantized LLM model. So, I need to attach trainable adapters to enhance its performance.

### pytorch gpu not detected…
- url: https://itctshop.com/pytorch-gpu-not-detected/?srsltid=AfmBOopm15Kux7qSOh4FBv0FeUU2IqxqzpI4h1mf5yLNOTKaQGwcHIla
- score: 0.49758363

### PyTorch Can’t See GPU But nvidia-smi Works: Driver vs CUDA Version Fix. PyTorch Can't See GPU But nvidia-smi Works Driver vs CUDA Version Fix. # PyTorch Can’t See GPU But nvidia-smi Works: Driver vs CUDA Version Fix. The most common reason `torch.cuda.is_available()` returns **False** despite `nvidia-smi` working correctly is a version mismatch between the installed NVIDIA driver and the PyTorch CUDA runtime, or the accidental installation of a CPU-only PyTorch build. The root cause of this issue lies in a complex web of version dependencies between your NVIDIA driver, CUDA runtime libraries, and PyTorch installation. The most common culprit remains version mismatches: PyTorch built for 

### How to resolve Torch not compiled with CUDA enabled
- url: https://www.educative.io/answers/how-to-resolve-torch-not-compiled-with-cuda-enabled
- score: 0.3468736

The  `''Torch not compiled with CUDA enabled''`error is likely to occur when the user does not have CUDA Toolkit installed in their Python environment. We can resolve this error by installing CUDA Toolkit on our machine and upgrading the version of our current PyTorch library. It is essential to install the right version of PyTorch with CUDA support. The first approach is to reinstall PyTorch with CUDA support. ## Installing CUDA Toolkit. The next approach is to install the NVIDIA CUDA Toolkit before installing PyTorch with CUDA support. Next, we install CUDA Toolkit and its dependencies by using the following command:. ## Installing PyTorch with CUDA support. We can install PyTorch with CUD

### Pytorch 2.1.0 CUDA compatibility and unable to load loaders? - Reddit
- url: https://www.reddit.com/r/Oobabooga/comments/17ilf3v/pytorch_210_cuda_compatibility_and_unable_to_load/
- score: 0.28905097

I can run oobabooga on Windows 10 but only on CPU and the Transformers loader. When I try to run on GPU it returns an error stating:

### Installation — Transformer Engine 2.15.0 documentation
- url: https://docs.nvidia.com/deeplearning/transformer-engine/user-guide/installation.html
- score: 0.23543385

# Installation. If the CUDA Toolkit headers are not available at runtime in a standard. Transformer Engine library is preinstalled in the PyTorch container in versions 22.09 and later. Transformer Engine can be directly installed from our PyPI, e.g. To obtain the necessary Python bindings for Transformer Engine, the frameworks needed must be explicitly specified as extra dependencies in a comma-separated list (e.g. Transformer Engine ships wheels for the core library. Source distributions are shipped for the JAX and PyTorch extensions. By default, this will install the core library compiled for CUDA 12. Execute the following command to install the latest stable version of Transformer Engine

## Origin

Open question surfaced by the AIOS dream/consolidation organ; fetched
by the autonomous search→absorb executor. This note is a draft memory
candidate — acceptance requires explicit MemoryOS review.