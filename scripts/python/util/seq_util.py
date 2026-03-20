from collections import Counter


def inspect_residue_distribution(protein_table, batch_size):
    """
    Count residues from the raw sequence column.
    Useful sanity check before tokenizer training.
    """
    counts = Counter()

    for batch in protein_table.to_batches(max_chunksize=batch_size):
        seq_col = batch.column("sequence")
        for seq_scalar in seq_col:
            if not seq_scalar.is_valid:
                continue
            seq = seq_scalar.as_py()
            if seq:
                counts.update(seq.upper().replace(" ", ""))

    return counts
