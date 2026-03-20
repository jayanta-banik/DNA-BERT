from .base import RARE_RESIDUES, SPECIAL_TOKENS, STANDARD_RESIDUES, ProteinTokenizer
from .bpe_tokenizer import BPETokenizer
from .kmers_tokenizer import KmersTokenizer
from .seq_normalizer import SequenceNormalizer
from .unigram_tokenizer import UnigramTokenizer
from .wordpiece_tokenizer import WordPieceTokenizer
from .words_tokenizer import WordsTokenizer

__all__ = [
    "BPETokenizer",
    "KmersTokenizer",
    "ProteinTokenizer",
    "RARE_RESIDUES",
    "SequenceNormalizer",
    "SPECIAL_TOKENS",
    "STANDARD_RESIDUES",
    "UnigramTokenizer",
    "WordPieceTokenizer",
    "WordsTokenizer",
    "create_tokenizer",
    "load_tokenizer",
]

TOKENIZER_REGISTRY = {
    "BPE": BPETokenizer,
    "Unigram": UnigramTokenizer,
    "WordPiece": WordPieceTokenizer,
    "words": WordsTokenizer,
    "k-mers": KmersTokenizer,
}


def create_tokenizer(name, **kwargs) -> ProteinTokenizer:
    """Factory: instantiate a tokenizer by strategy name."""
    cls = TOKENIZER_REGISTRY[name]  # KeyError = fast fail on unknown strategy
    return cls(**kwargs)


def load_tokenizer(name, path, **kwargs) -> ProteinTokenizer:
    """Factory: load a tokenizer from disk by strategy name."""
    cls = TOKENIZER_REGISTRY[name]  # KeyError = fast fail on unknown strategy
    return cls(**kwargs).load(path)
