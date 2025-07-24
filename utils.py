import math

def distance(p1, p2):
    """Berekent de Euclidische afstand tussen twee punten."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def resample_points(points, interval=5):
    """Her-samplet een lijst met punten zodat er een vaste afstand (interval) tussen zit."""
    if len(points) < 2:
        return points
    distances = [0]
    for i in range(1, len(points)):
        d = distance(points[i-1], points[i])
        distances.append(distances[-1] + d)
    
    total_length = distances[-1]
    if total_length == 0:
        return points
        
    new_points = [points[0]]
    current_distance = interval
    i = 1
    while current_distance < total_length and i < len(points):
        while i < len(points) and distances[i] < current_distance:
            i += 1
        if i >= len(points):
            break
        
        p0 = points[i-1]
        p1 = points[i]
        segment_length = distances[i] - distances[i-1]
        
        if segment_length == 0:
            continue
            
        ratio = (current_distance - distances[i-1]) / segment_length
        new_x = p0[0] + ratio * (p1[0] - p0[0])
        new_y = p0[1] + ratio * (p1[1] - p0[1])
        new_points.append((new_x, new_y))
        
        current_distance += interval
        
    new_points.append(points[-1])
    return new_points

def smooth_points(points, window=5):
    """Maakt een lijn van punten vloeiender met een bewegend gemiddelde."""
    if len(points) < window:
        return points
    smoothed = []
    for i in range(len(points)):
        start = max(0, i - window // 2)
        end = min(len(points), i + window // 2 + 1)
        avg_x = sum(p[0] for p in points[start:end]) / (end - start)
        avg_y = sum(p[1] for p in points[start:end]) / (end - start)
        smoothed.append((avg_x, avg_y))
    return smoothed

def point_line_distance(pt, line_start, line_end):
    """Berekent de kortste afstand van een punt tot een lijnsegment."""
    x0, y0 = pt
    x1, y1 = line_start
    x2, y2 = line_end
    dx = x2 - x1
    dy = y2 - y1
    if dx == dy == 0:  # Lijnsegment is een punt
        return distance(pt, line_start)
    
    # Projecteer het punt op de lijn
    t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx*dx + dy*dy)))
    proj = (x1 + t * dx, y1 + t * dy)
    return distance(pt, proj)
