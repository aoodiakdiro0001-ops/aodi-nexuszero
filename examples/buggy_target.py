def risky(a, b=1):
    return a / b


def crash_on_boom(text, count=1):
    if text == "boom":
        raise RuntimeError("planted crash in examples")
    return text * count
