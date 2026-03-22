from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

from .base import SPECIAL_TOKENS, ProteinTokenizer


class BPETokenizer(ProteinTokenizer):
    name = "BPE"
    requires_training = True

    def normalize(self, seq):
        return self.normalizer.normalize(seq, add_spaces=False)

    def train(self, protein_table, save_dir, vocab_size, min_frequency=2, batch_size=65536, **kwargs):
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

        print("[BPETokenizer.train] train_from_iterator begin")
        self.tokenizer.train_from_iterator(
            iterator=self.iter_training_corpus(protein_table, batch_size=batch_size, batched=True),
            trainer=trainer,
        )
        print("[BPETokenizer.train] train_from_iterator done")
        self.tokenizer.decoder = decoders.BPEDecoder()

        print("[BPETokenizer.train] postprocessing configuration begin")
        self._configure_postprocessing()
        print("[BPETokenizer.train] postprocessing configuration done")
        print(f"Vocab size learned: {self.tokenizer.get_vocab_size()}")
        return self
