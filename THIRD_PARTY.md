# Third-party materials

`LICENSE` applies to original project integration code and documentation only.
Downloaded upstream code, pretrained weights, reference data, and their derived
materials retain their own terms; this project does not relicense them.

The unmodified official validator is bundled under the organizer repository's
BSD-3-Clause license, reproduced in `third_party/amp-challenge-LICENSE`.
The official antibacterial reference's provenance is in `records/model_sources.json`.
Third-party model weights are downloaded from upstream at runtime.

## Focused license review — 2026-09-28

Repository licenses below were read at the exact commits in
`records/model_sources.json`. Package findings use the stated release, not the
latest release. This is a direct-component review, not an exhaustive dependency,
training-data, or model-weight rights audit.

| Component | Verified terms and source |
|---|---|
| PLUM | [MIT](https://github.com/priyamayur/PLUM/blob/650fdae718f8e761deb2c96ff428766854d050a3/LICENSE), copyright Priyanka Banerjee. The pipeline obtains its checkpoint and training exclusion CSV from this Git revision, not Figshare. |
| APEXGo | [MIT](https://github.com/Yimeng-Zeng/APEXGo/blob/10a355a4220e6f8f432d62b267317b5b8b337dc8/LICENSE). |
| Deep-AMP adapter | [MIT](https://github.com/szczurek-lab/BattleAMP-deep-amp/blob/0a31ad796732b5e5874c3f92e771057e887f58a9/LICENSE), copyright Amir Pandi. |
| fair-esm 2.0.0 | MIT, verified in the [PyPI wheel](https://pypi.org/project/fair-esm/2.0.0/)'s LICENSE. |
| HemoPI2 1.3 | GPL version 3 text in the [PyPI wheel](https://pypi.org/project/hemopi2/1.3/)'s `hemopi2-1.3.dist-info/LICENSE.txt`. The bundled `hemopi2/merci/MERCI_motif_locator.pl` header specifies GPLv3-or-later, copyright Celine Vens. |
| tsAMP-CS | No LICENSE/COPYING/NOTICE file found in the complete pinned tree; the [README License section](https://github.com/YangLab-BUPT/tsAMP/blob/82c722090b10878edb0b9f45033e1806a659f2b7/README.md#license) is empty. Permissions for the released checkpoints and strain embeddings remain unestablished. |
| LLAMP | [PolyForm Noncommercial 1.0.0](https://github.com/GIST-CSBL/LLAMP/blob/bb48daaa94b947edac46e498dec741911cf98edc/LICENSE). The pinned README explicitly applies this to all source code. It mentions two licenses but describes only the code license; separate weight/data terms remain unestablished. |
| Daehun/peptide_tuned_ESM-2 | The [pinned Hugging Face revision](https://huggingface.co/Daehun/peptide_tuned_ESM-2/tree/16b0dddc26541a33740a1bf084a7030b373622d5) has no README/model card or license file; its API metadata has no cardData. Release permissions remain unestablished. |
| seqme 0.5.1 | BSD-3-Clause, verified in [release metadata](https://pypi.org/pypi/seqme/0.5.1/json). |
| Biopython 1.81 and 1.88 | Both wheels contain the Biopython License Agreement, permitting use for any purpose subject to notices, with file-specific BSD-3-Clause dual licensing. This is not a claim that the whole package is BSD-3-Clause or that its custom license has been individually OSI-approved. |

Code-license findings do not independently establish the rights to every
associated model weight or upstream training dataset.

## Unresolved terms

The pipeline imports LLAMP's upstream `utils/model.py` directly. Its noncommercial
license may conflict with [Kaggle rule 6(c)](https://www.kaggle.com/competitions/amp-challenge/rules),
which calls for OSI-approved licenses without commercial-use restrictions for
open-source code used to generate submissions, unless otherwise specified.
Downloading the file at runtime does not change its license.

Separate permissions for LLAMP weights/data, tsAMP checkpoints and strain
embeddings, and peptide-tuned ESM-2 remain unclear from the reviewed releases.
tsAMP inference uses a reconstructed network with the upstream checkpoints and
strain embeddings.

HemoPI2's GPLv3 license permits commercial use and is OSI-approved, but is not
permissive. The organizers have not clarified whether the additional permissive
license requirement for co-authorship applies to separately installed tools.

The review did not establish complete upstream training-data provenance or
organizer acceptance of runtime weight downloads. These remain open questions;
the component table records the terms found at the pinned releases.
