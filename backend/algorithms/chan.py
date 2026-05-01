"""Chan 氏 TDOA 定位算法（2D，3 传感器闭式解）"""

import numpy as np
import logging

from .base import SourceLocalizer

logger = logging.getLogger(__name__)


class ChanLocalizer(SourceLocalizer):
    """Chan 氏两步加权最小二乘 TDOA 定位器"""

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

        x1, y1 = sensors[0]
        x2, y2 = sensors[1]
        x3, y3 = sensors[2]

        r21 = tdoa_values[0] * sound_speed
        r31 = tdoa_values[1] * sound_speed

        K1 = x1**2 + y1**2
        K2 = x2**2 + y2**2
        K3 = x3**2 + y3**2

        G = np.array([
            [-(x2 - x1), -(y2 - y1), -r21],
            [-(x3 - x1), -(y3 - y1), -r31],
        ])

        h = 0.5 * np.array([
            [r21**2 - K2 + K1],
            [r31**2 - K3 + K1],
        ])

        try:
            GtG = G.T @ G
            Gth = G.T @ h
            a = np.linalg.solve(GtG, Gth)
        except np.linalg.LinAlgError:
            logger.warning("Chan 氏算法第一步矩阵奇异，使用伪逆求解")
            a = np.linalg.pinv(G) @ h

        x_est = float(a[0, 0])
        y_est = float(a[1, 0])

        dx = np.array([x1 - x_est, x2 - x_est, x3 - x_est])
        dy = np.array([y1 - y_est, y2 - y_est, y3 - y_est])
        ranges = np.sqrt(dx**2 + dy**2)
        ranges = np.maximum(ranges, 1e-10)

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

        return {
            "x": round(x_est, 4),
            "y": round(y_est, 4),
            "gdop": round(gdop, 4),
            "gdop_quality": quality,
        }
