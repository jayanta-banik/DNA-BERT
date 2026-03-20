from pathlib import Path

from tokenizers import Tokenizer, processors
from util.file_utils import iter_dataset

from .seq_normalizer import SequenceNormalizer

STANDARD_RESIDUES = set("ACDEFGHIKLMNPQRSTVWY")
RARE_RESIDUES = set("XBZJUO")
SPECIAL_TOKENS = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "[UNKAA]"]


class ProteinTokenizer:
    name: str = None
    requires_training: bool = False

    def __init__(self, max_seq_length=512, rare_residue_policy="keep", **kwargs):
        self.max_seq_length = max_seq_length
        self.rare_residue_policy = rare_residue_policy
        self.normalizer = SequenceNormalizer(
            standard_residues=STANDARD_RESIDUES,
            rare_residues=RARE_RESIDUES,
            rare_residue_policy=rare_residue_policy,
        )
        self.tokenizer: Tokenizer = None
        if kwargs.get("requires_training"):
            self.requires_training = kwargs["requires_training"]

    def normalize(self, seq):
        return self.normalizer.normalize(seq)

    def encode(self, seq):
        norm = self.normalize(seq)
        return self.tokenizer.encode(norm)

    def iter_training_corpus(self, protein_dataset, batch_size):
        for batch in iter_dataset(protein_dataset, batch_size=batch_size, desc=f"Preparing {self.name} corpus"):
            seq_col = batch.column("sequence")
            for seq_scalar in seq_col:
                if not seq_scalar.is_valid:
                    continue
                seq = seq_scalar.as_py()
                if not seq:
                    continue
                norm = self.normalize(seq)
                if norm:
                    yield norm

    def train(self, **kwargs):
        raise NotImplementedError(f"{self.name} does not support training")

    def _configure_postprocessing(self):
        cls_id = self.tokenizer.token_to_id("[CLS]")
        sep_id = self.tokenizer.token_to_id("[SEP]")
        self.tokenizer.post_processor = processors.TemplateProcessing(
            single="[CLS] $A [SEP]",
            pair="[CLS] $A [SEP] $B:1 [SEP]:1",
            special_tokens=[("[CLS]", cls_id), ("[SEP]", sep_id)],
        )
        self.tokenizer.enable_padding(
            pad_id=self.tokenizer.token_to_id("[PAD]"),
            pad_token="[PAD]",
            length=self.max_seq_length,
        )
        self.tokenizer.enable_truncation(max_length=self.max_seq_length)

    def save(self, save_dir):
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        path = save_dir / "tokenizer.json"
        self.tokenizer.save(str(path))
        print(f"Saved {self.name} tokenizer to: {path}")
        return path

    def load(self, path):
        path = Path(path)
        tokenizer_path = path / "tokenizer.json" if path.is_dir() else path
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        return self

    # --- shared introspection methods (moved from notebook) ---

    def view_vocab(self, n=20, sort_by="id"):
        vocab = self.tokenizer.get_vocab()
        if sort_by == "id":
            items = sorted(vocab.items(), key=lambda x: x[1])
        elif sort_by == "alpha":
            items = sorted(vocab.items(), key=lambda x: x[0])
        elif sort_by == "len":
            items = sorted(vocab.items(), key=lambda x: (len(x[0]), x[0]))
        else:
            raise ValueError("sort_by must be one of: id, alpha, len")

        print(f"Showing top {n} tokens (sorted by {sort_by}):\n")
        for token, idx in items[:n]:
            print(f"{idx:>4}  {token}")

    def count_learned_tokens(self):
        vocab = self.tokenizer.get_vocab()
        learned = [t for t in vocab if len(t) > 1 and not t.startswith("[")]
        print(f"Learned tokens: {len(learned)}")
        return len(learned)

    def pipeline(self, sequences):
        for seq in sequences:
            yield self.encode(seq)

    def preview(self, sequences):
        for seq in sequences:
            norm = self.normalize(seq)
            enc = self.tokenizer.encode(norm)
            print("=" * 80)
            print("RAW:   ", seq)
            print("NORM:  ", norm)
            print("TOKENS:", enc.tokens)
            print("IDS:   ", enc.ids)
