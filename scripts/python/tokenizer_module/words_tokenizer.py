from tokenizers import Tokenizer, models, pre_tokenizers
from .base import ProteinTokenizer, STANDARD_RESIDUES, RARE_RESIDUES, SPECIAL_TOKENS


class WordsTokenizer(ProteinTokenizer):
    """Single amino acid tokenizer. Each residue is one token. No training needed."""

    name = "words"
    requires_training = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        vocab = {tok: i for i, tok in enumerate(SPECIAL_TOKENS)}
        for ch in sorted(STANDARD_RESIDUES | RARE_RESIDUES):
            vocab[ch] = len(vocab)

        self.tokenizer = Tokenizer(models.WordLevel(vocab=vocab, unk_token="[UNK]"))
        self.tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
        self._configure_postprocessing()
