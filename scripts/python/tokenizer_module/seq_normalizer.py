from tokenizers.normalizers import Normalizer


class SequenceNormalizer:
    def __init__(
        self,
        standard_residues=set("ACDEFGHIKLMNPQRSTVWY"),
        rare_residues=set("BJOUXZ"),
        rare_residue_policy="keep",
    ):
        self.rare_residue_policy = rare_residue_policy
        self.standard_residues = standard_residues
        self.rare_residues = rare_residues
        self.valid_residues = standard_residues.union(rare_residues)

    def as_tokenizer_normalizer(self, add_spaces=False):
        return Normalizer.custom(_TokenizerSequenceNormalizer(self, add_spaces=add_spaces))

    def normalize(self, seq, add_spaces=False, k_mer_length=None):
        """
        Normalize one protein sequence.
        - uppercases
        - strips spaces
        - handles rare/unknown residues
        - drops invalid chars
        """
        seq = seq.upper().replace(" ", "")
        out = []

        for ch in seq:
            if ch in self.standard_residues:
                out.append(ch)
            elif ch in self.rare_residues:
                if self.rare_residue_policy == "keep":
                    out.append(ch)
                elif self.rare_residue_policy == "replace_with_unk":
                    out.append("[UNKAA]")  # optional custom placeholder token
                elif self.rare_residue_policy == "replace_with_nn":
                    out.append("X")
                else:
                    raise ValueError(f"Unknown rare_residue_policy: {self.rare_residue_policy}")
            else:
                # silently drop junk chars for now
                continue

        if add_spaces:
            if k_mer_length is not None and k_mer_length > 1:
                return " ".join("".join(out[i : i + k_mer_length]) for i in range(len(out) - k_mer_length + 1))
            return " ".join(out)
        return "".join(out)


class _TokenizerSequenceNormalizer:
    def __init__(self, sequence_normalizer, add_spaces=True):
        self.sequence_normalizer = sequence_normalizer
        self.add_spaces = add_spaces

    def normalize(self, normalized):
        normalized_seq = self.sequence_normalizer.normalize(
            str(normalized),
            add_spaces=self.add_spaces,
        )
        normalized.clear()
        normalized.append(normalized_seq)
