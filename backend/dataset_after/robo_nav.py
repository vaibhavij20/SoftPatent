import time
import random
import logging
import heapq

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class KalmanFilter:
    def __init__(self):
        self.state = 0.0
        self.covariance = 1.0
        self.process_noise = 0.1
        self.measurement_noise = 0.5

    def predict(self, control_input):
        noise = random.uniform(-0.05, 0.05)
        self.state = self.state + control_input + noise
        self.covariance += self.process_noise
        logging.debug(f"KF Predict → state={self.state:.4f}, noise={noise:.4f}")

    def update(self, measurement):
        k = self.covariance / (self.covariance + self.measurement_noise)
        innovation = measurement - self.state
        self.state = self.state + k * innovation
        self.covariance = (1 - k) * self.covariance
        logging.debug(f"KF Update → state={self.state:.4f}, innovation={innovation:.4f}")

    def get_state(self):
        return self.state


def a_star(grid, start, goal):
    logging.info("Running A* pathfinding...")

    rows, cols = len(grid), len(grid[0])
    open_list = []
    heapq.heappush(open_list, (0, start))

    came_from = {start: None}
    cost_so_far = {start: 0}

    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    while open_list:
        _, current = heapq.heappop(open_list)

        if current == goal:
            break

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = current[0] + dx, current[1] + dy

            if (
                0 <= nx < rows
                and 0 <= ny < cols
                and grid[nx][ny] == 0
            ):
                new_cost = cost_so_far[current] + 1
                if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
                    cost_so_far[(nx, ny)] = new_cost
                    priority = new_cost + heuristic((nx, ny), goal)
                    heapq.heappush(open_list, (priority, (nx, ny)))
                    came_from[(nx, ny)] = current

    # Recover path
    path = []
    curr = goal
    while curr:
        path.append(curr)
        curr = came_from.get(curr)
    return list(reversed(path))


class RobotController:
    def __init__(self):
        self.kf = KalmanFilter()
        self.battery = 100.0
        self.position = (0, 0)
        self.grid = [[0] * 20 for _ in range(20)]
        self.goal = (19, 19)
        self.obstacle_prob = 0.1

    def update_sensors(self):
        measurement = self.position[0] + random.uniform(-1, 1)
        logging.debug(f"Sensor reading={measurement:.4f}")
        self.kf.update(measurement)

    def predict_motion(self):
        control = random.choice([0.5, 1.0, -0.5])
        logging.debug(f"Control input={control}")
        self.kf.predict(control)

    def check_battery(self):
        self.battery -= random.uniform(0.2, 0.5)
        logging.info(f"Battery={self.battery:.2f}%")
        if self.battery < 15:
            logging.warning("Battery critically low!")

    def generate_obstacles(self):
        for i in range(20):
            for j in range(20):
                if random.random() < self.obstacle_prob:
                    self.grid[i][j] = 1

    def compute_path(self):
        return a_star(self.grid, self.position, self.goal)

    def execute_motion(self, path):
        logging.info("Following computed path...")
        for step in path[:30]:
            self.position = step
            logging.debug(f"Robot moved to {step}")
            time.sleep(0.02)

    def run_cycle(self):
        self.generate_obstacles()
        self.update_sensors()
        self.predict_motion()
        self.check_battery()
        path = self.compute_path()
        self.execute_motion(path)


def main():
    logging.info("Starting Robotics Navigation System")
    robot = RobotController()

    for i in range(5):
        logging.info(f"--- Cycle {i} ---")
        robot.run_cycle()
        time.sleep(0.1)

    logging.info("Navigation complete.")


if __name__ == "__main__":
    main()
