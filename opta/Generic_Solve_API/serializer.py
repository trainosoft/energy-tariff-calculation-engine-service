def to_json(obj):
    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, list):
        return [to_json(item) for item in obj]

    if isinstance(obj, dict):
        return {k: to_json(v) for k, v in obj.items()}

    if hasattr(obj, "__dict__"):
        return {
            key: to_json(value)
            for key, value in obj.__dict__.items()
            if not key.startswith("_")
        }

    return str(obj)
