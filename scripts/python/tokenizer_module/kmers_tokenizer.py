import json
from pathlib import Path

from tokenizers import Tokenizer, models, pre_tokenizers

from .base import SPECIAL_TOKENS, ProteinTokenizer


class KmersTokenizer(ProteinTokenizer):
    """Sliding-window k-mer tokenizer. Builds vocab from a data scan (no ML training)."""

    name = "k-mers"
    requires_training = False

    def __init__(self, k=3, mode="sliding", **kwargs):
        super().__init__(**kwargs)
        self.k = k
        self.mode = mode

    def _kmerize(self, normalized_seq):
        residues = normalized_seq.split()
        if len(residues) < self.k:
            return normalized_seq
        kmers = []
        for i in range(len(residues) - self.k + 1):
            kmers.append("".join(residues[i : i + self.k]))
        return " ".join(kmers)

    def build_vocab(self, protein_table, batch_size=65536, total_batches=None):
        """One-pass scan to discover k-mer vocab from data."""
        from tqdm.auto import tqdm

        kmer_set = set()
        for batch in tqdm(
            protein_table.to_batches(max_chunksize=batch_size),
            total=total_batches,
            desc=f"Building {self.k}-mer vocab",
        ):
            seq_col = batch.column("sequence")
            for seq_scalar in seq_col:
                if not seq_scalar.is_valid:
                    continue
                seq = seq_scalar.as_py()
                if not seq:
                    continue
                norm = self.normalize(seq)
                kmer_set.update(self._kmerize(norm).split())

        vocab = {tok: i for i, tok in enumerate(SPECIAL_TOKENS)}
        for kmer in sorted(kmer_set):
            if kmer not in vocab:
                vocab[kmer] = len(vocab)

        self.tokenizer = Tokenizer(models.WordLevel(vocab=vocab, unk_token="[UNK]"))
        self.tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
        self._configure_postprocessing()
        print(f"Built {self.k}-mer vocab: {len(vocab)} tokens")
        return self

    def encode(self, seq):
        norm = self.normalize(seq)
        kmerized = self._kmerize(norm)
        return self.tokenizer.encode(kmerized)

    def save(self, save_dir):
        path = super().save(save_dir)
        meta_path = path.parent / "kmer_meta.json"
        with open(meta_path, "w") as f:
            json.dump({"k": self.k, "mode": self.mode}, f)
        return path

    def load(self, path):
        path = Path(path)
        meta_dir = path if path.is_dir() else path.parent
        super().load(path)

        meta_path = meta_dir / "kmer_meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            self.k = meta.get("k", self.k)
            self.mode = meta.get("mode", self.mode)

        return self
