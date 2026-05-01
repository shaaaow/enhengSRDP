"""算法注册表 — 新增算法只需在对应字典中添加一行映射"""

from .gcc_phat import GccPhatCppEstimator
from .chan import ChanLocalizer

TDOA_ESTIMATORS: dict = {
    "gcc_phat": GccPhatCppEstimator,
}

LOCALIZERS: dict = {
    "chan": ChanLocalizer,
}


def get_tdoa_estimator(name: str = "gcc_phat"):
    """按名称获取 TDOA 估计器实例"""
    cls = TDOA_ESTIMATORS.get(name)
    if cls is None:
        available = ", ".join(TDOA_ESTIMATORS.keys())
        raise ValueError(f"未知的 TDOA 算法 '{name}'，可用: {available}")
    return cls()


def get_localizer(name: str = "chan"):
    """按名称获取定位算法实例"""
    cls = LOCALIZERS.get(name)
    if cls is None:
        available = ", ".join(LOCALIZERS.keys())
        raise ValueError(f"未知的定位算法 '{name}'，可用: {available}")
    return cls()
