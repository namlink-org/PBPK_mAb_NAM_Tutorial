# Reproducible environment for the PBPK mAb NAM tutorial.
#
# The image contains only the software (R, Quarto, .NET 8 and the Open Systems
# Pharmacology R packages at fixed versions). The repository itself is mounted
# at /work when the container runs, so results are written back to your folder.
#
# Build (from the repository root):
#   docker build -t pbpk-mab-nam docker
# Run the a priori workflow:
#   docker run --rm -v "${PWD}:/work" pbpk-mab-nam apriori        (PowerShell)
#   docker run --rm -v "%cd%:/work" pbpk-mab-nam apriori          (Command Prompt)
#
# PK-Sim and MoBi are not needed: ospsuite bundles the simulation engine.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    MAMBA_ROOT_PREFIX=/opt/conda

# .NET 8 runtime (ospsuite 12.4 via rSharp), libxml2 (needed by the ospsuite
# simulation engine libOSPSuite.SimModelNative.so), git and tools.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       dotnet-runtime-8.0 libxml2 git curl bzip2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# R 4.5.1, Quarto and CRAN dependencies from conda-forge.
RUN curl -fsSL https://conda.anaconda.org/conda-forge/linux-64/micromamba-2.9.0-0.tar.bz2 \
       | tar -xj -C /usr/local bin/micromamba \
    && micromamba create -y -q -n pbpk -c conda-forge \
       "r-base=4.5.1" quarto \
       r-data.table r-dplyr r-ggplot2 r-knitr r-rmarkdown r-openxlsx r-purrr \
       r-ragg r-readr r-rvest r-scales r-stringr r-tibble r-tidyr r-xml2 \
       r-rlang r-lifecycle r-cli r-showtext r-colorspace r-fs r-jsonlite \
       r-patchwork r-r6 r-readxl r-usethis r-vctrs r-writexl r-ggnewscale \
       r-ggrepel r-ggtext r-checkmate r-gridextra r-logger r-cowplot \
       r-fitdistrplus r-ggh4x \
    && micromamba clean -y --all

# Make the environment (including conda Quarto's settings) active everywhere.
ENV PATH=/opt/conda/envs/pbpk/bin:$PATH \
    QUARTO_DENO=/opt/conda/envs/pbpk/bin/deno \
    QUARTO_PANDOC=/opt/conda/envs/pbpk/bin/pandoc \
    QUARTO_ESBUILD=/opt/conda/envs/pbpk/bin/esbuild \
    QUARTO_TYPST=/opt/conda/envs/pbpk/bin/typst \
    QUARTO_DART_SASS=/opt/conda/envs/pbpk/bin/sass \
    QUARTO_SHARE_PATH=/opt/conda/envs/pbpk/share/quarto \
    QUARTO_CONDA_PREFIX=/opt/conda/envs/pbpk

# Open Systems Pharmacology R packages at the tags verified to reproduce v0.2.x.
RUN set -e; mkdir -p /tmp/osp && cd /tmp/osp; \
    for spec in \
      "Open-Systems-Pharmacology/rSharp v1.2.3" \
      "Open-Systems-Pharmacology/OSPSuite.RUtils v1.11.0" \
      "Open-Systems-Pharmacology/TLF-Library v1.6.2" \
      "Open-Systems-Pharmacology/OSPSuite.Plots v1.1.0" \
      "Open-Systems-Pharmacology/OSPSuite-R v12.4.2" \
      "esqLABS/esqlabsR v5.6.0"; do \
      set -- $spec; \
      git clone -q --depth 1 -b "$2" "https://github.com/$1" "$(basename $1)"; \
      R CMD INSTALL --no-test-load "$(basename $1)"; \
    done; \
    cd / && rm -rf /tmp/osp; \
    Rscript -e 'v <- c(rSharp="1.2.3", ospsuite="12.4.2", esqlabsR="5.6.0"); \
      got <- sapply(names(v), function(p) as.character(packageVersion(p))); \
      print(got); stopifnot(identical(unname(got), unname(v)))'

# Repository files are owned by the host user; let git inside the container read them.
RUN git config --system --add safe.directory '*'

COPY run_pipeline.sh /usr/local/bin/pbpk
RUN sed -i 's/\r$//' /usr/local/bin/pbpk && chmod +x /usr/local/bin/pbpk

WORKDIR /work
ENTRYPOINT ["pbpk"]
CMD ["help"]
