import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def total_route_distance(points):
    total = 0
    segment_distances = []

    for i in range(len(points) - 1):
        lat1, lon1 = points[i]
        lat2, lon2 = points[i + 1]

        d = haversine(lat1, lon1, lat2, lon2)
        segment_distances.append(d)
        total += d

    return segment_distances, round(total)


# Example
# gps_points = [
#     (19.95869, 73.75723),
#     (19.96000, 73.76000),
#     (19.96200, 73.76500)
# ]

# segments, total = total_route_distance(gps_points)

# print("Segment distances:", segments)
# print("Total route distance:", total, "meters")
