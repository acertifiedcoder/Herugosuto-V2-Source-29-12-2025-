import pygame, math

BEZIER_TYPES = {
    'bounce_out': [[2.4, 0.01], [1.25, 2.65]],
    'slow_in': [[0.91, 0.29], [0.98, -0.33]],
}
LINE_VFX = {
    'found_item': {
        'points': [[0, 0], [5, -5], [70, -5]],
        'color': (208, 223, 215),
        'width': 1,
        'speed': 0.9,
        'time_cap': True,
        'offset_affected': True,
    },
}

class CubicBezier():
    def __init__(self, *points):
        points = list(points)
        if len(points) not in [2, 4]:
            raise Exception('InvalidArgumentCountError')
        if len(points) == 2:
            points = [[0, 0]] + points + [[1, 1]]
        self.points = points
    
    def calculate(self, t):
        x = (1 - t) ** 3 * self.points[0][0] + 3 * t * (1 - t) ** 2 * self.points[1][0] + 3 * t ** 2 * (1 - t) * self.points[2][0] + t ** 3 * self.points[3][0]
        y = (1 - t) ** 3 * self.points[0][1] + 3 * t * (1 - t) ** 2 * self.points[1][1] + 3 * t ** 2 * (1 - t) * self.points[2][1] + t ** 3 * self.points[3][1]
        return [x, y]

    def calculate_x(self, t):
        return self.calculate(t)[0]

class LineChainVFX():
    def __init__(self, point_config, location, bezier, rate, color, width=1, time_cap=True, offset_affected=True):
        dis = [math.sqrt((p[0] - point_config[i - 1][0]) ** 2 + (p[1] - point_config[i - 1][1]) ** 2) for i, p in enumerate(point_config) if i != 0]
        total_line_length = sum(dis)
        point_config_with_times = [point_config[0] + [0]]
        cumulative_length = 0
        for i, point in enumerate(point_config):
            if i != 0:
                temp_dis = math.sqrt((point[0] - point_config[i - 1][0]) ** 2 + (point[1] - point_config[i - 1][1]))
                cumulative_length += temp_dis
                point_config_with_times.append(point + [cumulative_length / total_line_length])
        self.point_config = point_config_with_times
        self.bezier = bezier
        self.time = 0
        self.rate = rate
        self.base_offset = location
        self.color = color
        self.width = width
        self.time_cap = time_cap
        self.offset_affected = offset_affected

    def update(self, dt):
        if self.time_cap:
            self.time = min(self.time + self.rate * dt, 1)
        else:
            self.time == self.rate * dt

    def draw(self, surf, offset=[0, 0]):
        if not self.offset_affected:
            offset = [0, 0]

        if self.time > 0:
            length = self.bezier.calculate_x(self.time)
            for i, point in enumerate(self.point_config):
                if i != 0:
                    first_point = [self.point_config[i - 1][0] + self.base_offset[0] - offset[0], self.point_config[i - 1][1] + self.base_offset[1] - offset[1]]

                    if (point[2] < length) and (i != len(self.point_config) - 1):
                        pygame.draw.line(surf, self.color, first_point, [point[0] + self.base_offset[0] - offset[0], point[1] + self.base_offset[1] - offset[1]], self.width)
                    else:
                        dif_x = point[0] - self.point_config[i - 1][0]
                        dif_y = point[1] - self.point_config[i - 1][1]
                        relative_length = (length - self.point_config[i - 1][2]) / (point[2] - self.point_config[i - 1][2])
                        line_end = [self.point_config[i - 1][0] + dif_x * relative_length, self.point_config[i - 1][1] + dif_y * relative_length]
                        pygame.draw.line(surf, self.color, first_point, [line_end[0] + self.base_offset[0] - offset[0], line_end[1] + self.base_offset[1] - offset[1]], self.width)
                        break

def generate_line_chain_vfx(line_type, bezier_type, location):
    line_info = LINE_VFX[line_type]
    return LineChainVFX(line_info['points'], location, CubicBezier(*BEZIER_TYPES[bezier_type]), line_info['speed'], line_info['color'], width=line_info['width'], time_cap=line_info['time_cap'], offset_affected=line_info['offset_affected'])