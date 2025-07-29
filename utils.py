import math
import numpy as np

def distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def resample_points(points, interval):
    if len(points) < 2 or interval <= 0:
        return points
    resampled = [points[0]]
    for i in range(len(points) - 1):
        p1, p2 = points[i], points[i+1]
        segment_len = distance(p1, p2)
        if segment_len == 0:
            continue
        num_new_points = int(segment_len / interval)
        for j in range(1, num_new_points + 1):
            t = j * interval / segment_len
            resampled.append((p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])))
    if len(points) > 1 and distance(resampled[-1], points[-1]) > interval / 2:
        resampled.append(points[-1])
    return resampled

def smooth_points(points, window=5):
    # Implement smoothing logic if needed, for now it's a pass-through
    return points

def point_line_distance(point, p1, p2):
    line_len_sq = distance(p1, p2)**2
    if line_len_sq == 0:
        return distance(point, p1)
    t = max(0, min(1, np.dot(np.subtract(point, p1), np.subtract(p2, p1)) / line_len_sq))
    return distance(point, (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])))

# --- FUNCTIE HIER TOEGEVOEGD ---
def rgb_to_rgbw(r, g, b):
    r, g, b = int(r), int(g), int(b)
    white = min(r, g, b)
    r_out = max(0, min(255, r - white))
    g_out = max(0, min(255, g - white))
    b_out = max(0, min(255, b - white))
    white = max(0, min(255, white))
    return r_out, g_out, b_out, white
