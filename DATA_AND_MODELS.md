# Data and models

The packaged path uses released weights; it contains no model training step.
The following sources are used in the final pipeline. Complete upstream training
data provenance and redistribution permissions are not established by this file.

| Component | Source | Use |
|---|---|---|
| PLUM | https://github.com/priyamayur/PLUM | Generator; `data/train.csv` exact-match exclusion |
| APEX | https://github.com/Yimeng-Zeng/APEXGo/tree/main/optimization/apex_oracle | Eight-model early activity ensemble |
| Deep-AMP | https://github.com/szczurek-lab/BattleAMP-deep-amp | Gram-negative and Gram-positive regressors |
| HemoPI2 1.3 | https://pypi.org/project/hemopi2/1.3/ | Model 3 hemolysis classification |
| tsAMP-CS | https://github.com/YangLab-BUPT/tsAMP | Released species checkpoints and exact-strain embeddings |
| ESM-1v | https://github.com/facebookresearch/esm | Peptide embeddings for tsAMP-CS |
| LLAMP | https://github.com/GIST-CSBL/LLAMP | Species-level MIC estimates |
| Peptide-tuned ESM-2 | https://huggingface.co/Daehun/peptide_tuned_ESM-2 | LLAMP peptide representation |
| Official antibacterial reference | https://github.com/szczurek-lab/amp-challenge-2027/blob/main/data/antibacterial.fasta | Exact-match library exclusion and Top-100 similarity check |
| Biopython and seqme | https://biopython.org/ ; https://pypi.org/project/seqme/ | Physicochemical descriptors |

Repository commits, checkpoint hashes, and model download locations are recorded
in `records/model_sources.json` and in the executable setup. A repository's
code license does not by itself establish the license of every training dataset
or weight file. Model weights are fetched from their upstream sources at run time.

Earlier project records also describe AMP-Diffusion generation experiments,
OmegAMP benchmark peptides, a 46-peptide AMP-Diffusion experimental benchmark,
and exploratory BattleAMP web results. These are not sequence inputs to this
packaged generator. The Deep-AMP repository's name contains BattleAMP; that is
distinct from querying the BattleAMP web service. The complete historical
inventory, upstream training-set overlaps, and any manual-intervention declaration
still require the separate factual submission review.
