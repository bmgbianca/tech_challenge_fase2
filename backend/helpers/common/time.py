def convert_seconds(seconds: float):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    return (hours, minutes)
