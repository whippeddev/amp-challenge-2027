# Third-party materials

`LICENSE` covers this project's own integration code and documentation. Upstream
code, pretrained weights, and reference data keep their own terms.

The official validator is bundled unmodified under the organizer repository's
BSD-3-Clause license, reproduced in `third_party/amp-challenge-LICENSE`. The
antibacterial reference's provenance and every pinned revision are recorded in
`records/model_sources.json`. Model weights are downloaded from upstream at run
time.

## Component licenses

Read at the commits pinned in `records/model_sources.json`. Package entries refer
to the stated release.

| Component | License |
|---|---|
| PLUM | [MIT](https://github.com/priyamayur/PLUM/blob/650fdae718f8e761deb2c96ff428766854d050a3/LICENSE), copyright Priyanka Banerjee. The checkpoint and training exclusion CSV come from this revision. |
| APEXGo | [MIT](https://github.com/Yimeng-Zeng/APEXGo/blob/10a355a4220e6f8f432d62b267317b5b8b337dc8/LICENSE) |
| Deep-AMP adapter | [MIT](https://github.com/szczurek-lab/BattleAMP-deep-amp/blob/0a31ad796732b5e5874c3f92e771057e887f58a9/LICENSE), copyright Amir Pandi |
| fair-esm 2.0.0 | MIT, in the [PyPI wheel](https://pypi.org/project/fair-esm/2.0.0/) |
| HemoPI2 1.3 | GPLv3, in the [PyPI wheel](https://pypi.org/project/hemopi2/1.3/). The bundled `hemopi2/merci/MERCI_motif_locator.pl` is GPLv3-or-later, copyright Celine Vens. |
| tsAMP-CS | No license file in the [pinned tree](https://github.com/YangLab-BUPT/tsAMP/blob/82c722090b10878edb0b9f45033e1806a659f2b7/README.md#license). Inference uses a reconstructed network with the upstream checkpoints and strain embeddings. |
| LLAMP | [PolyForm Noncommercial 1.0.0](https://github.com/GIST-CSBL/LLAMP/blob/bb48daaa94b947edac46e498dec741911cf98edc/LICENSE). The pipeline imports `utils/model.py` from this revision. |
| Daehun/peptide_tuned_ESM-2 | No license or model card at the [pinned revision](https://huggingface.co/Daehun/peptide_tuned_ESM-2/tree/16b0dddc26541a33740a1bf084a7030b373622d5) |
| seqme 0.5.1 | BSD-3-Clause, in the [release metadata](https://pypi.org/pypi/seqme/0.5.1/json) |
| Biopython 1.81 and 1.88 | Biopython License Agreement, with file-level BSD-3-Clause dual licensing |
