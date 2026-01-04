
def format_time(timeticks):
    """ Convert timeticks in Human readable format """

    if timeticks is None:
        return "N/A"

    total_seconds = int(timeticks / 100)

    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    years, days = divmod(days, 365)

    time_parts=[]
    if years > 0:
        time_parts.append(f"{years}y")
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    if seconds > 0 or not time_parts:
        time_parts.append(f"{seconds}s")

    time = " ".join(time_parts)
 
    return time    
    