"""Unseen-family reference selection."""
from ...sampling import choose_ids

def select_families(families, n, seed, class_label):
    return choose_ids(families, n, seed, 'families:' + class_label)

