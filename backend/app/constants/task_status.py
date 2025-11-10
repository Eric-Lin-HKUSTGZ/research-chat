"""
任务状态常量定义
Task Status Constants
"""

class CreationStatus:
    """
    ResearchChatProcessInfo 的 creation_status 枚举值
    对应数据库 Enum('pending', 'creating', 'created', 'failed')
    """
    PENDING = 'pending'      # 任务等待中
    CREATING = 'creating'    # 任务进行中
    CREATED = 'created'      # 任务已完成
    FAILED = 'failed'        # 任务失败

    # 正在处理中的状态集合
    IN_PROGRESS = [PENDING, CREATING]

    # 已结束的状态集合
    FINISHED = [CREATED, FAILED]

    @classmethod
    def is_in_progress(cls, status: str) -> bool:
        """判断状态是否为处理中"""
        return status in cls.IN_PROGRESS

    @classmethod
    def is_finished(cls, status: str) -> bool:
        """判断状态是否已结束"""
        return status in cls.FINISHED
