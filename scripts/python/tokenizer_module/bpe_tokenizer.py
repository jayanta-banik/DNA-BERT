from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

from .base import SPECIAL_TOKENS, ProteinTokenizer


class BPETokenizer(ProteinTokenizer):
    name = "BPE"
    requires_training = True

    def normalize(self, seq):
        return self.normalizer.normalize(seq, add_spaces=True)

    def train(
        self,
        protein_table,
        save_dir,
        vocab_size,
        min_frequency=2,
        batch_size=65536,
        lines_per_corpus_file=50000,
        overwrite_corpus=False,
        **kwargs,
    ):
        print(f"[BPETokenizer.train] start vocab_size={vocab_size} min_frequency={min_frequency} batch_size={batch_size}")

        self.tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))
        self.tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
        print("[BPETokenizer.train] tokenizer instance created")

        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=SPECIAL_TOKENS,
            show_progress=True,
        )
        print("[BPETokenizer.train] trainer configured")

        print("[BPETokenizer.train] writing normalized corpus begin")
        corpus_files = self.write_normalized_corpus(
            protein_dataset=protein_table,
            save_dir=save_dir,
            batch_size=batch_size,
            lines_per_file=lines_per_corpus_file,
            overwrite=overwrite_corpus,
        )
        print(f"[BPETokenizer.train] writing normalized corpus done ({len(corpus_files)} files)")

        print("[BPETokenizer.train] file training begin")
        self.tokenizer.train(files=[str(path) for path in corpus_files], trainer=trainer)
        print("[BPETokenizer.train] file training done")
        self.tokenizer.decoder = decoders.BPEDecoder()

        print("[BPETokenizer.train] postprocessing configuration begin")
        print("[BPETokenizer.train] postprocessing configuration done")
        print(f"Vocab size learned: {self.tokenizer.get_vocab_size()}")
        self._configure_postprocessing()
        return self
