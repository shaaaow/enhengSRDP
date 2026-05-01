"""Chan 氏 TDOA 定位算法（2D，3 传感器，WLS 初始化 + Newton-Raphson 精化）"""

import numpy as np
import logging

from .base import SourceLocalizer

logger = logging.getLogger(__name__)


class ChanLocalizer(SourceLocalizer):
    """Chan 氏 WLS 初始化 + Newton-Raphson 迭代精化定位器"""

    def localize(
        self,
        sensors: list[tuple[float, float]],
        tdoa_values: list[float],
        sound_speed: float = 1500.0,
    ) -> dict:
        """
        @param sensors     - 3 个传感器坐标 [(x1,y1), (x2,y2), (x3,y3)]
        @param tdoa_values - 以第一个传感器为参考的 TDOA [dt12, dt13]（秒）
        @param sound_speed - 声速（m/s）
        @returns {x, y, gdop, gdop_quality}
        """
        if len(sensors) != 3:
            raise ValueError("Chan 氏算法当前仅支持 3 个传感器")
        if len(tdoa_values) != 2:
            raise ValueError("需要 2 个独立 TDOA 值 (dt12, dt13)")

        r21 = tdoa_values[0] * sound_speed
        r31 = tdoa_values[1] * sound_speed

        x0, y0 = self._wls_initial(sensors, r21, r31)

        cx = np.mean([s[0] for s in sensors])
        cy = np.mean([s[1] for s in sensors])

        starts = [
            (x0, y0),
            (cx, cy),
            (cx, cy * 2),
            *[(s[0] + 0.1, s[1] + 0.1) for s in sensors],
        ]

        res_threshold = 1e-4
        candidates = []

        for sx, sy in starts:
            rx, ry = self._newton(sx, sy, sensors, r21, r31)
            res = self._residual(rx, ry, sensors, r21, r31)
            if res < res_threshold:
                dist_to_centroid = (rx - cx) ** 2 + (ry - cy) ** 2
                candidates.append((dist_to_centroid, res, rx, ry))

        if candidates:
            _, _, x_est, y_est = min(candidates)
        else:
            x_est, y_est = x0, y0

        gdop, quality = self._compute_gdop(x_est, y_est, sensors)

        return {
            "x": round(x_est, 4),
            "y": round(y_est, 4),
            "gdop": round(gdop, 4),
            "gdop_quality": quality,
        }

    @staticmethod
    def _wls_initial(
        sensors: list[tuple[float, float]], r21: float, r31: float
    ) -> tuple[float, float]:
        x1, y1 = sensors[0]
        x2, y2 = sensors[1]
        x3, y3 = sensors[2]

        K1, K2, K3 = x1**2 + y1**2, x2**2 + y2**2, x3**2 + y3**2

        G = np.array([
            [-(x2 - x1), -(y2 - y1), -r21],
            [-(x3 - x1), -(y3 - y1), -r31],
        ])
        h = 0.5 * np.array([[r21**2 - K2 + K1], [r31**2 - K3 + K1]])

        a = np.linalg.pinv(G) @ h
        return float(a[0, 0]), float(a[1, 0])

    @staticmethod
    def _newton(
        x: float,
        y: float,
        sensors: list[tuple[float, float]],
        r21: float,
        r31: float,
        max_iter: int = 50,
        tol: float = 1e-10,
    ) -> tuple[float, float]:
        x1, y1 = sensors[0]
        x2, y2 = sensors[1]
        x3, y3 = sensors[2]

        for _ in range(max_iter):
            d1 = np.sqrt((x - x1) ** 2 + (y - y1) ** 2)
            d2 = np.sqrt((x - x2) ** 2 + (y - y2) ** 2)
            d3 = np.sqrt((x - x3) ** 2 + (y - y3) ** 2)

            if d1 < 1e-12 or d2 < 1e-12 or d3 < 1e-12:
                break

            f = np.array([d2 - d1 - r21, d3 - d1 - r31])

            J = np.array([
                [(x - x2) / d2 - (x - x1) / d1, (y - y2) / d2 - (y - y1) / d1],
                [(x - x3) / d3 - (x - x1) / d1, (y - y3) / d3 - (y - y1) / d1],
            ])

            try:
                delta = np.linalg.solve(J, f)
            except np.linalg.LinAlgError:
                break

            x -= float(delta[0])
            y -= float(delta[1])

            if np.linalg.norm(delta) < tol:
                break

        return x, y

    @staticmethod
    def _residual(
        x: float,
        y: float,
        sensors: list[tuple[float, float]],
        r21: float,
        r31: float,
    ) -> float:
        d = [np.sqrt((x - sx) ** 2 + (y - sy) ** 2) for sx, sy in sensors]
        return (d[1] - d[0] - r21) ** 2 + (d[2] - d[0] - r31) ** 2

    @staticmethod
    def _compute_gdop(
        x: float, y: float, sensors: list[tuple[float, float]]
    ) -> tuple[float, str]:
        dx = np.array([s[0] - x for s in sensors])
        dy = np.array([s[1] - y for s in sensors])
        ranges = np.maximum(np.sqrt(dx**2 + dy**2), 1e-10)

        H = np.column_stack([dx / ranges, dy / ranges])

        try:
            cov = np.linalg.inv(H.T @ H)
            gdop = float(np.sqrt(np.trace(cov)))
        except np.linalg.LinAlgError:
            gdop = 99.99

        if gdop < 2.0:
            quality = "良好布局"
        elif gdop < 5.0:
            quality = "一般布局"
        else:
            quality = "较差布局"

        return gdop, quality
