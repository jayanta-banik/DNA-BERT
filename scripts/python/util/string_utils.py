def humanizeNumericString(n, decimals=0):
    if n >= 1_000_000_000:
        return f"{round(n / 1_000_000_000, decimals)}B"
    elif n >= 1_000_000:
        return f"{round(n / 1_000_000, decimals)}M"
    elif n >= 1_000:
        return f"{round(n / 1_000, decimals)}K"
    return str(n)
