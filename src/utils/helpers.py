# Shared utility functions


def chunk_list(lst: list, size: int) -> list[list]:
    """Split a list into chunks of a given size."""
    return [lst[i:i + size] for i in range(0, len(lst), size)]
