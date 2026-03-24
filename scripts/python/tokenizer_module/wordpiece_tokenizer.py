from tokenizers import Tokenizer, models, pre_tokenizers, trainers

from .base import SPECIAL_TOKENS, ProteinTokenizer


class WordPieceTokenizer(ProteinTokenizer):
    name = "WordPiece"
    requires_training = True

    def train(self, protein_table, save_dir, vocab_size, batch_size=65536, total_batches=None):
        self.tokenizer = Tokenizer(models.WordPiece(unk_token="[UNK]"))
        self.tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()

        trainer = trainers.WordPieceTrainer(
            vocab_size=vocab_size,
            special_tokens=SPECIAL_TOKENS,
        )

        self.tokenizer.train_from_iterator(
            iterator=self.iter_training_corpus(protein_table, batch_size=batch_size, batched=True),
            trainer=trainer,
        )

        self._configure_postprocessing()
        print(f"Vocab size learned: {self.tokenizer.get_vocab_size()}")
        return self
